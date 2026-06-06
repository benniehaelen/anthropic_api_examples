# Learn — Structured outputs

A study sheet for the `structured_outputs/` example. Pair it with the notebook
([`structured_outputs.ipynb`](structured_outputs.ipynb)), the Streamlit extractor
([`extract_app.py`](extract_app.py)), and the CLI ([`run_extract.py`](run_extract.py)).

**Where this fits in the CCA exam:** the other half of **Prompt Engineering & Structured Output**
(20%) — getting reliable, schema-valid data out of the model. See the [STUDY_GUIDE](../STUDY_GUIDE.md).

## Learning objectives

- Get a **validated object** back with `client.messages.parse(output_format=<Pydantic>)`.
- Use the raw `output_config.format` (JSON schema) and know its strict-mode rules.
- Use `strict: True` on a **tool** to guarantee valid tool arguments.
- Recall the constraints: strict-schema limits, and the **citations incompatibility**.

## Key concepts

- **Three mechanisms, one idea — constrain the shape:**
  - `messages.parse(..., output_format=PydanticModel)` → `response.parsed_output` is a validated
    instance. *Recommended* for a structured final answer.
  - `output_config={"format": {"type": "json_schema", "schema": {...}}}` → the response text is
    guaranteed-valid JSON. The lower-level form `parse` builds on.
  - `"strict": True` on a tool's `input_schema` → Claude's `tool_use.input` is schema-valid. Use
    when it's *tool arguments* you need reliable, not the final answer.
- **Strict-schema rules:** set `additionalProperties: false`, list `required`, and use `enum` for
  bounded values — the strict validator **does not support numeric `minimum`/`maximum`**.
- **`cited_text` is free; structured output is cheap to parse** — but the two features don't mix
  (below).

## API cheat-sheet

```python
from pydantic import BaseModel

class Contact(BaseModel):
    name: str
    email: str
    wants_demo: bool

resp = client.messages.parse(
    model="claude-sonnet-4-5", max_tokens=512,
    messages=[{"role": "user", "content": "Jane (jane@co.com) asked for a demo."}],
    output_format=Contact,
)
contact = resp.parsed_output          # validated Contact instance

# Raw JSON schema (no Pydantic):
resp = client.messages.create(
    model="claude-sonnet-4-5", max_tokens=512,
    messages=[{"role": "user", "content": "..."}],
    output_config={"format": {"type": "json_schema", "schema": {
        "type": "object",
        "properties": {"name": {"type": "string"}, "score": {"type": "integer", "enum": [1, 2, 3]}},
        "required": ["name", "score"], "additionalProperties": False}}},
)
```

## Common pitfalls

- **`minimum`/`maximum` on integers** → 400 in strict mode. Use `enum`.
- **Missing `additionalProperties: false` / `required`** → weaker guarantees or errors.
- **Combining with citations** → 400. Citations interleave citation blocks with text, which the
  strict JSON shape can't express. Choose one.
- **Over-deep / overly permissive schemas.** Keep schemas tight; ambiguous shapes invite drift.
- **Using structured outputs when you wanted tool arguments validated** — that's `strict: True` on
  the tool, not `output_config.format`.

## Try it yourself

1. **Typed extraction:** run `run_extract.py --sample` and read the JSON records — every one has
   the same shape.
2. **Edit the schema:** add a field (e.g. `weather: str | None`) to `SightingReport` in
   `_structured_outputs.py` and re-run — the new field is populated automatically.
3. **Raw vs parse:** run the notebook's `output_config.format` cell and compare it to the Pydantic
   path.
4. **Break it:** add `minimum`/`maximum` to the raw schema's integer and watch the 400 — then fix
   it with an `enum`.

## Check yourself

1. **What's the simplest way to get a validated Python object back from Claude?**
   <details><summary>Answer</summary>`client.messages.parse(..., output_format=PydanticModel)`,
   then read `response.parsed_output` — the SDK enforces the schema and returns an instance.</details>

2. **You need a *tool's* arguments to be schema-valid. Which feature?**
   <details><summary>Answer</summary>`"strict": True` on the tool's `input_schema` (not
   `output_config.format`, which constrains the final answer).</details>

3. **A strict integer field with `minimum: 1, maximum: 5` returns a 400. Fix?**
   <details><summary>Answer</summary>The strict validator doesn't support numeric min/max — use
   `"enum": [1, 2, 3, 4, 5]` instead.</details>

4. **Can you combine structured outputs with citations?**
   <details><summary>Answer</summary>No — enabling both returns a 400. Citations interleave
   citation blocks with text, incompatible with the strict JSON shape. Pick one per request.</details>

## Further reading

- [Structured outputs — Claude API docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
