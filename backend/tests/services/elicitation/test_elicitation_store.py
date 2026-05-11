import asyncio

import pytest

from src.services.elicitation.elicitation_store import (
    ElicitationStore,
    PendingElicitation,
    get_elicitation_store,
)


def test_pending_elicitation_to_dict_exposes_only_ui_fields():
    pending = PendingElicitation(
        session_id="session-1",
        message="Classified content detected. Choose provider.",
        options=["local", "cloud"],
    )

    assert pending.to_dict() == {
        "message": "Classified content detected. Choose provider.",
        "options": ["local", "cloud"],
    }


@pytest.mark.asyncio
async def test_pending_elicitation_wait_returns_user_choice():
    pending = PendingElicitation(
        session_id="session-1",
        message="Choose provider",
        options=["local", "cloud"],
    )

    waiter = asyncio.create_task(pending.wait())
    await asyncio.sleep(0)
    pending.respond("cloud")

    assert await waiter == "cloud"


@pytest.mark.asyncio
async def test_pending_elicitation_wait_falls_back_to_first_option_for_empty_response():
    pending = PendingElicitation(
        session_id="session-1",
        message="Choose provider",
        options=["local", "cloud"],
    )

    waiter = asyncio.create_task(pending.wait())
    await asyncio.sleep(0)
    pending.respond("")

    assert await waiter == "local"


def test_store_replaces_pending_elicitation_per_session_and_respond_removes_it():
    store = ElicitationStore()

    first = store.create("session-1", "First message", ["local"])
    second = store.create("session-1", "Second message", ["cloud"])

    assert first is not second
    assert store.get("session-1") is second
    assert store.respond("session-1", "cloud") is True
    assert store.get("session-1") is None
    assert store.respond("session-1", "cloud") is False


def test_store_tracks_provider_warning_once_per_session():
    store = ElicitationStore()

    assert store.has_warned("session-1") is False

    store.mark_warned("session-1")

    assert store.has_warned("session-1") is True
    assert store.has_warned("other-session") is False


def test_get_elicitation_store_returns_singleton():
    assert get_elicitation_store() is get_elicitation_store()
