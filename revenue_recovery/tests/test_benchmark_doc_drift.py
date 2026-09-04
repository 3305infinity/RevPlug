"""Test: benchmark numbers in README.md and PROJECT.md must match evaluation_report.json.

evaluation_report.json is the single source of truth. README.md and PROJECT.md are
manually written narrative docs, but every numeric benchmark claim they contain must
exactly match the current JSON values. This test prevents silent drift.

It is NOT an auto-generation test: the prose and structure of README.md / PROJECT.md
are intentionally hand-written. This test only guards the numeric claims.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = REPO_ROOT / "revenue_recovery" / "docs"
JSON_PATH = REPO_ROOT / "evaluation_report.json"

if not JSON_PATH.is_file():
    pytest.skip("evaluation_report.json not found — run a benchmark first.", allow_module_level=True)


def load_json() -> dict:
    with open(JSON_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def read_doc(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def minor_to_rs(minor: int | float) -> float:
    return float(minor) / 100.0


BOLD_RS = re.compile(r"\*\*₹([\d,]+\.\d{2})\*\*|₹([\d,]+\.\d{2})")
BOLD_PCT = re.compile(r"\*\*([\d]+\.\d+)%pts?\*\*|\*\*([\d]+\.\d+)%\*\*|([\d]+\.\d+)%")
WIN_RATE = re.compile(r"\*\*(\d+)/10 seeds \((\d+)%\)\*\*")


def extract_rs_values(text: str) -> list[float]:
    values = []
    for m in BOLD_RS.finditer(text):
        val = m.group(1) or m.group(2)
        if val:
            values.append(float(val.replace(",", "")))
    return values


class TestBenchmarkDocDrift:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = load_json()
        self.ros = self.data["revplug"]
        self.bl = self.data["baseline"]
        self.sbl = self.data["safe_baseline"]
        self.comp = self.data["comparison"]
        self.agg = self.data.get("multi_seed_aggregate", {})
        self.attr = self.ros.get("attribution_metrics", {})

    def _read_readme(self) -> str:
        path = REPO_ROOT / "README.md"
        assert path.is_file(), f"README.md not found at {path}"
        return read_doc(path)

    def _read_project(self) -> str:
        path = REPO_ROOT / "PROJECT.md"
        assert path.is_file(), f"PROJECT.md not found at {path}"
        return read_doc(path)

    # ---- single-seed rupee amounts (set-based, order-independent) ----

    def _check_single_seed_amounts(self, content: str, doc_label: str):
        block = re.search(
            r"(### .*?Seed 42.*?\n)(.*?)(\n### |\n## |\Z)",
            content,
            re.DOTALL | re.IGNORECASE,
        )
        section_text = block.group(2) if block else content

        expected = {
            minor_to_rs(self.ros["total_amount_at_risk"]),
            minor_to_rs(self.bl["actual_recovered"]),
            minor_to_rs(self.sbl["actual_recovered"]),
            minor_to_rs(self.ros["actual_recovered"]),
            minor_to_rs(self.ros["net_recovered"]),
            minor_to_rs(self.bl["intervention_cost"]),
            minor_to_rs(self.sbl["intervention_cost"]),
            minor_to_rs(self.ros["intervention_cost"]),
        }
        found = set(extract_rs_values(section_text))

        missing = []
        for exp in sorted(expected):
            closest = min(found, key=lambda f: abs(f - exp)) if found else None
            if closest is None or abs(closest - exp) >= 0.01:
                missing.append(f"₹{exp:.2f}")

        assert not missing, (
            f"{doc_label} single-seed section missing/mismatched amounts: {missing}. "
            f"Found: {sorted(found)}"
        )

    def test_readme_single_seed_rupee_amounts(self):
        self._check_single_seed_amounts(self._read_readme(), "README.md")

    def test_project_single_seed_rupee_amounts(self):
        self._check_single_seed_amounts(self._read_project(), "PROJECT.md")

    # ---- recovery rate percentages ----

    def test_readme_recovery_rate_pct(self):
        content = self._read_readme()
        ros_rate = round(self.ros["recovery_rate"] * 100, 1)
        assert f"{ros_rate:.1f}%" in content

    def test_project_recovery_rate_pct(self):
        content = self._read_project()
        ros_rate = round(self.ros["recovery_rate"] * 100, 1)
        assert f"{ros_rate:.1f}%" in content

    # ---- multi-seed win rate ----

    def test_readme_win_rate(self):
        content = self._read_readme()
        wins = self.agg.get("revplug_wins_vs_safe", 0)
        total = self.agg.get("total_seeds", 10)
        pct = self.agg.get("revplug_win_rate_pct", 0)
        label = f"{wins}/{total} seeds ({int(round(pct))}%)"
        assert label in content

    def test_project_win_rate(self):
        content = self._read_project()
        wins = self.agg.get("revplug_wins_vs_safe", 0)
        total = self.agg.get("total_seeds", 10)
        pct = self.agg.get("revplug_win_rate_pct", 0)
        label = f"{wins}/{total} seeds ({int(round(pct))}%)"
        assert label in content

    # ---- multi-seed mean net values ----

    def test_readme_mean_net_revplug(self):
        content = self._read_readme()
        mean_net = minor_to_rs(self.agg.get("revplug_mean_net", 0))
        assert f"₹{mean_net:,.2f}" in content

    def test_project_mean_net_revplug(self):
        content = self._read_project()
        mean_net = minor_to_rs(self.agg.get("revplug_mean_net", 0))
        assert f"₹{mean_net:,.2f}" in content

    def test_readme_mean_net_safe(self):
        content = self._read_readme()
        safe_net = minor_to_rs(self.agg.get("safe_mean_net", 0))
        assert f"₹{safe_net:,.2f}" in content

    def test_project_mean_net_safe(self):
        content = self._read_project()
        safe_net = minor_to_rs(self.agg.get("safe_mean_net", 0))
        assert f"₹{safe_net:,.2f}" in content

    # ---- EVALUATION_REPORT.md is current ----

    def test_evaluation_report_md_is_current(self):
        md_path = DOCS_DIR / "EVALUATION_REPORT.md"
        if not md_path.is_file():
            pytest.skip("docs/EVALUATION_REPORT.md not found")
        content = read_doc(md_path)

        ros_rate = round(self.ros["recovery_rate"] * 100, 1)
        assert f"{ros_rate:.1f}%" in content

        wins = self.agg.get("revplug_wins_vs_safe", 0)
        total = self.agg.get("total_seeds", 10)
        pct = self.agg.get("revplug_win_rate_pct", 0)
        label = f"{wins}/{total} seeds ({int(round(pct))}%)"
        assert label in content

    # ---- attribution amounts ----

    def test_readme_attribution_agent_assisted(self):
        content = self._read_readme()
        aa_rs = minor_to_rs(self.attr.get("AGENT_ASSISTED_recovered_minor", 0))
        assert f"₹{aa_rs:,.2f}" in content
        assert "₹5,600.00" not in content

    def test_project_attribution_agent_assisted(self):
        content = self._read_project()
        aa_rs = minor_to_rs(self.attr.get("AGENT_ASSISTED_recovered_minor", 0))
        assert f"₹{aa_rs:,.2f}" in content
        assert "₹5,600.00" not in content

    # ---- terminology guard ----

    def _check_no_forbidden_merchant_claims(self, content: str, doc_label: str):
        bench_section = re.search(
            r"(## .*?Benchmark.*?\n)(.*?)(\n## |\Z)",
            content,
            re.DOTALL | re.IGNORECASE,
        )
        section_text = bench_section.group(2) if bench_section else content

        forbidden_patterns = [
            r"recovered\s+from\s+real\s+merchant",
            r"recovered\s+from\s+live\s+merchant",
            r"recovered\s+from\s+actual\s+merchant",
            r"revenue\s+from\s+real\s+merchant\s+payment",
        ]
        found = [p for p in forbidden_patterns if re.search(p, section_text, re.IGNORECASE)]
        assert not found, (
            f"{doc_label} benchmark section contains forbidden real-merchant claims: {found}. "
            "Use 'seeded counterfactual evaluation' or 'settlement-modeled recovery'."
        )

    def test_readme_no_forbidden_merchant_claims(self):
        self._check_no_forbidden_merchant_claims(self._read_readme(), "README.md")

    def test_project_no_forbidden_merchant_claims(self):
        self._check_no_forbidden_merchant_claims(self._read_project(), "PROJECT.md")
