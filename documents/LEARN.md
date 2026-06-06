# Learn — Documents (retrieval-augmented search)

A study sheet for the `documents/` example. Pair it with the notebook
([`document_search.ipynb`](document_search.ipynb)), the Streamlit app
([`search_app.py`](search_app.py)), and the CLI ([`run_search.py`](run_search.py)).

**Where this fits in the CCA exam:** primarily **Context & Reliability** (15%) — managing a corpus
that won't fit in context — with strong ties to **Agentic Architecture** (27%, the RAG pipeline)
and **Tool Design & MCP Integration** (18%). See the [STUDY_GUIDE](../STUDY_GUIDE.md).

## Learning objectives

- Explain the RAG pipeline: ingest → chunk → embed → retrieve top-k → answer with citations.
- Justify **why retrieval** (vs. stuffing everything into the 1M context window).
- Use an embeddings provider (Voyage) correctly, including the `query` vs `document` distinction.
- Map retrieved chunks to citations using a **custom-content document**.

## Key concepts

- **No Anthropic embeddings endpoint.** Retrieval needs vectors, so this topic uses **Voyage AI**
  (the provider Anthropic recommends) — a second API key (`VOYAGE_API_KEY`).
- **Chunking** sets citation/retrieval granularity. Sentence-aware chunks with a small overlap
  keep facts that straddle a boundary retrievable.
- **`input_type` matters:** embed the corpus with `input_type="document"` and the query with
  `input_type="query"` — Voyage uses different internal prompts for each, improving retrieval.
- **Ranking:** cosine similarity between the query vector and chunk vectors → top-k. Those top-k
  *are* your "search results."
- **Grounding the answer:** send the top-k chunks as one **custom-content document** (each chunk a
  content block) with citations enabled. Citations come back as `content_block_location`, whose
  block index maps straight back to the retrieved passage → exact attribution.
- **Retrieval vs. context-stuffing:** for a large corpus, retrieving the relevant slice is
  cheaper, faster, and often *more* accurate than dumping everything into context.

## API cheat-sheet

```python
import voyageai, numpy as np
vo = voyageai.Client()                                   # reads VOYAGE_API_KEY
doc_vecs = np.array(vo.embed(chunks, model="voyage-3.5", input_type="document").embeddings)
q = np.array(vo.embed([query], model="voyage-3.5", input_type="query").embeddings[0])
top = np.argsort(-(doc_vecs @ q))[:5]                    # cosine (vectors ~unit) → top-k

# Ground the answer: top-k chunks as a citable custom-content document
document = {"type": "document",
            "source": {"type": "content", "content": [{"type": "text", "text": chunks[i]} for i in top]},
            "citations": {"enabled": True}}
```

## Common pitfalls

- **Re-embedding every run.** For a real corpus, persist embeddings (a vector DB) and re-embed
  only new/changed docs — re-embedding on each query wastes tokens and time.
- **Wrong `input_type`.** Embedding the query as a "document" (or vice-versa) quietly hurts
  ranking.
- **Chunks too big or too small.** Huge chunks dilute relevance and bloat the prompt; tiny chunks
  lose context. Tune `target_chars`/overlap to your content (prose vs. tables vs. transcripts).
- **Forgetting the second provider.** No `VOYAGE_API_KEY` → retrieval can't run. (Anthropic has no
  embeddings endpoint.)
- **Unsupported/scanned files.** `.docx` needs extraction (python-docx); scanned PDFs have no text.
- **Citations + Structured Outputs** are incompatible here too (it 400s) — same rule as `citations/`.

## Try it yourself

1. **Vary k.** Retrieve 3 vs 10 passages for the same query. How does the answer and its citation
   coverage change?
2. **Tune chunking.** Change `target_chars`/`overlap_chars` in `_documents.py` and observe
   retrieval quality on a long document.
3. **Add a Word doc.** Drop a `.docx` into the app and confirm its text is extracted, chunked, and
   citable.
4. **Semantic vs lexical.** Query with a synonym not present in the text (e.g. "canine" when the
   doc says "wolf") and confirm semantic retrieval still finds it.

## Check yourself

1. **Why does this topic need Voyage instead of the Anthropic API for retrieval?**
   <details><summary>Answer</summary>The Anthropic API has no embeddings endpoint. Retrieval needs
   vector embeddings, so a dedicated provider (Voyage, Anthropic's recommendation) supplies them.</details>

2. **Why embed the query and the documents with different `input_type` values?**
   <details><summary>Answer</summary>Voyage applies different internal prompts for `query` vs
   `document`, which improves retrieval relevance for search use-cases.</details>

3. **How does a citation map back to a specific retrieved passage?**
   <details><summary>Answer</summary>The top-k chunks are sent as a custom-content document (one
   block per chunk). Citations return as `content_block_location` with a block index that equals
   the position in the retrieved list → that passage.</details>

4. **When is retrieval preferable to putting all documents in the context window?**
   <details><summary>Answer</summary>When the corpus is large: retrieving the relevant slice is
   cheaper and faster, and focusing the model on relevant text is often more accurate than
   stuffing everything in (even with a 1M window).</details>

## Further reading

- [Embeddings (Anthropic guidance, recommends Voyage)](https://platform.claude.com/docs/en/build-with-claude/embeddings)
- [Voyage AI embeddings docs](https://docs.voyageai.com/docs/embeddings)
- [Citations — Claude API docs](https://platform.claude.com/docs/en/build-with-claude/citations)
