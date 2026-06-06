# Learn — Citations (grounded answers)

A study sheet for the `citations/` example. Pair it with the notebook
([`citations_demo.ipynb`](citations_demo.ipynb)) and the Streamlit app
([`citation_app.py`](citation_app.py)).

**Where this fits in the CCA exam:** primarily **Context & Reliability** (15%) — making answers
verifiable and trustworthy — with a strong secondary tie to **Prompt Engineering & Structured
Output** (20%) via the citations-vs-structured-output trade-off. See the
[STUDY_GUIDE](../STUDY_GUIDE.md).

## Learning objectives

- Enable citations on document content blocks and read the cited response.
- Distinguish the three document types and their **citation location formats**.
- Explain why the Citations feature beats prompt-based "please quote your sources."
- Know the hard constraints: all-or-none, and **incompatible with Structured Outputs**.

## Key concepts

- **Enable per document:** `citations: {"enabled": True}` on each `document` block. It must be
  **all or none** across the documents in a request.
- **Three document types → three location types:**
  - Plain text → `char_location` (0-indexed char range, exclusive end)
  - PDF → `page_location` (1-indexed pages, exclusive end)
  - Custom content (a list of blocks) → `content_block_location` (0-indexed block range)
- **Response shape:** the answer is a sequence of text blocks; a block that makes a grounded
  claim carries a `citations` list. Each citation has `cited_text` (the exact source quote),
  `document_index`, `document_title`, and the location fields above.
- **`cited_text` is free** — it doesn't count toward output tokens, nor input tokens when passed
  back on later turns.
- **`title` / `context` are not citable** — they're passed to the model but never cited from.
- **Composes with prompt caching** — cache the source documents (`cache_control` on the document
  blocks); the citation blocks in the response are not themselves cached.

## API cheat-sheet

```python
doc = {
    "type": "document",
    "source": {"type": "text", "media_type": "text/plain", "data": "The grass is green."},
    "title": "Notes",
    "citations": {"enabled": True},
    "cache_control": {"type": "ephemeral"},   # citations + caching compose
}
resp = client.messages.create(model="claude-opus-4-8", max_tokens=1024,
    messages=[{"role": "user", "content": [doc, {"type": "text", "text": "What color is the grass?"}]}])

for block in resp.content:
    if block.type == "text" and getattr(block, "citations", None):
        for c in block.citations:
            print(block.text, "→", c.cited_text, c.document_title)
```

## Common pitfalls

- **Mixing citations on/off across documents** in one request → error. All or none.
- **Combining citations with Structured Outputs** (`output_config.format`) → **400**. They are
  fundamentally incompatible: citations interleave citation blocks with text, which a strict JSON
  schema can't represent. (Classic exam "which feature wins" trade-off.)
- **Scanned/image PDFs** have no extractable text → nothing to cite.
- **Unsupported formats as document blocks** — `.docx/.csv/.xlsx` aren't valid; convert to text.
- **Index conventions** — char indices are 0-indexed with exclusive end; page numbers are
  1-indexed with exclusive end. Off-by-one bugs hide here.

## Try it yourself

1. **Add a PDF** to the app and ask a question spanning it and a text doc — note the different
   location types (`page_location` vs `char_location`) in the raw-citations expander.
2. **Inspect the objects** in the notebook: print `cited_text`, `document_index`, and the
   location fields for every citation.
3. **Trigger the constraint:** try enabling citations on only one of two documents (expect an
   error), then add `output_config.format` alongside citations (expect a 400).
4. **Cache it:** add a long document with `cache_control` and confirm
   `usage.cache_read_input_tokens` is non-zero on the second identical request.

## Check yourself

1. **Why use the Citations feature instead of asking Claude to quote sources in the prompt?**
   <details><summary>Answer</summary>Guaranteed valid pointers into the source (parsed, not
   model-typed), higher-quality/most-relevant quotes, and `cited_text` doesn't count toward output
   tokens — cheaper and more reliable than prompt-based quoting.</details>

2. **Name the three document types and their citation location formats.**
   <details><summary>Answer</summary>Plain text → `char_location` (char range); PDF →
   `page_location` (page range); custom content → `content_block_location` (block range).</details>

3. **You need both citations and a strict JSON schema for the output. What happens?**
   <details><summary>Answer</summary>You can't — enabling citations with `output_config.format`
   returns a 400. Pick one: cite, or constrain output shape.</details>

4. **Does `cited_text` count toward your token bill?**
   <details><summary>Answer</summary>No — not toward output tokens, and not toward input tokens
   when passed back on later turns.</details>

## Further reading

- [Citations — Claude API docs](https://platform.claude.com/docs/en/build-with-claude/citations)
- [Prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
