# Glossary

Key terms used across this repo and the Claude API, with a pointer to the topic that demonstrates
each. See the [STUDY_GUIDE](STUDY_GUIDE.md) for how it all maps to the certification.

## Messages & content

- **Message** — one turn in a conversation: a `role` (`user`/`assistant`) and `content`.
- **Content block** — an item in a message's `content` list: `text`, `image`, `document`,
  `tool_use`, `tool_result`, `container_upload`, etc. You interleave them. *(all topics)*
- **System prompt** — top-level instructions (`system`), separate from the conversation. Keep it
  frozen for caching. *(prompt_caching)*
- **`max_tokens`** — hard cap on the response length. Stream for large values. *(all)*
- **`stop_reason`** — why the turn ended: `end_turn`, `tool_use`, `pause_turn`, `max_tokens`.
- **Streaming** — receive the response incrementally (`client.messages.stream`). *(vision, citations)*
- **Token** — the unit of text the model processes/bills. Context window = max tokens per request.

## Vision

- **Image block** — an image in `content`, sourced by **URL** (Claude fetches it) or **base64**
  (you send bytes). *(vision)*
- **EXIF / GPS** — file metadata (incl. coordinates) the model never sees; read it yourself.
  *(vision: precise location vs the model's region estimate)*

## Tools

- **Client tool** — a tool *you* implement: Claude emits `tool_use`, you run it and return a
  `tool_result`, in a loop. *(tool_use)*
- **Server tool** — a tool Anthropic runs (e.g. **code execution**, web search); no client loop.
  *(code_execution)*
- **`tool_use` / `tool_result`** — the request for a call (name + input + id) and your reply
  (matched by `tool_use_id`, optionally `is_error`). *(tool_use)*
- **`tool_choice`** — `auto` / `any` / a forced `{type:"tool", name}`. *(tool_use)*
- **Tool runner** — SDK helper (`@beta_tool` + `client.beta.messages.tool_runner`) that runs the
  agentic loop for you. *(tool_use)*
- **MCP (Model Context Protocol)** — a standard for connecting models to external tools/data;
  usable via SDK helpers (local servers) or the `mcp_servers` parameter (remote). *(mcp)*

## Code execution

- **Container** — the sandbox a code-execution request runs in; reuse it via `container=<id>`.
- **`container_upload`** — a content block referencing a Files-API `file_id` for the sandbox.
- **Files API** — upload/download files (`client.beta.files.*`, beta `files-api-2025-04-14`).
- **`pause_turn`** — a long server-tool turn paused; resend the response to continue. *(code_execution)*

## Citations & documents

- **Document block** — a `document` content block (plain text / PDF / custom content) you can
  enable citations on. *(citations)*
- **`citations: {enabled: true}`** — turn on grounded citations (all-or-none per request).
- **`cited_text`** — the exact source quote returned with a citation (free — no token cost).
- **Citation location** — `char_location` (text), `page_location` (PDF), `content_block_location`
  (custom content). *(citations, documents)*
- **RAG (retrieval-augmented generation)** — retrieve relevant chunks, then answer from them.
  *(documents)*
- **Embedding / cosine similarity** — vector representation of text / the score used to rank
  chunks against a query. Anthropic has no embeddings endpoint → **Voyage AI**. *(documents)*
- **Chunking** — splitting documents into retrievable pieces. *(documents)*

## Structured output

- **`messages.parse`** — SDK helper: pass a Pydantic model as `output_format`, get a validated
  `response.parsed_output`. *(structured_outputs)*
- **`output_config.format`** — the raw JSON-schema constraint on the response. *(structured_outputs)*
- **Strict tool** — `"strict": True` on a tool's `input_schema` for guaranteed-valid arguments.

## Prompt caching

- **Prompt caching** — reuse a stable prompt **prefix** across requests at ~0.1× input price.
- **`cache_control`** — `{"type":"ephemeral"}` breakpoint marking a cacheable prefix (5-min TTL;
  `"ttl":"1h"` for 1 hour). *(prompt_caching)*
- **Breakpoint** — where a cache prefix ends (max 4 per request). Render order `tools → system →
  messages`.
- **`cache_creation_input_tokens` / `cache_read_input_tokens`** — tokens written (~1.25×) / read
  (~0.1×) this request. `input_tokens` is the uncached remainder.
- **Silent invalidator** — volatile content (timestamp, UUID) before a breakpoint that defeats the
  cache. *(prompt_caching)*

## Models & reasoning

- **Effort** — `output_config.effort` (`low`…`max`) controlling thinking depth / token spend.
- **Adaptive thinking** — `thinking: {type: "adaptive"}`; the model decides how much to think
  (Opus 4.6+, Sonnet 4.6).
- **Batch** — the Batches API: asynchronous processing at ~50% cost. *(gap)*
