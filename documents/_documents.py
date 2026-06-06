"""
Shared building blocks for the document-search example.

A small retrieval-augmented search over a library of mixed-format documents:

    ingest (PDF / Word / text / markdown / CSV)  ->  extract text  ->  chunk
      ->  embed every chunk with Voyage AI  ->  embed the query, rank by cosine
      ->  send the top-k chunks to Claude with citations enabled
      ->  a grounded answer (cited back to the passages) + the ranked passages

Anthropic has no embeddings endpoint, so retrieval uses Voyage AI (the provider Anthropic
recommends). Requires both ANTHROPIC_API_KEY and VOYAGE_API_KEY. Imported by `search_app.py`,
`run_search.py`, and `document_search.ipynb`.
"""

import io
import os
import re
from html import escape

import numpy as np

MODEL = "claude-opus-4-8"        # answer model — matches the citations topic for citation quality
EMBED_MODEL = "voyage-3.5"       # Voyage embedding model (1024-dim)
SUPPORTED_EXTS = (".pdf", ".docx", ".txt", ".md", ".csv")


# --------------------------------------------------------------------------- #
# Ingestion
# --------------------------------------------------------------------------- #
def extract_text(data, filename):
    """Extract plain text from a document by extension. PDFs and Word need real parsers;
    text/markdown/CSV are decoded directly. Returns '' if nothing extractable."""
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages)
    if ext == ".docx":
        import docx

        document = docx.Document(io.BytesIO(data))
        return "\n\n".join(p.text for p in document.paragraphs)
    # .txt / .md / .csv / anything else: decode as text
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1", errors="replace")


def _split_oversized(sentence, limit):
    return [sentence[i : i + limit] for i in range(0, len(sentence), limit)]


def chunk_text(text, source, target_chars=900, overlap_chars=150):
    """Split text into overlapping, sentence-aware chunks of ~target_chars.

    Returns [{source, chunk_index, text}]. Newlines are flattened (PDF/Word text is often
    line-broken), then text is grouped by sentence up to the size target, with a small overlap
    so a fact spanning a chunk boundary is still retrievable.
    """
    flat = re.sub(r"\s+", " ", text).strip()
    if not flat:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", flat)

    chunks, current = [], ""
    for sentence in sentences:
        for piece in (_split_oversized(sentence, target_chars) if len(sentence) > target_chars else [sentence]):
            if current and len(current) + len(piece) + 1 > target_chars:
                chunks.append(current.strip())
                current = (current[-overlap_chars:] + " " + piece) if overlap_chars else piece
            else:
                current = (current + " " + piece).strip()
    if current.strip():
        chunks.append(current.strip())

    return [{"source": source, "chunk_index": i, "text": c} for i, c in enumerate(chunks)]


# --------------------------------------------------------------------------- #
# Embedding + retrieval (Voyage AI)
# --------------------------------------------------------------------------- #
_voyage_client = None


def _voyage():
    global _voyage_client
    if _voyage_client is None:
        import voyageai

        _voyage_client = voyageai.Client()  # reads VOYAGE_API_KEY
    return _voyage_client


def embed_texts(texts, input_type, model=EMBED_MODEL, batch_size=128):
    """Embed texts with Voyage. input_type is 'document' (for the corpus) or 'query'."""
    client = _voyage()
    vectors = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        vectors.extend(client.embed(batch, model=model, input_type=input_type).embeddings)
    return np.array(vectors, dtype="float32")


def build_library(files, model=EMBED_MODEL):
    """Ingest files into an embedded chunk library.

    `files` is a list of (filename, bytes). Returns a list of chunk dicts, each with an
    'embedding' (np.ndarray). Skipped files (no extractable text) are reported separately.
    """
    chunks, skipped = [], []
    for filename, data in files:
        text = extract_text(data, filename)
        file_chunks = chunk_text(text, filename)
        if file_chunks:
            chunks.extend(file_chunks)
        else:
            skipped.append(filename)

    if chunks:
        embeddings = embed_texts([c["text"] for c in chunks], "document", model)
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding
    return chunks, skipped


def retrieve(query, chunks, k=5, model=EMBED_MODEL):
    """Return the top-k chunks most similar to the query, each with a cosine 'score'."""
    if not chunks:
        return []
    query_vec = embed_texts([query], "query", model)[0]
    matrix = np.array([c["embedding"] for c in chunks])
    sims = matrix @ query_vec / (np.linalg.norm(matrix, axis=1) * np.linalg.norm(query_vec) + 1e-9)
    order = np.argsort(-sims)[:k]
    return [{**{key: chunks[i][key] for key in ("source", "chunk_index", "text")},
             "score": float(sims[i])} for i in order]


# --------------------------------------------------------------------------- #
# Cited answer (Claude)
# --------------------------------------------------------------------------- #
def answer(client, query, retrieved, max_tokens=2048):
    """Send the retrieved passages to Claude as one citable custom-content document.

    Each retrieved passage is a content block, so citations come back as
    `content_block_location` with a block index that maps straight to `retrieved[index]`.
    Returns the response content blocks.
    """
    document = {
        "type": "document",
        "source": {
            "type": "content",
            "content": [{"type": "text", "text": c["text"]} for c in retrieved],
        },
        "title": "Retrieved passages",
        "citations": {"enabled": True},
    }
    instruction = (
        "Answer the question using only the retrieved passages below, and cite the passages "
        "that support each claim. If the passages do not contain the answer, say so plainly.\n\n"
        f"Question: {query}"
    )
    message = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": [document, {"type": "text", "text": instruction}]}],
    )
    return message.content


def _as_dict(obj):
    if isinstance(obj, dict):
        return obj
    return obj.model_dump() if hasattr(obj, "model_dump") else obj


def text_blocks(content):
    """Normalize response content into [{text, citations: [dict, ...]}] for text blocks."""
    blocks = []
    for block in content:
        bdict = _as_dict(block)
        if bdict.get("type") != "text":
            continue
        citations = [_as_dict(c) for c in (bdict.get("citations") or [])]
        blocks.append({"text": bdict.get("text", ""), "citations": citations})
    return blocks


def answer_text(content):
    """Plain concatenated answer text (no markup)."""
    return "".join(b["text"] for b in text_blocks(content))


# --------------------------------------------------------------------------- #
# HTML rendering: cited answer with hover footnotes + ranked passages panel
# --------------------------------------------------------------------------- #
_CSS = """
  :root{--paper:#f4efe4;--paper-deep:#ebe3d2;--ink:#221c14;--ink-soft:#5b5141;--accent:#9a2515;--accent-soft:#c46a4a;--highlight:#f7e07a;}
  *{box-sizing:border-box;} html{scroll-behavior:smooth;}
  body{margin:0;background:var(--paper);color:var(--ink);font-family:'Newsreader',Georgia,serif;font-size:1.08rem;line-height:1.65;-webkit-font-smoothing:antialiased;}
  .wrap{max-width:680px;margin:0 auto;padding:28px 26px 50px;}
  .eyebrow{font-family:'Fraunces',serif;font-weight:600;font-size:.68rem;letter-spacing:.36em;text-transform:uppercase;color:var(--accent);margin:0 0 .8rem;}
  h1{font-family:'Fraunces',serif;font-weight:900;font-size:clamp(1.5rem,4vw,2.1rem);line-height:1.08;letter-spacing:-.02em;margin:0 0 1.2rem;}
  .answer{margin:0 0 1rem;}
  .cite{position:relative;cursor:pointer;font-family:'Fraunces',serif;border:none;background:none;padding:0;font-size:inherit;color:inherit;}
  .cite sup{color:var(--accent);font-weight:600;font-size:.62em;padding:0 .06em;border-radius:3px;transition:color .18s,background .18s;}
  .cite:hover sup,.cite:focus-visible sup{background:var(--accent);color:var(--paper);outline:none;}
  .tip{position:absolute;bottom:130%;left:50%;transform:translateX(-50%) translateY(6px);width:280px;background:var(--ink);color:var(--paper);font-family:'Newsreader',serif;font-size:.82rem;font-style:normal;line-height:1.5;text-align:left;padding:.8rem .95rem;border-radius:8px;box-shadow:0 14px 34px rgba(34,28,20,.32);opacity:0;pointer-events:none;transition:opacity .2s,transform .2s;z-index:20;}
  .tip::after{content:'';position:absolute;top:100%;left:50%;transform:translateX(-50%);border:7px solid transparent;border-top-color:var(--ink);}
  .tip .tip-src{display:block;font-family:'Fraunces',serif;font-weight:600;font-size:.62rem;letter-spacing:.12em;text-transform:uppercase;color:var(--accent-soft);margin-bottom:.3rem;}
  .cite:hover .tip,.cite:focus-visible .tip{opacity:1;transform:translateX(-50%) translateY(0);}
  .panel{margin-top:2.2rem;padding-top:1.2rem;border-top:2px solid var(--ink);}
  .panel h2{font-family:'Fraunces',serif;font-weight:600;font-size:.72rem;letter-spacing:.32em;text-transform:uppercase;color:var(--ink-soft);margin:0 0 1rem;}
  .passage{padding:.7rem .8rem;margin:0 -.8rem .3rem;border-radius:8px;scroll-margin-top:18vh;transition:background .4s;}
  .passage .head{font-family:'Fraunces',serif;font-size:.8rem;color:var(--ink-soft);margin-bottom:.25rem;}
  .passage .rank{color:var(--accent);font-weight:600;} .passage .src{color:var(--ink);} .passage .score{color:var(--ink-soft);}
  .passage .text{font-size:.92rem;color:var(--ink-soft);}
  .passage.lit{background:var(--highlight);} .passage.lit .text{color:var(--ink);}
  .empty{font-style:italic;color:var(--ink-soft);}
  ::selection{background:var(--highlight);color:var(--ink);}
"""

_TEMPLATE = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;0,9..144,900&family=Newsreader:opsz,wght@6..72,400;6..72,500&display=swap" rel="stylesheet">
<style>__CSS__</style></head><body><div class="wrap">
  <p class="eyebrow">Document search · Claude + Voyage</p>
  <h1>__QUERY__</h1>
  <p class="answer">__ANSWER__</p>
  <section class="panel"><h2>Retrieved passages (ranked)</h2>__PASSAGES__</section>
</div>
<script>
  const markers=document.querySelectorAll('.cite');const passages=document.querySelectorAll('.passage');let t=null;
  markers.forEach(m=>m.addEventListener('click',()=>{
    const target=document.getElementById(m.dataset.target);if(!target)return;
    target.scrollIntoView({behavior:'smooth',block:'center'});
    passages.forEach(p=>p.classList.remove('lit'));clearTimeout(t);
    target.classList.add('lit');t=setTimeout(()=>target.classList.remove('lit'),4000);
  }));
</script></body></html>"""


def render_html(query, content, retrieved):
    """Render the cited answer (hover footnotes, click-to-jump) + the ranked passages panel."""
    blocks = text_blocks(content)

    answer_parts = []
    for block in blocks:
        answer_parts.append(escape(block["text"]))
        for citation in block["citations"]:
            if citation.get("type") != "content_block_location":
                continue
            idx = citation.get("start_block_index", 0)
            rank = idx + 1
            passage = retrieved[idx] if 0 <= idx < len(retrieved) else {}
            src = escape(passage.get("source", "passage"))
            score = passage.get("score")
            score_txt = f" · score {score:.2f}" if score is not None else ""
            quoted = escape(citation.get("cited_text", ""))
            tip = (
                f'<span class="tip"><span class="tip-src">Passage {rank} · {src}{score_txt}</span>'
                f"{quoted}</span>"
            )
            answer_parts.append(
                f'<button class="cite" data-target="p{idx}" aria-label="See passage {rank}">'
                f"<sup>{rank}</sup>{tip}</button>"
            )
    answer_html = "".join(answer_parts) or '<span class="empty">No answer was returned.</span>'

    if retrieved:
        rows = []
        for i, passage in enumerate(retrieved):
            src = escape(passage.get("source", "passage"))
            score = passage.get("score", 0.0)
            snippet = escape(passage.get("text", ""))
            rows.append(
                f'<div class="passage" id="p{i}"><div class="head">'
                f'<span class="rank">#{i + 1}</span> · <span class="src">{src}</span> · '
                f'<span class="score">cosine {score:.3f}</span></div>'
                f'<div class="text">{snippet}</div></div>'
            )
        passages_html = "".join(rows)
    else:
        passages_html = '<p class="empty">No passages were retrieved.</p>'

    return (
        _TEMPLATE.replace("__CSS__", _CSS)
        .replace("__QUERY__", escape(query))
        .replace("__ANSWER__", answer_html)
        .replace("__PASSAGES__", passages_html)
    )
