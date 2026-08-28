import pytest

from app.idempotency.store import IdempotencyStore, InMemoryIdempotencyStore


def test_fresh_event_is_not_processed():
    store = InMemoryIdempotencyStore()
    assert store.has_processed("evt_1") is False


def test_mark_processed_returns_true_on_next_check():
    store = InMemoryIdempotencyStore()
    store.mark_processed("evt_1")
    assert store.has_processed("evt_1") is True


def test_duplicate_mark_processed_raises():
    store = InMemoryIdempotencyStore()
    store.mark_processed("evt_1")
    with pytest.raises(ValueError, match="already processed"):
        store.mark_processed("evt_1")


def test_different_keys_are_independent():
    store = InMemoryIdempotencyStore()
    store.mark_processed("evt_1")
    assert store.has_processed("evt_1") is True
    assert store.has_processed("evt_2") is False
    store.mark_processed("evt_2")
    assert store.has_processed("evt_2") is True


def test_empty_key_is_allowed():
    store = InMemoryIdempotencyStore()
    store.mark_processed("")
    assert store.has_processed("") is True
    with pytest.raises(ValueError):
        store.mark_processed("")
