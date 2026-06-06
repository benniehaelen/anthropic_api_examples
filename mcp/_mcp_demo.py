"""
Shared helper for the MCP (Model Context Protocol) example.

MCP is an open standard for connecting models to external tools and data. Here we run a small
**local MCP server** (`server.py`) as a subprocess over stdio, list its tools, wrap them with the
Anthropic SDK's MCP helper, and let the SDK tool runner drive the agentic loop — so Claude uses
MCP-provided tools exactly like native ones.

The MCP client path is **async** (subprocess + `anyio`), so `run_query` is a coroutine: `await`
it in a notebook, or `asyncio.run(...)` it in a script (see `run_mcp.py`).

Requires `pip install "anthropic[mcp]" mcp`, and ANTHROPIC_API_KEY for the caller.
"""

import os
import sys

MODEL = "claude-sonnet-4-5"
SERVER_PATH = os.path.join(os.path.dirname(__file__), "server.py")


async def run_query(question, server_path=SERVER_PATH, model=MODEL, max_tokens=1024):
    """Spawn the local MCP server, expose its tools to Claude, and answer `question`.

    Returns {"final": str, "transcript": [events], "tools": [tool names]}.
    """
    from anthropic import AsyncAnthropic
    from anthropic.lib.tools.mcp import async_mcp_tool
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    client = AsyncAnthropic()
    params = StdioServerParameters(command=sys.executable, args=[server_path])
    transcript, final = [], ""

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            tool_names = [t.name for t in listed.tools]
            tools = [async_mcp_tool(t, session) for t in listed.tools]

            runner = client.beta.messages.tool_runner(
                model=model, max_tokens=max_tokens,
                messages=[{"role": "user", "content": question}], tools=tools,
            )
            async for message in runner:
                for block in message.content:
                    if block.type == "text" and block.text.strip():
                        transcript.append({"kind": "text", "text": block.text})
                        final = block.text
                    elif block.type == "tool_use":
                        transcript.append({"kind": "tool_use", "name": block.name, "input": block.input})

    return {"final": final, "transcript": transcript, "tools": tool_names}
