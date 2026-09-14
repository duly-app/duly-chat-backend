from typing import Any

from src.chatbot.tools.registry import RegisteredTool, ToolRegistry
from src.chatbot.tools.tool import Tool


class SumTool(Tool):
    name = "sum"
    description = "Add a list of numbers together and return the total."
    input_schema = {
        "type": "object",
        "properties": {
            "numbers": {"type": "array", "items": {"type": "number"}},
        },
        "required": ["numbers"],
    }

    def run(self, **tool_input: Any) -> str:
        numbers: list[float] = tool_input.get("numbers", [])

        return str(sum(numbers))


def with_testing_tools(registry: ToolRegistry) -> ToolRegistry:
    """The production registry plus the test-only tools."""
    return {
        **registry,
        SumTool.name: RegisteredTool(schema=SumTool.schema(), create=SumTool),
    }
