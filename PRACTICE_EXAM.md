# Practice exam — scenario questions

A self-check mock for the [Claude Certified Architect](https://anthropic.skilljar.com/) (CCA)
exam, organized like the real thing: short **scenarios**, each with a few questions. Answers and
explanations are collapsed — decide first, then expand.

> **Unofficial.** Community practice, not real exam questions and not endorsed by Anthropic. The
> real exam is proctored and scenario-based; confirm scope on
> [Anthropic's training platform](https://anthropic.skilljar.com/). Each question is tagged with
> the domain it exercises (see [STUDY_GUIDE](STUDY_GUIDE.md)).

---

## Scenario 1 — Policy assistant over a document set

You're building an assistant that answers employee questions from ~40 policy PDFs. Leaders insist
every answer show exactly which policy and passage it came from, and the team wants the answer as
JSON `{answer, sources}` to render in their UI.

**Q1.** *(Prompt Eng. & Structured Output)* They ask you to enable **citations** and a strict
`output_config.format` JSON schema in the same request. What happens?
<details><summary>Answer</summary><b>It returns a 400 — citations and structured outputs are
mutually incompatible.</b> Citations interleave citation blocks with text, which a strict JSON
shape can't represent. Choose one: use citations for attribution and assemble any JSON yourself
from the response, or use structured output without citations.</details>

**Q2.** *(Context & Reliability)* 40 PDFs far exceed what you want in every prompt. What's the
right architecture?
<details><summary>Answer</summary><b>Retrieval (RAG):</b> chunk + embed the PDFs, retrieve the
top-k relevant chunks per question, and answer from those (with citations). Embeddings come from a
provider like Voyage — the Anthropic API has none. See <code>documents/</code>.</details>

**Q3.** *(Context & Reliability)* One 60-page handbook is referenced on almost every query. How do
you cut cost?
<details><summary>Answer</summary><b>Prompt-cache that handbook</b> (a <code>cache_control</code>
breakpoint on the document/system prefix). It's reused across requests, so reads come back at
~0.1× input price. See <code>prompt_caching/</code>.</details>

---

## Scenario 2 — Data-analysis assistant

Users upload CSVs and ask for cleaning, stats, and charts. You don't want to build or host a
Python runtime.

**Q4.** *(Agentic Architecture / Tool Design)* Which capability fits, and what do you implement
for the tool loop?
<details><summary>Answer</summary><b>The code-execution server tool</b> — Anthropic runs the code
in a sandbox. You implement <b>no</b> tool-result loop; the code Claude ran and its output come
back in the response. Attach the CSV via the Files API + a <code>container_upload</code> block.
See <code>code_execution/</code>.</details>

**Q5.** *(Context & Reliability)* A big job returns `stop_reason == "pause_turn"`. What do you do?
<details><summary>Answer</summary><b>Resume:</b> append the partial response to your messages and
call again, repeating until a real finish (e.g. <code>end_turn</code>). It paused a long-running
turn, it didn't fail.</details>

**Q6.** *(Tool Design)* The chart Claude saved needs to reach the user. How do you get it?
<details><summary>Answer</summary>Its <code>file_id</code> appears in the execution result blocks;
download it via the Files API (<code>client.beta.files.download</code>).</details>

---

## Scenario 3 — High-volume extraction pipeline

You must turn 500k support emails into rows of `{intent, sentiment, product, urgency}` overnight.

**Q7.** *(Prompt Eng. & Structured Output)* How do you guarantee each result is the right shape?
<details><summary>Answer</summary><b>Structured outputs</b> — <code>client.messages.parse</code>
with a Pydantic model (or raw <code>output_config.format</code>). You get validated objects with no
brittle parsing. See <code>structured_outputs/</code>.</details>

**Q8.** *(Context & Reliability)* It's an overnight batch, not interactive. How do you cut cost?
<details><summary>Answer</summary><b>The Batch API</b> — asynchronous processing at ~50% cost,
ideal for non-latency-sensitive bulk work.</details>

**Q9.** *(Prompt Eng. & Structured Output)* Your strict schema sets `urgency` as an integer with
`minimum: 1, maximum: 5` and the request 400s. Fix?
<details><summary>Answer</summary>The strict validator <b>doesn't support numeric
minimum/maximum</b>. Use <code>"enum": [1,2,3,4,5]</code> (and keep
<code>additionalProperties: false</code> + <code>required</code>).</details>

**Q10.** *(Models)* Which model tier is the natural default for cheap, high-volume extraction —
and how could a larger model still help?
<details><summary>Answer</summary><b>Haiku</b> (or Sonnet) for cost/latency on a simple, repetitive
task. A larger model could serve as a fallback for the few emails the small model flags as
low-confidence — a two-tier funnel.</details>

---

## Scenario 4 — Internal operations agent

An agent answers staff questions by calling your internal APIs (inventory lookup, ticket
creation) and doing unit conversions.

**Q11.** *(Tool Design)* Server tool or client tools?
<details><summary>Answer</summary><b>Client tools.</b> Your internal APIs and business logic run
on your side: declare the tools, execute the <code>tool_use</code> calls yourself, and return
<code>tool_result</code>s in a loop. See <code>tool_use/</code>.</details>

**Q12.** *(Tool Design)* An inventory lookup fails for an unknown SKU. How should the tool result
come back so the agent recovers gracefully?
<details><summary>Answer</summary>As a <code>tool_result</code> with <code>is_error: True</code> and
a helpful message — Claude reads it and adapts (e.g. asks for a valid SKU) instead of the run
crashing.</details>

**Q13.** *(Tool Design)* The API rejects your turn with a tool-result error. Two common causes?
<details><summary>Answer</summary>(1) The <code>tool_result.tool_use_id</code> doesn't match the
<code>tool_use.id</code>; (2) you didn't append the assistant turn (with its <code>tool_use</code>
blocks) before sending the results.</details>

**Q14.** *(Tool Design / MCP)* Ops wants to expose an existing **MCP** server's tools to the agent.
Is that possible?
<details><summary>Answer</summary>Yes — connect via the SDK's MCP helpers (or the
<code>mcp_servers</code> parameter) and feed those tools into the same tool runner. MCP is a
standard way to plug external tools/data into the model.</details>

---

## Scenario 5 — Cutting the bill on a long-running agent

An agent reuses a large system prompt + tool set across thousands of requests, but your caching
shows almost no hits.

**Q15.** *(Context & Reliability)* `cache_read_input_tokens` is 0 across identical-looking
requests. First thing to check?
<details><summary>Answer</summary>A <b>silent invalidator</b> in the prefix — most often a
timestamp/UUID, a non-deterministic JSON serialization, or a per-request flag <i>before</i> the
breakpoint. Diff the rendered prompt bytes between two requests. Also confirm the prefix exceeds
the model's minimum.</details>

**Q16.** *(Context & Reliability)* A teammate "fixes" it by interpolating the current date into the
system prompt header "so the model knows the date." Why is that bad, and what's the fix?
<details><summary>Answer</summary>The date changes every request, so the prefix changes and nothing
caches. Move dynamic content <b>after the last breakpoint</b> — into a <code>messages</code> block,
not the system prompt.</details>

**Q17.** *(Context & Reliability)* The prefix is ~3,000 tokens and caches on Sonnet 4.5 but not
after switching to Opus 4.8. Why?
<details><summary>Answer</summary>The minimum cacheable prefix is model-dependent: 1024 (Sonnet
4.5) vs <b>4096</b> (Opus 4.8). 3K is below Opus's minimum, so it silently won't cache. (Caches are
also model-scoped, so the switch itself resets them.)</details>

---

## Scenario 6 — Multimodal intake

A field app sends in photos (and occasionally short video clips) of equipment for triage.

**Q18.** *(Context & Reliability)* Engineers send full 4000×3000 photos and the token bill spikes.
Guidance?
<details><summary>Answer</summary>Image tokens scale with pixels (≈ width×height/750). Downscale
(~1568 px long edge) before sending — it cuts cost with no real loss in recognition. See
<code>vision/</code>.</details>

**Q19.** *(Context & Reliability)* They want to analyze a 2-minute clip. What's the catch and the
approach?
<details><summary>Answer</summary>The API has <b>no native video input</b>. Decode the clip into
sampled, timestamp-labeled frames spread across the <i>whole</i> clip and send them as images.
Sampling only the start misses later content. See <code>video/</code>.</details>

**Q20.** *(Prompt Eng. & Structured Output)* The triage output must be a confident-but-honest call.
What prompt-design choice reduces confident-wrong answers?
<details><summary>Answer</summary>Demand <b>calibrated</b> output: have the model cite the visual
evidence, list plausible alternatives, and assign an explicit confidence rating — so weak evidence
yields low confidence instead of a fluent wrong answer. (The <code>vision/</code> 1–4 rating
pattern.)</details>

---

## Note on coverage

This mock emphasizes the domains this repo teaches: **Prompt Engineering & Structured Output**,
**Context & Reliability**, **Tool Design & MCP**, and **Agentic Architecture**. The real exam also
covers **Claude Code Configuration** (the Claude Code CLI), which is out of scope here — study
Anthropic's Claude Code material for that domain.
