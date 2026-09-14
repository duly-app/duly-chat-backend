from enum import Enum


class BlockType(str, Enum):
    """Types of context blocks."""

    SYSTEM = "system"
    TOOLS = "tools"
    USER_RULES = "user_rules"
    SAFETY = "safety"
