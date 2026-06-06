"""
Shared building blocks for the self-correcting analyst agent (multi-agent orchestration).

Four roles cooperate to answer a data question:

  ORCHESTRATOR  decomposes the question into independent sub-analyses (a structured plan)
  ANALYST       writes and runs Python (code-execution server tool) to answer one sub-analysis
  CRITIC        reviews the analyst's finding and returns a pass/fail verdict (structured)
  SYNTHESIZER   combines the verified findings into a final report

Each sub-analysis runs an ANALYST → CRITIC self-correction loop: if the critic isn't satisfied,
the analyst revises with the critique, up to a cap. Control flow is plain Python (deterministic
orchestration); the model does the reasoning.

Imported by `analyst.ipynb`, `analyst_app.py`, and `run_analyst.py`.
"""

from typing import List

from pydantic import BaseModel, Field

MODEL = "claude-sonnet-4-5"

CODE_TOOL = {"type": "code_execution_20250825", "name": "code_execution"}
FILES_BETA = "files-api-2025-04-14"


# --------------------------------------------------------------------------- #
# Structured hand-offs between agents
# --------------------------------------------------------------------------- #
class Plan(BaseModel):
    subtasks: List[str] = Field(
        description="2-4 concrete, independently answerable sub-analyses for the question."
    )


class Verdict(BaseModel):
    passed: bool = Field(description="True if the finding correctly and rigorously answers the subtask.")
    issues: List[str] = Field(description="Specific problems found (empty if none).")
    suggestion: str = Field(description="Concrete guidance for revision (empty if passed).")


# --------------------------------------------------------------------------- #
# Sample dataset (generated, deterministic) — wildlife survey observations
# --------------------------------------------------------------------------- #
def build_observations_csv():
    """Deterministic observations CSV with planted data-quality issues for the agent to find."""
    sites = ["Ridge", "Marsh", "Creek", "Meadow"]
    species = ["red fox", "mule deer", "barred owl", "river otter"]
    rows = ["date,site,species,count,observer"]
    for day in range(1, 31):
        for i in range(4):  # four observations per day
            site = sites[(day + i) % 4]
            sp = species[(day * 2 + i) % 4]
            count = 1 + ((day * 3 + i * 7) % 6)
            observer = ["A. Singh", "B. Cole", "C. Ito"][(day + i) % 3]
            # Planted issues: a wild outlier and an empty count, for the agent to flag.
            if day == 13 and i == 2:
                count = 999            # outlier
            if day == 21 and i == 1:
                count = ""             # missing value
            rows.append(f"2026-04-{day:02d},{site},{sp},{count},{observer}")
    return "\n".join(rows) + "\n"


OBSERVATIONS_CSV = build_observations_csv()
DEFAULT_QUESTION = (
    "Summarize this wildlife survey: which species and site are most active, the trend over the "
    "month, and any data-quality problems."
)


def write_dataset(path="observations.csv"):
    with open(path, "w", newline="") as handle:
        handle.write(OBSERVATIONS_CSV)
    return path


def upload_dataset(client, path):
    with open(path, "rb") as handle:
        return client.beta.files.upload(file=handle)


# --------------------------------------------------------------------------- #
# Low-level helpers
# --------------------------------------------------------------------------- #
def _preview(csv_text, rows=6):
    return "\n".join(csv_text.splitlines()[:rows])


def _run_code(client, prompt, file_id, max_tokens=2048):
    """One code-execution turn over the uploaded dataset (handles pause_turn)."""
    messages = [{"role": "user", "content": [
        {"type": "text", "text": prompt},
        {"type": "container_upload", "file_id": file_id},
    ]}]
    while True:
        resp = client.beta.messages.create(
            model=MODEL, betas=[FILES_BETA], max_tokens=max_tokens,
            messages=messages, tools=[CODE_TOOL],
        )
        if resp.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": resp.content})
            continue
        return resp


def _text(resp):
    return "\n".join(b.text for b in resp.content if b.type == "text").strip()


def _stdout(resp):
    out = []
    for b in resp.content:
        if b.type == "bash_code_execution_tool_result":
            s = getattr(b.content, "stdout", "") or ""
            if s:
                out.append(s)
    return "\n".join(out).strip()


# --------------------------------------------------------------------------- #
# The four agents
# --------------------------------------------------------------------------- #
def orchestrate_plan(client, question, csv_text, max_subtasks=3):
    """ORCHESTRATOR: decompose the question into independent sub-analyses."""
    prompt = (
        "You are the lead analyst planning how to answer a question about a CSV dataset. "
        f"Break it into at most {max_subtasks} concrete, independently answerable sub-analyses "
        "(each a single clear analytical question). Do not answer them.\n\n"
        f"Question: {question}\n\nDataset preview (first rows):\n{_preview(csv_text)}"
    )
    plan = client.messages.parse(
        model=MODEL, max_tokens=512,
        messages=[{"role": "user", "content": prompt}], output_format=Plan,
    ).parsed_output
    return plan.subtasks[:max_subtasks]


def run_analyst(client, file_id, subtask, critique=None, max_tokens=3000):
    """ANALYST: answer one sub-analysis by writing and running Python on the dataset."""
    prompt = (
        "You are a data analyst. The CSV is in your sandbox. In THIS turn, immediately write and "
        "run a single Python script (pandas) that computes the answer and PRINTS the key numbers — "
        "do not stop after just listing or previewing the file. Then state a specific finding that "
        "is grounded in the printed numbers. Handle missing values and outliers explicitly and say "
        "how you treated them.\n\n"
        f"Sub-analysis: {subtask}"
    )
    if critique:
        prompt += f"\n\nA reviewer rejected your previous attempt:\n{critique}\nRevise accordingly."
    resp = _run_code(client, prompt, file_id, max_tokens=max_tokens)
    return {"finding": _text(resp), "stdout": _stdout(resp)}


def run_critic(client, subtask, finding):
    """CRITIC: verify the finding actually and rigorously answers the sub-analysis."""
    prompt = (
        "You are a reviewer. Decide whether the analyst's finding is CORRECT and SUPPORTED by the "
        "computed output. PASS it when: real numbers were computed and printed, the conclusion "
        "follows from them, and any obvious data-quality issue in scope (a clear outlier or missing "
        "value) is acknowledged. REJECT only when: there is no computed output (e.g. the analyst "
        "merely listed the file or stated intent), the numbers are wrong or unsupported, or a "
        "glaring data-quality problem is ignored. Do not demand analysis beyond the sub-analysis, "
        "and do not reject a correct finding for lacking extra breakdowns.\n\n"
        f"Sub-analysis: {subtask}\n\nAnalyst finding:\n{finding['finding']}\n\n"
        f"Computed output:\n{finding['stdout'] or '(none shown)'}"
    )
    return client.messages.parse(
        model=MODEL, max_tokens=512,
        messages=[{"role": "user", "content": prompt}], output_format=Verdict,
    ).parsed_output


def synthesize(client, question, results, max_tokens=2000):
    """SYNTHESIZER: combine the verified findings into a final report."""
    findings = "\n\n".join(
        f"### {r['subtask']}\n{r['finding']}" + ("" if r["verdict"].passed else "  _(unverified)_")
        for r in results
    )
    prompt = (
        "Combine these verified sub-analysis findings into a concise final report that answers the "
        "original question. Use short sections and call out any data-quality caveats.\n\n"
        f"Original question: {question}\n\n{findings}"
    )
    resp = client.messages.create(
        model=MODEL, max_tokens=max_tokens, messages=[{"role": "user", "content": prompt}],
    )
    return _text(resp)


# --------------------------------------------------------------------------- #
# Orchestration: plan -> (analyst <-> critic loop) per subtask -> synthesize
# --------------------------------------------------------------------------- #
def orchestrate(client, question, file_id, csv_text, max_subtasks=3, max_revisions=1, emit=None):
    """Run the full multi-agent, self-correcting analysis. Returns {final, results, trace}."""
    trace = []

    def _emit(kind, **data):
        event = {"kind": kind, **data}
        trace.append(event)
        if emit:
            emit(event)

    subtasks = orchestrate_plan(client, question, csv_text, max_subtasks=max_subtasks)
    _emit("plan", subtasks=subtasks)

    results = []
    for subtask in subtasks:
        _emit("subtask_start", subtask=subtask)
        critique = None
        finding = verdict = None
        for attempt in range(max_revisions + 1):
            finding = run_analyst(client, file_id, subtask, critique=critique)
            _emit("analyst", subtask=subtask, attempt=attempt + 1,
                  finding=finding["finding"], stdout=finding["stdout"])
            verdict = run_critic(client, subtask, finding)
            _emit("critic", subtask=subtask, attempt=attempt + 1,
                  passed=verdict.passed, issues=verdict.issues, suggestion=verdict.suggestion)
            if verdict.passed:
                break
            critique = "Issues: " + "; ".join(verdict.issues) + f"\nSuggestion: {verdict.suggestion}"
        results.append({"subtask": subtask, "finding": finding["finding"],
                        "stdout": finding["stdout"], "verdict": verdict})

    _emit("synthesizing")
    final = synthesize(client, question, results)
    _emit("final", report=final)
    return {"final": final, "results": results, "trace": trace}
