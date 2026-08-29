# RecoverOS

Autonomous Revenue Recovery with Deterministic Controls.

> **Note:** The actual project code and detailed documentation reside in the `revenue_recovery/` subdirectory.

## Overview

RecoverOS detects failed payments, diagnoses the failure, calculates the economic value of recovery, recommends an intervention using an Agentic workflow, and executes only when deterministic safety controls (Policy Engine & Guardrails) allow it.

## Key Subdirectories
- `revenue_recovery/app` - The core FastAPI backend and Engine (Orchestrator, Scorer, PolicyEngine, Guardrails, Worker).
- `revenue_recovery/frontend` - The operational Next.js command center frontend.
- `revenue_recovery/tests` - The comprehensive regression and adversarial test suite.

To read the full documentation, architecture, and instructions on how to start the app locally, please refer to [revenue_recovery/README.md](revenue_recovery/README.md).
