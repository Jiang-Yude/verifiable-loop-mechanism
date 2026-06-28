# Documents as a System: A Machine-Verifiable Loop Mechanism for a One-Person, Non-Engineer AI Operation

Author: Jiang Yude (江昱德)
Status: working note, v0.1, 2026-06-28. Single operator, single knowledge base (n=1). Not peer-reviewed. Treat as a design reference, not a settled result.

## Abstract

This note describes a loop mechanism for running AI agents (Claude Code, Codex, and others) semi-autonomously across one person's knowledge base, on both a laptop and a desktop. The mechanism's job is to answer two questions that an AI should not answer by feeling: in each round, "is this actually done?" and "should it stop now?". We replace the subjective stop ("the AI thinks it is good enough") with a machine-checked completion condition for tasks that have an objective spec, while deliberately keeping human or LLM-judge evaluation for creative and writing tasks that have no objective grader. The completion primitive is adopted from Yuta Tu's G-T-W (Grader, Trace, Worthy Condition). The contribution here is the wrapping: how a non-engineer turns that primitive into a portable, teachable operating rhythm, with a two-layer design (portable scripts for every agent, plus an enforcement hook on the main agent), validated on a minimal real implementation.

## 1. Problem

A text rule like "stop when it is good enough" fails in three ways that we observed directly:

1. False Completion. The agent announces "done" while a machine-checkable condition is still false. Formally, False Completion = Claimed Completion AND NOT WC(G(state)).
2. Loopmaxxing. With no objective stop, the agent keeps iterating past the point of useful return, or polishes cosmetic issues (raising a score) while the blocking issue remains.
3. Rule loss on context compaction. Rules written only as prose get dropped when the context window is compacted. The agent then proceeds as if the rule never existed. We reproduced this in the design process itself: a rule that said "for complex tasks, pull a second model automatically" was in context, and the operator still had to remind the agent to do it. That failure is the clearest argument for making verification a forced step, not a remembered instruction.

## 2. Background

### 2.1 Loop engineering (four nested loops)

Modern agent design separates context engineering (what goes into the token window) from loop engineering (what happens after the model speaks). A common structure is four nested loops: an agent loop (plan, act with tools, produce output), wrapped in a verification loop (a grader checks the output against a rubric and returns it with feedback until it passes), wrapped in an event loop (triggers and schedules), wrapped in a hill-climbing loop (analyze traces and rewrite the harness itself).

### 2.2 G-T-W (adopted primitive)

From Yuta Tu, "Machine-Verifiable Completion for AI Agent Systems, G-T-W" (2026, preprint, n=1, not peer-reviewed; source link omitted pending the author's permission):

- Grader: a script that scores the current state 0 to 100 and emits a problem list. Severity weights P0 = blocking (-10), P1 = important (-5), P2 = minor (-2). The verdict is decided by the script, not by the AI.
- Trace: each round re-runs the Grader and records the score trajectory and which checks ran, so progress can be checked for regression.
- Worthy Condition: a boolean completion condition. WC = (P0 count == 0). Only when WC holds is the task complete.

We adopt G-T-W as the verification-loop primitive and treat the rest of our mechanism as the surrounding operating system.

## 3. The mechanism

### 3.1 Default rhythm (Loop mode)

Non-mechanical tasks run a default rhythm without per-step prompting. The rhythm only defines when to start, how hard to review, when to stop, and how to report; the execution rules themselves are reused from existing house rules.

- Task tiers L0 to L3. L0 mechanical (do directly, no second brain, no retro). L1 small (quick self-check). L2 complex (may pull one second brain, short retro). L3 high-risk (change rules, deploy, secrets, business decisions, public release): plan first, back up, cross-family review, explicit acceptance, only then write back.
- Autonomy levels switched by one phrase. Default = Loop mode (auto by tier). "A bit more autonomous" = stronger, fewer check-backs. "Full auto" = finish as much as possible; discuss problems with another model and execute the resolvable ones; skip-and-log only the items needing major authorization or facing a real contradiction; report all skipped items once at the end.
- Cross-family three states (honesty). Call another model if possible; otherwise produce a bounded handoff; otherwise label as single-model self-check. Never report an unperformed cross-review as done.
- Stop conditions (anti-loopmaxxing). Reflection returns diminish after 2 to 3 rounds, then stop; a per-task cost ceiling downgrades or reports instead of grinding.
- Retro gate and write-back gate prevent journal spam and rule bloat. Writing back to a skill requires dual-model plus a concision review.
- A fixed closing report: tier, cross-family or not, acceptance result, residual risk, whether to write back a rule.

### 3.2 G-T-W integration and two-layer architecture

For machine-checkable tasks, the subjective stop is replaced by WC.

- Universal layer (every agent, both devices): a portable Grader script (plain Python or Bash) plus a short written SOP in the single source-of-truth rules file. Any agent (Claude Code, Codex, others) can call the same script and read the same SOP; cross-device sync is by file sync.
- Enforcement layer (main agent): because important decisions run mainly on Claude Code, a Claude Code hook can force the Grader to run and block a completion claim while P0 != 0. Other agents fall back to the universal layer, where the loop script's last step always calls the Grader.

This split is deliberate: the universal layer guarantees "runs everywhere," and the hook guarantees "runs strictest where it matters most."

### 3.3 "Run it yourself" behavioral contract

Once the operator says "run it yourself" or "full auto," the agent must: start immediately (do not open with questions), not stop for small decisions (decide reasonably, log the assumption, continue), not stop after a sub-stage (chain to the end), ask clarifying questions only before starting, and stop only for the narrow red line or a true blocker (which is skipped, logged, and the run continues). Completion is judged by the objective condition (WC), not by finishing one stage. After starting, zero questions go back to the operator; problems are resolved by cross-model discussion plus a concision review, and anything needing the operator is accumulated into the single final report.

Narrow red line, never auto-executed even in full auto: irreversible or outward-sending or money actions (public publish/send, payment/order/transfer, destructive delete or overwrite, sending secrets externally, external commitments). Screen and web operation is allowed in full auto (saying "full auto" is the per-session authorization), but if it gets stuck on the same problem 5 times or for 3 minutes with no progress, skip and log.

### 3.4 Boundary

G-T-W applies only to loops with an objective, machine-checkable spec (deployment, file governance, data consistency, tests, board-read completeness). Creative and open-ended work (writing, tone, strategy) has no objective grader and keeps human or LLM-judge evaluation. This boundary is a protection: it stops the verification machinery from contaminating content production.

## 4. Minimal-viable implementation and validation

Following a concision review, the first implementation is intentionally minimal: one shared Grader script (not one per task), a short SOP, and the score recorded in the existing closing-report field rather than a separate trace database. A full trace store and the enforcement hook are deferred until proven necessary.

The shared Grader (`grader/grader.py`) reads a manifest of checks, runs them, and emits a verdict JSON with score, P0/P1/P2 lists, and `wc`. Exit code is 0 when WC holds and 2 when it fails, so a shell or hook can gate on it.

Validation (run 2026-06-28):

| Test | Target | Expected | Result |
|---|---|---|---|
| Real board completeness | a live kanban file | WC true, exit 0 | PASS (score 100, exit 0) |
| initFixedStars duplicated | fixture with duplicates | WC false, exit 2 | PASS (P0 fired, evidence count=3, exit 2) |
| initFixedStars fixed | fixture with 1 occurrence | WC true, exit 0 | PASS (exit 0) |

The duplicate case is a real recurring bug in a separate project (a star-init function defined twice). The Grader catches it by literal count, with machine evidence, and the non-zero exit blocks a completion claim. This is the whole point: a machine, not the agent, decides done.

## 5. Comparison with Yuta Tu's G-T-W

The two are not competitors; they sit at different layers and were built for different situations, shown in the table below.

| Dimension | Yuta Tu G-T-W | This mechanism |
|---|---|---|
| Object | A completion primitive (Grader, Trace, WC) | A full one-person operating rhythm that adopts G-T-W as its verification step |
| Situation it fits | Establishing the primitive on a focused project (n=1) | One non-engineer running mixed content + ops work across two agents and two devices |
| Completion criterion | WC = (P0 = 0) | Same, for machine-checkable tasks only |
| Anti-loopmaxxing | Trace-based detection of stagnation and score-gaming | Reuses an existing "diminishing returns after 2 to 3 rounds + cost ceiling" rule; deliberately does not add a separate detector (avoids duplication for a one-person scale) |
| Trace | Full immutable trace for regression audit | Minimal: one line in the existing closing report; full trace deferred until a long loop needs it |
| Enforcement | Forced machine step (the central lesson) | Two layers: portable script everywhere + an optional hook on the main agent, hook deferred until self-discipline is shown to fail |
| Creative work | Not the focus | Explicit boundary: excluded, kept on human or LLM-judge |
| Portability goal | Not stated | First-class: plain scripts plus prose SOP, so it is teachable and runs on mainstream agents without bespoke infrastructure |

Reading of the difference: the paper isolates and argues for the primitive; this mechanism is an operator-level system that needed the primitive and wrapped it for a non-engineer, content-heavy, multi-device life. Where the paper optimizes for rigor of the completion claim, this mechanism also optimizes for "do not become a burden," which is why several full-G-T-W components are deferred rather than built on day one.

## 6. Limitations

- n=1, single operator, single knowledge base. No external replication.
- The author is a non-engineer; the implementation favors readability and portability over performance or generality.
- The behavioral contract (section 3.3) is still prose, and prose is exactly what the paper warns can be dropped on context compaction. Only the Grader and its exit code are machine-enforced today; the enforcement hook is designed but deferred.
- Not peer-reviewed. The G-T-W source is itself a preprint with n=1.
- Graders only cover what someone wrote a check for. An absent check is a silent gap, not a pass.

## 7. Reproduce

See `README.md`. In short: `python3 grader/grader.py --root examples --manifest examples/manifest.board.json`. Exit 0 = WC holds, exit 2 = P0 remains.

## 8. Provenance

- From Yuta Tu's preprint (adopted): the False Completion framing, the Grader/Trace/Worthy-Condition triad, the P0/P1/P2 severity model, and the lesson that rules must be machine-enforced rather than remembered.
- Added by this work: the L0 to L3 tiers, the one-phrase autonomy levels, the cross-family three states, the "run it yourself" behavioral contract and narrow red line, the universal-plus-hook two-layer split, the explicit creative-work boundary, the portability and teachability goals, and the minimal-viable scoping (one shared Grader, deferred trace and hook).
