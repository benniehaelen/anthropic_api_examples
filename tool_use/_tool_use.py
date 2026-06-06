"""
Shared building blocks for the tool-use (function calling) example.

Custom *client* tools are the core agentic primitive: you declare tools, Claude decides when to
call one, you execute it, and you feed the result back — looping until Claude has what it needs.
This is the opposite end from the `code_execution/` server tool (where Anthropic runs the code);
here *you* run the tools.

This module defines two small, self-contained tools (a safe calculator and a mock weather
lookup), a manual agentic loop that records a transcript, and tool-runner wrappers — so the
notebook, app, and CLI can demonstrate both the manual loop and the SDK's automatic runner.
"""

import ast
import operator

MODEL = "claude-sonnet-4-5"


# --------------------------------------------------------------------------- #
# Tool implementations (plain Python — this is the code you control)
# --------------------------------------------------------------------------- #
_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv, ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("unsupported expression")


def calculator(expression: str) -> str:
    """Safely evaluate a basic arithmetic expression (+ - * / // % ** and parentheses)."""
    return str(_eval(ast.parse(expression, mode="eval").body))


# A tiny static "weather service" — deterministic, no network (examples have no internet).
_WEATHER = {
    "paris": "18°C, cloudy", "london": "14°C, rain", "tokyo": "24°C, clear",
    "new york": "12°C, windy", "sydney": "27°C, sunny", "cairo": "33°C, sunny",
    "reykjavik": "6°C, sleet",
}


def get_weather(city: str) -> str:
    """Return mock current weather for a known city, or raise for an unknown one."""
    key = city.strip().lower()
    if key not in _WEATHER:
        raise KeyError(f"No weather for '{city}'. Known cities: {', '.join(sorted(_WEATHER))}.")
    return f"{city.title()}: {_WEATHER[key]}"


# --------------------------------------------------------------------------- #
# Tool schemas + dispatch (for the manual loop)
# --------------------------------------------------------------------------- #
TOOLS = [
    {
        "name": "calculator",
        "description": "Evaluate a basic arithmetic expression and return the numeric result.",
        "input_schema": {
            "type": "object",
            "properties": {"expression": {"type": "string", "description": "e.g. '18 * 9/5 + 32'"}},
            "required": ["expression"],
        },
    },
    {
        "name": "get_weather",
        "description": "Get the current weather for a city.",
        "input_schema": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "City name, e.g. 'Paris'."}},
            "required": ["city"],
        },
    },
]

_REGISTRY = {"calculator": calculator, "get_weather": get_weather}


def execute_tool(name, tool_input):
    """Run a tool by name; return (content_str, is_error). Errors are returned, not raised, so
    Claude can read them and recover."""
    func = _REGISTRY.get(name)
    if func is None:
        return f"Unknown tool: {name}", True
    try:
        return str(func(**tool_input)), False
    except Exception as exc:  # noqa: BLE001 — surface the error text back to the model
        return f"Error: {exc}", True


# --------------------------------------------------------------------------- #
# Manual agentic loop (records a transcript for display)
# --------------------------------------------------------------------------- #
def run_loop(client, user_message, max_turns=6):
    """Run the tool-use loop manually; return (final_text, transcript).

    transcript is a list of events: {"kind": "text"|"tool_call"|"tool_result", ...} in order.
    """
    messages = [{"role": "user", "content": user_message}]
    transcript = []
    final_text = ""

    for _ in range(max_turns):
        response = client.messages.create(
            model=MODEL, max_tokens=1024, tools=TOOLS, messages=messages,
        )
        for block in response.content:
            if block.type == "text" and block.text.strip():
                transcript.append({"kind": "text", "text": block.text})
                final_text = block.text

        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if response.stop_reason != "tool_use" or not tool_uses:
            break

        messages.append({"role": "assistant", "content": response.content})
        results = []
        for tu in tool_uses:
            content, is_error = execute_tool(tu.name, tu.input)
            transcript.append({"kind": "tool_call", "name": tu.name, "input": tu.input})
            transcript.append({"kind": "tool_result", "name": tu.name, "content": content,
                               "is_error": is_error})
            results.append({"type": "tool_result", "tool_use_id": tu.id,
                            "content": content, "is_error": is_error})
        messages.append({"role": "user", "content": results})

    return final_text, transcript


# The SDK also offers an automatic loop (`client.beta.messages.tool_runner` with `@beta_tool`
# functions) — see the notebook for that approach. This module keeps the manual loop because it
# exposes the step-by-step transcript the app and CLI render.
