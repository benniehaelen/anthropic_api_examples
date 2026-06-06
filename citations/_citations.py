"""
Shared building blocks for the Citations example.

The Claude Citations feature grounds an answer in documents you provide: enable
`citations: {"enabled": True}` on `document` content blocks, ask a question, and Claude returns
its answer as a sequence of text blocks where each block either is plain prose or carries a
`citations` list. Each citation gives the exact source quote (`cited_text`), the document it came
from (`document_index` / `document_title`), and a precise location (character range for plain
text, page range for PDFs, block range for custom content).

This module supplies a small wildlife knowledge base, calls the API with citations enabled, and
renders the cited answer as an editorial HTML page with hover-preview footnotes and
click-to-jump references. Imported by `citation_app.py` and `citations_demo.ipynb`.
"""

from html import escape

# NOTE: the rest of this repo standardizes on claude-sonnet-4-5; we keep that here for
# consistency and cost. Citations are supported on all current models (except Haiku 3); switch
# to claude-opus-4-8 if you want the highest citation quality.
MODEL = "claude-sonnet-4-5"

# A tiny plain-text knowledge base. Plain-text documents are auto-chunked into sentences, so
# Claude can cite a single sentence or a span of them — ideal for footnote-style markers.
WILDLIFE_DOCS = [
    {
        "title": "Red fox",
        "text": (
            "The red fox (Vulpes vulpes) is the largest of the true foxes and the most widely "
            "distributed wild carnivore, found across the entire Northern Hemisphere. It thrives "
            "in a remarkable range of habitats, from arctic tundra and forests to farmland and "
            "the centers of large cities. The red fox is an opportunistic omnivore whose diet "
            "includes small rodents, rabbits, birds, insects, and fruit. Its coat is typically "
            "rusty red, with white underparts, black ears and legs, and a bushy white-tipped tail."
        ),
    },
    {
        "title": "Polar bear",
        "text": (
            "The polar bear (Ursus maritimus) is a large bear native to the Arctic sea ice and "
            "the surrounding coasts. It is the most carnivorous of the bear species, feeding "
            "almost exclusively on seals, which it hunts from the edge of the ice. Polar bears "
            "are insulated by a thick layer of blubber and a dense water-repellent coat, and "
            "their fur appears white to blend with the snow and ice. Unlike the wide-ranging red "
            "fox, the polar bear depends on sea ice to hunt and is highly vulnerable to its loss."
        ),
    },
    {
        "title": "Gray wolf",
        "text": (
            "The gray wolf (Canis lupus) is a social canid that lives and hunts in family groups "
            "called packs. Once found throughout the Northern Hemisphere, its range contracted "
            "sharply due to human persecution, though populations have recovered in parts of "
            "North America and Europe. Wolves are cooperative hunters that pursue large hoofed "
            "mammals such as deer, elk, and moose. A pack is typically led by a single breeding "
            "pair, and coordinated hunting lets wolves take prey far larger than themselves."
        ),
    },
]

DEFAULT_QUESTION = "How do the red fox and polar bear differ in their habitats and diets?"


# --------------------------------------------------------------------------- #
# API call
# --------------------------------------------------------------------------- #
def build_content(docs, question):
    """Build the user message content: one citable document block per doc, then the question."""
    content = []
    for doc in docs:
        content.append(
            {
                "type": "document",
                "source": {"type": "text", "media_type": "text/plain", "data": doc["text"]},
                "title": doc["title"],
                "citations": {"enabled": True},
                # Citations and prompt caching compose: cache the source documents. (Short docs
                # below the ~1024-token minimum won't actually cache, but the pattern is correct.)
                "cache_control": {"type": "ephemeral"},
            }
        )
    content.append({"type": "text", "text": question})
    return content


def ask(client, docs, question, max_tokens=1024):
    """Send the documents + question with citations enabled; return the response content blocks."""
    message = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": build_content(docs, question)}],
    )
    return message.content


# --------------------------------------------------------------------------- #
# Response normalization
# --------------------------------------------------------------------------- #
def _as_dict(obj):
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return obj


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


def location_label(citation):
    """Human-readable location for a citation, by document type."""
    ctype = citation.get("type")
    if ctype == "char_location":
        return f"chars {citation['start_char_index']}–{citation['end_char_index']}"
    if ctype == "page_location":
        start, end = citation["start_page_number"], citation["end_page_number"]
        return f"p. {start}" if end - start <= 1 else f"pp. {start}–{end - 1}"
    if ctype == "content_block_location":
        start, end = citation["start_block_index"], citation["end_block_index"]
        return f"block {start}" if end - start <= 1 else f"blocks {start}–{end - 1}"
    return ""


def _citation_key(citation):
    """Identity for de-duplicating citations that point at the same source span."""
    return (
        citation.get("document_index"),
        citation.get("type"),
        citation.get("start_char_index"),
        citation.get("end_char_index"),
        citation.get("start_page_number"),
        citation.get("end_page_number"),
        citation.get("start_block_index"),
        citation.get("end_block_index"),
    )


# --------------------------------------------------------------------------- #
# HTML rendering (editorial page with hover footnotes + click-to-jump)
# --------------------------------------------------------------------------- #
_TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;0,9..144,900&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500&display=swap" rel="stylesheet">
<style>
  :root{--paper:#f4efe4;--paper-deep:#ebe3d2;--ink:#221c14;--ink-soft:#5b5141;--accent:#9a2515;--accent-soft:#c46a4a;--highlight:#f7e07a;}
  *{box-sizing:border-box;} html{scroll-behavior:smooth;}
  body{margin:0;background:var(--paper);color:var(--ink);font-family:'Newsreader',Georgia,serif;font-size:1.12rem;line-height:1.7;-webkit-font-smoothing:antialiased;}
  .wrap{max-width:680px;margin:0 auto;padding:36px 28px 60px;}
  .eyebrow{font-family:'Fraunces',serif;font-weight:600;font-size:.7rem;letter-spacing:.4em;text-transform:uppercase;color:var(--accent);margin:0 0 1rem;}
  h1{font-family:'Fraunces',serif;font-weight:900;font-size:clamp(1.9rem,5vw,2.7rem);line-height:1.04;letter-spacing:-.02em;margin:0 0 .5rem;}
  .standfirst{font-size:1.15rem;font-style:italic;color:var(--ink-soft);margin:0 0 1.6rem;}
  .rule{height:2px;background:var(--ink);width:52px;margin:0 0 2rem;}
  .answer{margin:0 0 1.2rem;}
  .answer.dropcap::first-letter{font-family:'Fraunces',serif;font-weight:900;font-size:3.4rem;line-height:.78;float:left;padding:.06em .12em 0 0;color:var(--accent);}
  .cite{position:relative;cursor:pointer;font-family:'Fraunces',serif;border:none;background:none;padding:0;font-size:inherit;color:inherit;}
  .cite sup{color:var(--accent);font-weight:600;font-size:.62em;padding:0 .06em;border-radius:3px;transition:color .18s,background .18s;}
  .cite:hover sup,.cite:focus-visible sup{background:var(--accent);color:var(--paper);outline:none;}
  .tip{position:absolute;bottom:130%;left:50%;transform:translateX(-50%) translateY(6px);width:260px;background:var(--ink);color:var(--paper);font-family:'Newsreader',serif;font-size:.84rem;font-style:normal;line-height:1.5;text-align:left;padding:.8rem .95rem;border-radius:8px;box-shadow:0 14px 34px rgba(34,28,20,.32);opacity:0;pointer-events:none;transition:opacity .2s,transform .2s;z-index:20;}
  .tip::after{content:'';position:absolute;top:100%;left:50%;transform:translateX(-50%);border:7px solid transparent;border-top-color:var(--ink);}
  .tip .tip-src{display:block;font-family:'Fraunces',serif;font-weight:600;font-size:.64rem;letter-spacing:.14em;text-transform:uppercase;color:var(--accent-soft);margin-bottom:.3rem;}
  .cite:hover .tip,.cite:focus-visible .tip{opacity:1;transform:translateX(-50%) translateY(0);}
  .refs{margin-top:2.6rem;padding-top:1.4rem;border-top:2px solid var(--ink);}
  .refs h2{font-family:'Fraunces',serif;font-weight:600;font-size:.74rem;letter-spacing:.36em;text-transform:uppercase;color:var(--ink-soft);margin:0 0 1.2rem;}
  .ref{display:flex;gap:.8rem;font-size:.94rem;line-height:1.5;padding:.7rem .8rem;margin:0 -.8rem;border-radius:8px;scroll-margin-top:20vh;transition:background .4s;}
  .ref .num{font-family:'Fraunces',serif;font-weight:600;color:var(--accent);flex-shrink:0;}
  .ref .body{color:var(--ink-soft);} .ref .body cite{color:var(--ink);font-style:italic;}
  .ref .quote{color:var(--ink);} .ref .loc{font-size:.8rem;color:var(--ink-soft);}
  .ref .back{display:inline-block;margin-left:.5rem;color:var(--accent);text-decoration:none;font-family:'Fraunces',serif;font-weight:600;opacity:0;transform:translateX(-4px);transition:opacity .3s,transform .3s;pointer-events:none;}
  .ref.lit{background:var(--highlight);} .ref.lit .body,.ref.lit .body cite{color:var(--ink);}
  .ref.lit .back{opacity:1;transform:translateX(0);pointer-events:auto;} .ref.lit .back:hover{text-decoration:underline;}
  .empty{font-style:italic;color:var(--ink-soft);}
  footer{margin-top:2.4rem;font-size:.78rem;font-style:italic;color:var(--ink-soft);}
  ::selection{background:var(--highlight);color:var(--ink);}
</style></head><body><div class="wrap">
  <p class="eyebrow">Grounded answer · Claude Citations</p>
  <h1>{{TITLE}}</h1>
  <p class="standfirst">{{QUESTION}}</p>
  <div class="rule"></div>
  <p class="answer dropcap">{{ANSWER}}</p>
  <section class="refs"><h2>References</h2>{{REFS}}</section>
  <footer>Every red number is a real API citation: hover to preview the exact source text, click to jump to the reference.</footer>
</div>
<script>
  const markers=document.querySelectorAll('.cite');
  const refs=document.querySelectorAll('.ref');
  let litTimer=null;
  markers.forEach((m)=>{
    m.addEventListener('click',()=>{
      const target=document.getElementById('ref-'+m.dataset.ref);
      if(!target) return;
      target.scrollIntoView({behavior:'smooth',block:'center'});
      refs.forEach(r=>r.classList.remove('lit'));
      clearTimeout(litTimer);
      target.classList.add('lit');
      litTimer=setTimeout(()=>target.classList.remove('lit'),4000);
    });
  });
  document.querySelectorAll('.ref .back').forEach((b)=>{
    b.addEventListener('click',()=>refs.forEach(r=>r.classList.remove('lit')));
  });
</script></body></html>"""


def render_html(question, content):
    """Render Claude's cited answer as a standalone editorial HTML page (string)."""
    blocks = text_blocks(content)

    refs = []  # ordered list of (number, citation)
    key_to_num = {}
    ref_first_marker = {}
    marker_count = 0

    def number_for(citation):
        key = _citation_key(citation)
        if key not in key_to_num:
            key_to_num[key] = len(refs) + 1
            refs.append((len(refs) + 1, citation))
        return key_to_num[key]

    answer_parts = []
    for block in blocks:
        answer_parts.append(escape(block["text"]))
        for citation in block["citations"]:
            num = number_for(citation)
            marker_count += 1
            marker_id = f"m{marker_count}"
            ref_first_marker.setdefault(num, marker_id)
            src = escape(citation.get("document_title") or "Source")
            loc = location_label(citation)
            quoted = escape(citation.get("cited_text", ""))
            tip = (
                f'<span class="tip"><span class="tip-src">{src} · {loc}</span>{quoted}</span>'
            )
            answer_parts.append(
                f'<button class="cite" id="{marker_id}" data-ref="{num}" '
                f'aria-label="See reference {num}"><sup>{num}</sup>{tip}</button>'
            )
    answer_html = "".join(answer_parts) or '<span class="empty">No answer was returned.</span>'

    if refs:
        ref_rows = []
        for num, citation in refs:
            src = escape(citation.get("document_title") or "Source")
            loc = location_label(citation)
            quoted = escape(citation.get("cited_text", ""))
            back = ref_first_marker.get(num, "")
            ref_rows.append(
                f'<div class="ref" id="ref-{num}"><span class="num">{num}.</span>'
                f'<span class="body"><cite>{src}</cite> <span class="loc">({loc})</span><br>'
                f'<span class="quote">“{quoted}”</span>'
                f'<a class="back" href="#{back}" aria-label="Return to citation {num}">↩</a>'
                f"</span></div>"
            )
        refs_html = "".join(ref_rows)
    else:
        refs_html = '<p class="empty">Claude did not cite any sources for this answer.</p>'

    return (
        _TEMPLATE.replace("{{TITLE}}", "A Cited Answer")
        .replace("{{QUESTION}}", escape(question))
        .replace("{{ANSWER}}", answer_html)
        .replace("{{REFS}}", refs_html)
    )
