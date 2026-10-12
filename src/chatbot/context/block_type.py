from enum import Enum


class BlockType(str, Enum):
    """Types of context blocks."""

    SYSTEM = "system"
    USER_RULES = "user_rules"
    SAFETY = "safety"
