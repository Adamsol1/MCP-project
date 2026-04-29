"""ElicitationStore — in-memory store for MCP elicitation requests.

When an MCP tool calls ctx.elicit(), the elicitation_callback parks a question
here and blocks on an asyncio.Event. The frontend polls collection-status, sees
the pending elicitation, shows a modal, and POSTs the user's choice back.
Responding resolves the Event and unblocks the agent.
"""

import asyncio
import logging
from dataclasses import dataclass, field

logger = logging.getLogger("app")


@dataclass
class PendingElicitation:
    session_id: str
    message: str
    options: list[str]
    _event: asyncio.Event = field(default_factory=asyncio.Event, repr=False)
    _response: str | None = field(default=None, repr=False)

    def to_dict(self) -> dict:
        return {"message": self.message, "options": self.options}

    def respond(self, choice: str) -> None:
        self._response = choice
        self._event.set()

    async def wait(self) -> str:
        await self._event.wait()
        return self._response or self.options[0]


class ElicitationStore:
    """Singleton store — one pending elicitation per session at a time.

    Also tracks which sessions have already received a provider-switch warning
    so the classified-content elicitation fires at most once per session.
    """

    def __init__(self) -> None:
        self._pending: dict[str, PendingElicitation] = {}
        self._warned: set[str] = set()

    def create(self, session_id: str, message: str, options: list[str]) -> PendingElicitation:
        elicitation = PendingElicitation(session_id=session_id, message=message, options=options)
        self._pending[session_id] = elicitation
        logger.info(f"[Elicitation] Created for session {session_id}: {message!r}")
        return elicitation

    def get(self, session_id: str) -> PendingElicitation | None:
        return self._pending.get(session_id)

    def respond(self, session_id: str, choice: str) -> bool:
        elicitation = self._pending.pop(session_id, None)
        if elicitation is None:
            return False
        elicitation.respond(choice)
        logger.info(f"[Elicitation] Responded for session {session_id}: {choice!r}")
        return True

    def has_warned(self, session_id: str) -> bool:
        return session_id in self._warned

    def mark_warned(self, session_id: str) -> None:
        self._warned.add(session_id)
        logger.info(f"[Elicitation] Session {session_id} marked as warned")


_store = ElicitationStore()


def get_elicitation_store() -> ElicitationStore:
    return _store
