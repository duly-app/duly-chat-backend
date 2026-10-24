from dataclasses import dataclass
from typing import Any, TypeAlias

from anthropic.types import ToolUseBlock

DECLINED = "The user declined this action."


@dataclass(frozen=True)
class PendingAction:
    tool_use_id: str
    name: str
    input: dict[str, Any]

    @classmethod
    def of(cls, call: ToolUseBlock) -> "PendingAction":
        return cls(
            tool_use_id=call.id,
            name=call.name,
            input=dict(call.input) if isinstance(call.input, dict) else {},
        )


@dataclass(frozen=True)
class Decision:
    """What the user chose for a pending action."""

    approved: bool
    reason: str = ""

    @property
    def declined_content(self) -> str:
        """What the model is told when the user says no."""
        return f"{DECLINED} {self.reason}".strip() if self.reason else DECLINED


CallId: TypeAlias = str
Decisions: TypeAlias = dict[CallId, Decision]
