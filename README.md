# verifiable-loop-mechanism

繁體中文說明見 [README.zh-TW.md](README.zh-TW.md).

A small, portable mechanism for running AI agents (Claude Code, Codex, others) semi-autonomously, where "is this round actually done?" is decided by a machine, not by the AI's feeling.

Built by a non-engineer for a one-person knowledge-base operation. Status: working draft, n=1, not peer-reviewed. See `paper.md` for the full write-up.

## Who is this for, and when

**Who:** anyone running AI agents (Claude Code, Codex, etc.) on tasks that have an objective right or wrong, and who wants "done" decided by a machine instead of by the agent's feeling. You need to run one Python command (you do not need to write code; you can have the agent run it for you). Developers, technical-leaning knowledge workers, and one-person operators all fit, as long as the task itself is machine-checkable.

**When it fits:** deployment checks, file governance, board-read completeness, link integrity, tests passing, a string appearing the right number of times (for example a function defined exactly once).

**When it does not fit:** whether writing is good, whether a strategy is right, creative quality. Those have no objective grader; keep them on human or LLM-judge review.

**What it solves:** the three ways an AI fakes completion (false completion, loopmaxxing, and rules dropped when the context window is compacted). It turns "done" from the agent's feeling into a machine-verifiable fact.

## The idea in one line

Stop designing prompts; design the loop. A loop needs a goal, an action, and an objective stop. The objective stop here is a Worthy Condition: P0 (blocking) problem count == 0, checked by a script.

Adopted primitive: Yuta Tu, "Machine-Verifiable Completion for AI Agent Systems, G-T-W", 2026 preprint (n=1, not peer-reviewed). Source link omitted pending the author's permission.

## What's here

```
paper.md                     full write-up + comparison with the source paper
grader/grader.py             the shared Grader: runs a manifest of checks, emits a verdict
examples/manifest.board.json example: kanban-read completeness
examples/manifest.dialogues.json example: a function must appear exactly once
```

## Run it

```bash
python3 grader/grader.py --root examples --manifest examples/manifest.board.json
```

(Manifest paths resolve against `--root`; the bundled examples use `--root examples`.)

Output is a verdict JSON:

```json
{ "task_id": "...", "score": 100, "wc": true, "p0": [], "p1": [], "p2": [], "checked_at": "..." }
```

- `wc: true` and exit code 0  -> the Worthy Condition holds, the task may be claimed done.
- `wc: false` and exit code 2 -> a P0 remains, completion must NOT be claimed.
- exit code 1 -> the grader itself could not run (e.g. unreadable manifest).

Requires Python 3.8+ (standard library only, no dependencies).

`score` (0 to 100) is only a trend indicator for anti-stagnation. It is never the completion criterion; `wc` is.

## How it plugs into a loop

1. Agent does a round of work.
2. Before claiming "done", the loop's last step runs the Grader on the task manifest.
3. If `wc` is false, the agent must fix the P0 items and loop again, not stop.
4. If `wc` is true, stop.

On Claude Code, step 2 can be enforced by a Stop hook (block completion while exit code is 2). On other agents, the loop script calls the Grader as its final step. This is the two-layer design: portable script everywhere, enforcement hook on the main agent.

## Writing a check

A manifest is a list of checks. Built-in check types: `file_exists`, `literal_count` (substring appears exactly N times), `min_lines` (not truncated below N), `forbid` (a regex must not appear). Add new checks as small functions in `grader/grader.py`; prefer growing one shared library over one grader per task.

## Boundary

Use this only for tasks with an objective, machine-checkable spec (deployment, file governance, tests, board completeness, link integrity). Do not use it for creative or open-ended writing; those keep human or LLM-judge evaluation.

## License / status

Draft for reference. Not yet published or versioned as a release.
