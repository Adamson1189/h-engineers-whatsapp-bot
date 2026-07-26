"""
services/conversation_state.py

WHY THIS FILE EXISTS:
WhatsApp webhooks are stateless -- each incoming message is just "phone
number X said Y," with no built-in memory of what happened before. But
registration is a multi-step conversation ("what's your name?" -> "what's
your email?" -> ...). We need SOMETHING to remember "phone number X is
currently on step 2 of registration, and already told us their name is
Adam."

This file is that memory. It's a simple in-memory dictionary keyed by
phone number.

IMPORTANT LIMITATION (by design, for now):
This state lives in RAM only. If uvicorn restarts (a code change with
--reload, a crash, a deploy), everyone's in-progress conversation is lost
and they'd need to start over. That's an acceptable tradeoff to get the
core registration logic built and proven first. In a later phase, we can
move this to the database (a ConversationState table) or Redis so it
survives restarts -- swapping the storage backend won't require changing
any of the conversation logic itself, only this file.
"""

from dataclasses import dataclass, field


@dataclass
class ConversationState:
    step: str = "main_menu"  # which step of which flow the user is on
    data: dict = field(default_factory=dict)  # answers collected so far


# phone_number (str) -> ConversationState
_sessions: dict[str, ConversationState] = {}


def get_session(phone_number: str) -> ConversationState:
    """Returns the existing session for this phone number, or creates a
    fresh one (defaulting to the main menu) if this is a new conversation."""
    if phone_number not in _sessions:
        _sessions[phone_number] = ConversationState()
    return _sessions[phone_number]


def reset_session(phone_number: str) -> None:
    """Wipes a phone number's session, returning them to the main menu.
    Used after completing or cancelling a flow."""
    _sessions[phone_number] = ConversationState()
