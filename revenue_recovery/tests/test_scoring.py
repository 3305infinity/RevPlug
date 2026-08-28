from datetime import datetime, timezone

import pytest

from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.scoring.expected_value import ExpectedValueScorer


@pytest.fixture
def utcnow():
    return datetime(2026, 8, 26, 9, 0, 0, tzinfo=timezone.utc)


def test_score_with_probability(utcnow):
    scorer = ExpectedValueScorer()
    item = RecoveryItem(
        id="ri_1",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_1",
        customer_id="C_1",
        amount_minor=10000,
        currency="INR",
        created_at=utcnow,
        recovery_probability=0.4,
    )
    assert scorer.score(item) == 4000


def test_score_zero_probability(utcnow):
    scorer = ExpectedValueScorer()
    item = RecoveryItem(
        id="ri_2",
        source_type=SourceType.RECEIVABLE,
        external_id="ext_2",
        customer_id="C_2",
        amount_minor=50000,
        currency="INR",
        created_at=utcnow,
        recovery_probability=0.0,
    )
    assert scorer.score(item) == 0


def test_score_full_probability(utcnow):
    scorer = ExpectedValueScorer()
    item = RecoveryItem(
        id="ri_3",
        source_type=SourceType.CHECKOUT_ABANDONMENT,
        external_id="ext_3",
        customer_id="C_3",
        amount_minor=25000,
        currency="INR",
        created_at=utcnow,
        recovery_probability=1.0,
    )
    assert scorer.score(item) == 25000


def test_score_requires_probability(utcnow):
    scorer = ExpectedValueScorer()
    item = RecoveryItem(
        id="ri_4",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_4",
        customer_id="C_4",
        amount_minor=10000,
        currency="INR",
        created_at=utcnow,
    )
    with pytest.raises(ValueError, match="recovery_probability must be set before scoring"):
        scorer.score(item)


def test_score_deterministic(utcnow):
    scorer = ExpectedValueScorer()
    item = RecoveryItem(
        id="ri_5",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_5",
        customer_id="C_5",
        amount_minor=12345,
        currency="INR",
        created_at=utcnow,
        recovery_probability=0.33,
    )
    first = scorer.score(item)
    second = scorer.score(item)
    assert first == second == 4073  # 12345 * 0.33 truncated to int
