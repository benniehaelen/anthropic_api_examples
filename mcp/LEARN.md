# Learn — MCP (Model Context Protocol)

A study sheet for the `mcp/` example. Pair it with the notebook ([`mcp_demo.ipynb`](mcp_demo.ipynb))
and the CLI ([`run_mcp.py`](run_mcp.py)). The server is [`server.py`](server.py).

**Where this fits in the CCA exam:** the **MCP** half of **Tool Design & MCP Integration** (18%) —
connecting Claude to external tools/data through a standard interface. See the
[STUDY_GUIDE](../STUDY_GUIDE.md).

## Learning objectives

- Explain what MCP is and why it exists (a standard tool/data interface, not a new execution model).
- Stand up a **local MCP server** and connect Claude to its tools via the SDK + tool runner.
- Distinguish **local (stdio)** servers from **remote (`mcp_servers`)** connections.
- Recognize that MCP tools run through the same tool-use loop as native tools.

## Key concepts

- **MCP = a standard.** A server exposes **tools**, **resources**, and **prompts**; any MCP client
  (Claude, IDEs, other apps) can consume them. Write a tool once, reuse it everywhere.
- **Two connection styles:**
  - **Local stdio server** — you launch a server process and talk over stdin/stdout. Best for
    self-contained tools, local data, and full control. *(this example)*
  - **Remote server** — the API connects to a hosted MCP server via the `mcp_servers` request
    parameter (needs a URL, possibly auth).
- **SDK MCP helpers** adapt MCP to Anthropic types: `async_mcp_tool(tool, session)` (or sync
  `mcp_tool`) turns an MCP tool into one the **tool runner** can call; `mcp_message` /
  `mcp_resource_to_content` bring MCP prompts/resources into a request.
- **Same loop as `tool_use/`.** Once adapted, MCP tools flow through the ordinary tool-use loop —
  MCP changes *where tools come from*, not how they execute.
- **The client path is async** (subprocess + anyio): `await run_query(...)` in a notebook,
  `asyncio.run(...)` in a script.

## API cheat-sheet

```python
# --- a local MCP server (FastMCP) ---
from mcp.server.fastmcp import FastMCP
server = FastMCP("my-tools")

@server.tool()
def get_species_info(name: str) -> str:
    "Return a blurb about a species."
    return LOOKUP[name]

if __name__ == "__main__":
    server.run()          # stdio transport

# --- connecting Claude to it (async) ---
from anthropic import AsyncAnthropic
from anthropic.lib.tools.mcp import async_mcp_tool
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

params = StdioServerParameters(command=sys.executable, args=["server.py"])
async with stdio_client(params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        listed = await session.list_tools()
        tools = [async_mcp_tool(t, session) for t in listed.tools]
        runner = AsyncAnthropic().beta.messages.tool_runner(
            model="claude-sonnet-4-5", max_tokens=1024, tools=tools,
            messages=[{"role": "user", "content": "..."}])
        async for message in runner:
            ...

# --- or a remote MCP server, no client wiring ---
client.beta.messages.create(
    model="claude-sonnet-4-5", max_tokens=1024,
    messages=[{"role": "user", "content": "..."}],
    mcp_servers=[{"type": "url", "url": "https://.../mcp", "name": "tools"}],
    betas=["mcp-client-2025-04-04"])
```

## Common pitfalls

- **Forgetting it's async.** `asyncio.run()` in scripts; top-level `await` in notebooks. Don't call
  `asyncio.run` inside an already-running loop (e.g. Jupyter) — it errors.
- **`load_dotenv()` not finding `.env`.** python-dotenv searches from the *calling file's*
  directory — run from the repo (where `.env` lives) or pass the key explicitly.
- **Missing dependency.** Needs `pip install "anthropic[mcp]" mcp` (Python 3.10+).
- **Server not initialized.** Call `await session.initialize()` before `list_tools()`.
- **Confusing local vs remote.** Use the SDK helpers for local/stdio servers; use `mcp_servers`
  for hosted ones — they're different code paths.

## Try it yourself

1. **Run it:** `run_mcp.py -q "Compare the red fox and gray wolf, with sighting counts."` and watch
   which MCP tools get called.
2. **Add a tool** to `server.py` (a new `@server.tool()` function) and ask a question that needs it
   — no client change required.
3. **Inspect discovery:** print `session.list_tools()` to see the schemas the server advertises.
4. **Think remote:** sketch how you'd swap the local server for a hosted one via `mcp_servers`.

## Check yourself

1. **What does MCP standardize, and what does that buy you?**
   <details><summary>Answer</summary>A uniform interface for exposing tools, resources, and prompts
   from a server to any MCP-aware client. Write a tool/server once and reuse it across Claude, IDEs,
   and other apps — no per-app reimplementation.</details>

2. **Local stdio server vs the `mcp_servers` parameter — when each?**
   <details><summary>Answer</summary>Local stdio (SDK helpers) for self-contained tools, local data,
   and connection control. `mcp_servers` to let the API connect to a hosted/remote MCP server by
   URL.</details>

3. **Once you've adapted MCP tools, how do they execute?**
   <details><summary>Answer</summary>Through the ordinary tool-use loop (like `tool_use/`) — the tool
   runner calls them and feeds results back. MCP only changes where the tools come from.</details>

4. **Why is there no Streamlit app for this topic?**
   <details><summary>Answer</summary>The MCP client is async and launches the server as a
   subprocess; driving that cleanly from Streamlit's synchronous rerun model is awkward, so the
   topic ships a notebook + CLI instead.</details>

## Further reading

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Tool use overview — Claude API docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)
