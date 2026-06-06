# Learn — Tool use (custom / client tools)

A study sheet for the `tool_use/` example. Pair it with the notebook
([`tool_use.ipynb`](tool_use.ipynb)), the Streamlit agent ([`agent_app.py`](agent_app.py)), and
the CLI ([`run_agent.py`](run_agent.py)).

**Where this fits in the CCA exam:** primarily **Tool Design & MCP Integration** (18%) and
**Agentic Architecture** (27%) — tool use is how an agent acts. See the [STUDY_GUIDE](../STUDY_GUIDE.md).

## Learning objectives

- Define a tool (name, description, JSON-schema inputs) and read a `tool_use` block.
- Run the **agentic loop**: execute the tool, return a `tool_result`, repeat until `end_turn`.
- Use the **SDK tool runner** for the automatic loop, and know when to hand-roll it instead.
- Handle multiple/parallel calls, force a tool with `tool_choice`, and report failures via
  `is_error`.

## Key concepts

- **Client tool = you run it.** Claude emits a `tool_use` block (name + input); your code executes
  it and returns a `tool_result` referencing the same `tool_use_id`. (Contrast the `code_execution/`
  *server* tool, which Anthropic runs with no loop for you.)
- **The loop.** While `stop_reason == "tool_use"`: append the assistant turn, execute each
  `tool_use`, append all `tool_result`s as one user message, call again. Stop on `end_turn`.
- **Tool schema** is plain JSON Schema under `input_schema`. Good `description`s matter — they're
  how Claude decides when and how to call.
- **Parallel calls.** A single turn may contain several `tool_use` blocks; execute them all and
  return all results together.
- **`tool_choice`** — `{"type":"auto"}` (default), `{"type":"any"}` (must use some tool), or
  `{"type":"tool","name":...}` (force one).
- **`is_error`** — return failures as `tool_result` with `is_error: True` so Claude can recover.
- **Tool runner** — `@beta_tool` on a typed function generates the schema from its signature +
  docstring; `client.beta.messages.tool_runner(...)` runs the whole loop and yields each message.

## API cheat-sheet

```python
TOOLS = [{"name": "get_weather", "description": "Get weather for a city.",
          "input_schema": {"type": "object",
                           "properties": {"city": {"type": "string"}}, "required": ["city"]}}]

messages = [{"role": "user", "content": "Weather in Paris?"}]
while True:
    resp = client.messages.create(model="claude-sonnet-4-5", max_tokens=1024,
                                  tools=TOOLS, messages=messages)
    if resp.stop_reason != "tool_use":
        break
    messages.append({"role": "assistant", "content": resp.content})
    results = []
    for b in resp.content:
        if b.type == "tool_use":
            out = run_my_tool(b.name, b.input)          # your code
            results.append({"type": "tool_result", "tool_use_id": b.id, "content": out})
    messages.append({"role": "user", "content": results})

# Or let the SDK do all of the above:
from anthropic import beta_tool
@beta_tool
def get_weather(city: str) -> str:
    "Get weather for a city. Args: city: City name."
    return lookup(city)
for msg in client.beta.messages.tool_runner(model="claude-sonnet-4-5", max_tokens=1024,
                                             tools=[get_weather], messages=messages):
    ...
```

## Common pitfalls

- **Mismatched `tool_use_id`.** The `tool_result` must echo the exact `tool_use.id`, or the API
  rejects the turn.
- **Forgetting to append the assistant turn** (with its `tool_use` blocks) before the results —
  the result must follow the call it answers.
- **Raising instead of returning errors.** A crashed tool ends the run; an `is_error` result lets
  Claude adapt.
- **Vague tool descriptions / loose schemas** → wrong tool, wrong arguments. Be specific; add
  `enum`/`format`; use `strict: True` when arguments must be exact.
- **No loop bound.** Always cap iterations to avoid a runaway loop.
- **Changing the tool set mid-conversation** breaks prompt caching (tools render at position 0).

## Try it yourself

1. **Watch the loop:** run `run_agent.py -q "Weather in Paris, and 18°C in Fahrenheit?"` and read
   the two tool calls + results before the final answer.
2. **Add a tool:** add a third tool (e.g. `word_count(text)`) to `_tool_use.py` — schema +
   implementation + registry entry — and ask a question that needs it.
3. **Runner vs manual:** run the notebook's tool-runner cell and compare it to `run_loop`.
4. **Force and fail:** force the calculator with `tool_choice`, and ask for an unknown city to see
   the `is_error` recovery.

## Check yourself

1. **What's the difference between a client tool (this topic) and the code-execution server tool?**
   <details><summary>Answer</summary>For a client tool, Claude requests a call and *you* execute it
   and return a `tool_result` in a loop. The code-execution server tool runs on Anthropic's side —
   there's no tool-result loop you implement.</details>

2. **You sent a `tool_result` but the API rejects the request. Most likely cause?**
   <details><summary>Answer</summary>The `tool_use_id` doesn't match the `tool_use` block, or you
   didn't append the assistant turn (with the `tool_use`) before the result.</details>

3. **A tool failed. How should you respond so Claude can recover?**
   <details><summary>Answer</summary>Return a `tool_result` with `is_error: True` and a helpful
   message, rather than raising — Claude reads it and tries another approach.</details>

4. **When is the SDK tool runner the wrong choice?**
   <details><summary>Answer</summary>When you need fine-grained control of the loop — approval
   gates, custom logging, conditional execution, or a custom transcript. Then hand-roll the loop.</details>

## Further reading

- [Tool use overview — Claude API docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)
- [Tool runner (Anthropic Python SDK)](https://github.com/anthropics/anthropic-sdk-python)
