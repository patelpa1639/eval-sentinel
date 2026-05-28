# Eval Sentinel — Demo Video Storyboard (≤ 3:00)

A scene-by-scene script for the submission video. Target runtime **2:50**.
Each scene lists what's on screen and a timed voiceover (VO). Keep cuts tight;
the agent's live reasoning is the star — let it breathe but don't linger.

---

## Scene 1 — The problem (0:00–0:22, ~22s)

**On screen:** Title card "Eval Sentinel" over a dim terminal. Cut to a simple
diagram: an LLM app box feeding a "ship prompt change" arrow, with a tiny red
crack appearing in the output.

**VO:**
> LLM applications regress silently. You tweak a prompt, ship it, and a whole
> category of answers quietly breaks — no exception, no stack trace, just worse
> output. By the time a human notices, it's been live for days. Eval Sentinel is
> an autonomous agent that catches that drift, finds the cause, fixes it, and
> proves the fix — on its own.

---

## Scene 2 — The regression in Phoenix (0:22–0:50, ~28s)

**On screen:** Browser at the Arize Phoenix experiments view
(`https://app.phoenix.arize.com/s/patelpa1639/datasets/RGF0YXNldDox/experiments`).
Show the `support-tickets` dataset (24 examples) and two experiments side by
side: **classifier-baseline** and **classifier-current**. Hover to reveal the
scores. Zoom the per-category breakdown.

**VO:**
> Here's a support-ticket classifier evaluated in Arize Phoenix — four
> categories, twenty-four labeled examples. The baseline experiment scores a
> clean one hundred percent. Then a prompt change ships. The new "current"
> experiment drops to seventy-five percent overall — and look closer: billing
> has collapsed from one hundred to zero. Account, technical, and other are
> untouched. That's exactly the kind of partial regression that hides in an
> average.

---

## Scene 3 — Launch the agent (0:50–1:08, ~18s)

**On screen:** Clean terminal. Type and run:
```bash
python -m src.run
```
Show the banner / first lines: the agent connecting to the Arize Phoenix MCP
server and listing that it has the Phoenix toolset available.

**VO:**
> Eval Sentinel is an ADK agent running on Gemini 3, with the Arize Phoenix MCP
> server wired in as its toolset — twenty-seven tools for reading datasets,
> experiments, traces, and evals. Its entire job is reasoning over Phoenix data.
> Let's wake it up and watch.

---

## Scene 4 — Detect (1:08–1:32, ~24s)

**On screen:** Live-streaming terminal. Highlight the tool calls as they appear:
the agent listing experiments, pulling `classifier-baseline` and
`classifier-current`, comparing per-category scores. Let the model's reasoning
text scroll. Visually box the line where it states billing went 100% → 0%.

**VO:**
> First it orients. It pulls both experiments through Phoenix, compares them
> category by category, and isolates the failure on its own: billing dropped
> from one hundred percent to zero, while everything else held. No threshold I
> hand-coded — it reasoned to that conclusion from the eval data.

---

## Scene 5 — Root-cause (1:32–1:58, ~26s)

**On screen:** Terminal continues. Agent inspects the failing billing examples /
spans, reads the experiment metadata (the prompt versions), and narrates the
diagnosis. Box the conclusion line: *"the current prompt folds billing under
account."*

**VO:**
> Now the harder part — why. It opens the failing billing cases and sees they're
> all being labeled "account." It reads the prompt attached to the current
> experiment and finds the smoking gun: the new prompt was rewritten to treat
> billing as part of account. That's the root cause, in plain language, with the
> evidence it relied on.

---

## Scene 6 — Fix + verify (1:58–2:28, ~30s)

**On screen:** Agent proposes a corrected prompt (re-separating billing from
account), then re-runs the evaluation experiment through Phoenix. Show the new
run completing and the agent reporting billing back at ~100% and overall back to
100%. Optional quick cut back to the Phoenix UI showing the recovered
experiment.

**VO:**
> It writes a corrected prompt that pulls billing back out as its own category —
> then it doesn't just claim victory, it verifies. It re-runs the eval
> experiment through Phoenix and watches billing recover to roughly one hundred
> percent, overall back to one hundred. Detect, root-cause, fix, verify — closed
> loop, no human in the middle. The only gate is approval before that fixed
> prompt is promoted to production.

---

## Scene 7 — Close (2:28–2:50, ~22s)

**On screen:** Split view: left, the Phoenix experiment now green; right, the
agent's final before/after report. Fade to a one-line architecture card:
`Gemini 3 ⟶ ADK agent ⟵ Arize Phoenix MCP · Vertex AI Agent Engine`.

**VO:**
> Eval Sentinel is a self-healing brain for AI quality. It's the same autonomous
> detect-fix-verify architecture we proved on infrastructure incidents,
> re-pointed at LLM-eval regressions. The Arize Phoenix integration isn't bolted
> on — reading and reasoning over Phoenix evals is the whole job. That's Eval
> Sentinel.

---

## Shot list (capture these clips)

1. Title card (static, generated).
2. Phoenix experiments page — `support-tickets`, both experiments visible.
3. Phoenix per-category breakdown showing billing 100% → 0%.
4. Terminal: typing + running `python -m src.run`; MCP connect lines.
5. Terminal: detect phase — experiment list + compare tool calls.
6. Terminal: root-cause phase — failing billing spans + prompt metadata.
7. Terminal: fix phase — proposed corrected prompt.
8. Terminal: verify phase — re-run experiment + recovered scores.
9. Phoenix UI: recovered experiment (green).
10. Final report + architecture card.

## Recording tips

- **Seed first, off camera:** run `python -m src.seed` before recording so the
  baseline (100%) and regressed (75%, billing 0%) experiments already exist in
  Phoenix. The video should open on the regression, not on seeding it.
- **Terminal:** large font (16–18pt), high-contrast theme, ~110 columns. Slow
  your typing or pre-type and paste, then hit enter on camera.
- **Pace the stream:** the agent emits tool calls and reasoning fast. Record at
  native speed, then in editing speed-ramp the quiet stretches 1.5–2× and hold
  full speed on the four key beats (detect, root-cause, fix, verify).
- **Highlight, don't narrate every token:** add a colored box/underline on the
  one line that matters in each phase (the 100%→0% line, the "folds billing
  under account" line, the recovered score). Viewers track visuals faster than
  scrolling text.
- **Two browser tabs ready:** Phoenix experiments + per-category view, so the
  open and close cuts are instant.
- **Audio:** record VO separately and lay it over the captured screen; it's far
  cleaner than narrating live. Keep total under 3:00 — aim for 2:50 so you have
  trim margin.
- **Safety:** never show `.env`, API keys, or the Phoenix API key on screen.
  Clear scrollback before recording and keep secrets out of the terminal title.
