"""Hinglish Promise-to-Pay Extractor.

Parses structured payment commitment intent from Hinglish/English customer text.
Enforces strict fail-closed behavior if amount or date cannot be safely resolved.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any


@dataclass(frozen=True, slots=True)
class ExtractedPromise:
    intent: str
    amount_minor: int | None
    promised_date: str | None  # YYYY-MM-DD
    confidence: float
    source_text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "amount_minor": self.amount_minor,
            "promised_date": self.promised_date,
            "confidence": self.confidence,
            "source_text": self.source_text,
        }


class HinglishPromiseExtractor:
    """Bounded structured extractor for Hinglish promise-to-pay customer messages."""

    DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    MONTH_MAP = {
        "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
        "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
        "august": 8, "aug": 8, "september": 9, "sept": 9, "sep": 9, "october": 10, "oct": 10,
        "november": 11, "nov": 11, "december": 12, "dec": 12,
    }

    def extract(self, text: str, reference_date: date | None = None) -> ExtractedPromise:
        if not text or not text.strip():
            return ExtractedPromise(
                intent="unknown",
                amount_minor=None,
                promised_date=None,
                confidence=0.0,
                source_text=text or "",
            )

        ref = reference_date or datetime.now(timezone.utc).date()
        lower = text.lower().strip()

        # Check payment intent keywords
        intent_keywords = ["clear kar", "payment kar", "pay kare", "pay kar", "bhej doon", "dunga", "dunge", "denge", "settle", "pay kar dungi", "pay kar dunga"]
        has_intent = any(kw in lower for kw in intent_keywords)

        # Extract Amount
        amount_minor = self._extract_amount(lower)

        # Extract Date
        promised_date = self._extract_date(lower, ref)

        if not has_intent and (amount_minor is None or promised_date is None):
            return ExtractedPromise(
                intent="ambiguous",
                amount_minor=None,
                promised_date=None,
                confidence=0.0,
                source_text=text,
            )

        # Fail-closed if amount or date is missing when required for promise creation
        if amount_minor is None or promised_date is None:
            return ExtractedPromise(
                intent="incomplete_promise",
                amount_minor=amount_minor,
                promised_date=promised_date.isoformat() if promised_date else None,
                confidence=0.3 if (amount_minor or promised_date) else 0.0,
                source_text=text,
            )

        confidence = 0.95 if has_intent else 0.85
        return ExtractedPromise(
            intent="promise_to_pay",
            amount_minor=amount_minor,
            promised_date=promised_date.isoformat(),
            confidence=confidence,
            source_text=text,
        )

    def _extract_amount(self, text: str) -> int | None:
        # 1. Match numbers with unit suffix like '50 hazaar', '50 hazar', '18k', '2 lakh', '12000 rupees', '12000 rs'
        match = re.search(r'([\d,]+(?:\.\d+)?)\s*(k|hazaar|hazar|lakh|lac|rupees|rupee|rs\.?|inr)\b', text)
        if match:
            raw_num = match.group(1).replace(',', '')
            try:
                val = float(raw_num)
                unit = match.group(2).rstrip('.')
                if unit in ('k', 'hazaar', 'hazar'):
                    val *= 1000
                elif unit in ('lakh', 'lac'):
                    val *= 100000
                if val > 0:
                    return int(val * 100)
            except ValueError:
                pass

        # 2. Match numbers with currency prefix like ₹18,000, rs 18000, inr 5000
        match = re.search(r'(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)', text)
        if match:
            raw_num = match.group(1).replace(',', '')
            try:
                val = float(raw_num)
                if val > 0:
                    return int(val * 100)
            except ValueError:
                pass

        # 3. Match standalone numbers associated with pay/clear/rupees/transfer/dungi
        match = re.search(r'([\d,]+)\s*(?:pay|kar|clear|ko|tak|dunga|dungi|transfer|rupees|rs)', text)
        if match:
            raw_num = match.group(1).replace(',', '')
            try:
                val = float(raw_num)
                if val > 0:
                    return int(val * 100)
            except ValueError:
                pass

        # 4. Match standalone 4+ digit numbers like 18000, 25000
        match = re.search(r'\b(\d{4,8})\b', text)
        if match:
            val = float(match.group(1))
            return int(val * 100)

        return None

    def _extract_date(self, text: str, ref: date) -> date | None:
        # Check "kal" (tomorrow) / "aaj" (today) / "parso" (day after tomorrow)
        if "kal" in text:
            return ref + timedelta(days=1)
        if "aaj" in text:
            return ref
        if "parso" in text:
            return ref + timedelta(days=2)

        # Check explicit month name with day e.g. "15 September", "15th Sept 2026", "September 15"
        match = re.search(
            r'(\d{1,2})\s*(?:st|nd|rd|th)?\s*(january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul|august|aug|september|sept|sep|october|oct|november|nov|december|dec)\b(?:\s*(\d{4}))?',
            text,
        )
        if match:
            day_num = int(match.group(1))
            month_name = match.group(2)
            year_str = match.group(3)
            month_num = self.MONTH_MAP.get(month_name)
            if month_num and 1 <= day_num <= 31:
                year_val = int(year_str) if year_str else ref.year
                try:
                    target_date = date(year_val, month_num, day_num)
                    if not year_str and target_date < ref:
                        target_date = date(year_val + 1, month_num, day_num)
                    return target_date
                except ValueError:
                    pass

        match = re.search(
            r'(january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul|august|aug|september|sept|sep|october|oct|november|nov|december|dec)\s*(\d{1,2})\s*(?:st|nd|rd|th)?\b(?:\s*(\d{4}))?',
            text,
        )
        if match:
            month_name = match.group(1)
            day_num = int(match.group(2))
            year_str = match.group(3)
            month_num = self.MONTH_MAP.get(month_name)
            if month_num and 1 <= day_num <= 31:
                year_val = int(year_str) if year_str else ref.year
                try:
                    target_date = date(year_val, month_num, day_num)
                    if not year_str and target_date < ref:
                        target_date = date(year_val + 1, month_num, day_num)
                    return target_date
                except ValueError:
                    pass

        # Check "X tareekh / tarik / tarikh" pattern e.g. "5 tareekh ko"
        match = re.search(r'(\d{1,2})\s*(?:st|nd|rd|th)?\s*(?:tareekh|tarik|tarikh|date)', text)
        if match:
            day_num = int(match.group(1))
            if 1 <= day_num <= 31:
                try:
                    target_date = date(ref.year, ref.month, day_num)
                    if target_date < ref:
                        next_month = ref.month % 12 + 1
                        next_year = ref.year + (1 if next_month == 1 else 0)
                        target_date = date(next_year, next_month, day_num)
                    return target_date
                except ValueError:
                    pass

        # Check day names e.g. "friday ko", "next monday tak"
        for idx, day_name in enumerate(self.DAY_NAMES):
            if day_name in text:
                current_weekday = ref.weekday()  # Monday is 0, Sunday is 6
                target_weekday = idx
                days_ahead = target_weekday - current_weekday
                if days_ahead <= 0:  # Target day already occurred this week, move to next week
                    days_ahead += 7
                if "next" in text and days_ahead < 7:
                    days_ahead += 7
                return ref + timedelta(days=days_ahead)

        # Check relative days e.g. "in 3 days", "3 din me"
        match = re.search(r'(\d+)\s*(?:days?|din)', text)
        if match:
            days = int(match.group(1))
            return ref + timedelta(days=days)

        # Check ISO date pattern YYYY-MM-DD
        match = re.search(r'\b(\d{4})-(\d{2})-(\d{2})\b', text)
        if match:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))

        return None
