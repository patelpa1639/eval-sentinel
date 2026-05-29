# Eval Sentinel — Demo Video Storyboard (≤ 3:00)

A scene-by-scene script for the submission video. Target runtime **2:50**.
Each scene lists what's on screen and a timed voiceover (VO). Keep cuts tight;
the agent's live reasoning is the star — let it breathe but don't linger.

---

## Scene 1 — The problem (0:00–0:24, ~24s)

**On screen:** Title card "Eval Sentinel" over a dim terminal. Cut to a simple
diagram: a home-assistant box ("local LLM — Gemma via Ollama") routing a spoken
command to subsystems (lights, climate, media, security), with a "swap model /
edit prompt" arrow and a tiny red crack appearing on the climate branch.

**VO:**
> Homelabbers are running local LLMs as the brain of their smart home — routing
> "dim the lights" or "set the thermostat" to the right subsystem. But swap the
> model or tweak the prompt and a whole category of commands can quietly start
> misfiring. No exception, no stack trace, just worse routing — and no tooling to
> catch it. Eval Sentinel is an autonomous agent that catches that drift, finds
> the cause, fixes it, and proves the fix — on its own.

---

## Scene 2 — The regression in Phoenix (0:24–0:52, ~28s)

**On screen:** Browser at the Arize Phoenix experiments view
(`https://app.phoenix.arize.com/s/patelpa1639/datasets/RGF0YXNldDoy/experiments`).
Navigate via **Datasets & Experiments → `smart-home-commands`**. Show the dataset
(25 examples) and two experiments side by side: **router-baseline** and
**router-current**. Hover to reveal the scores. Zoom the per-category breakdown.

**VO:**
> Here's a smart-home command router evaluated in Arize Phoenix — five
> categories, twenty-five labeled commands. The baseline experiment scores a
> clean 100%. Then someone ships a prompt "cleanup" that looks harmless. The new
> "current" experiment drops to 84% overall — and look closer: the dip is
> concentrated in two categories, media and security, while the rest hold. That's
> exactly the kind of partial regression that hides inside an average.

---

## Scene 3 — Launch the agent (0:52–1:10, ~18s)

**On screen:** Clean terminal. Type and run:
```bash
python -m src.run
```
Show the `rich`-rendered banner panel — "EVAL SENTINEL · autonomous LLM-eval
healing agent — Gemini 3 · Arize Phoenix MCP" — and the trigger line, then the
agent connecting to the Arize Phoenix MCP server.

**VO:**
> Eval Sentinel is an ADK agent running on Gemini 3, with the Arize Phoenix MCP
> server wired in as its toolset for reading datasets, experiments, traces, and
> evals. The agent is cloud Gemini 3; the model it's watching is the local one.
> It senses and investigates through Phoenix. Let's wake it up and watch.

---

## Scene 4 — Plan + detect (1:10–1:36, ~26s)

**On screen:** Live `rich` output. First the agent states an explicit PLAN
(numbered: detect, root-cause, propose fix, verify, report, await approval).
Then the `detect_regression` tool call, followed by the colored **"Regression
detected"** table (Category | Baseline | Current | flag) — the media and security
rows in red marked "▼ regressed," others green. Box the overall accuracy delta line.

**VO:**
> First it states a plan, then it orients. It pulls both experiments through
> Phoenix, compares them category by category, and isolates the failing
> categories on its own — media and security each dropped to 60% while the rest
> held at 100%. No threshold I hand-coded — it reasoned to that conclusion from
> the eval data.

---

## Scene 5 — Root-cause (1:36–2:02, ~26s)

**On screen:** Output continues. Agent calls `get_failing_examples("media")` and
`get_failing_examples("security")`; show the dim evidence lines ("2 'media'
commands failed, all misclassified as other"; likewise for security). Let the
model narrate the diagnosis as a Markdown panel. Box the conclusion: *the current
prompt narrowed "media" to entertainment-only and made "other" an over-broad
catch-all for any status check.*

**VO:**
> Now the harder part — why. It opens the failing commands and sees they're all
> being labeled "other." It reads the prompt attached to the current experiment
> and finds the smoking gun: the "cleanup" narrowed media to entertainment only —
> so "turn up the volume in the office" falls through — and added an over-broad
> rule sending any status check to "other," so "show me the backyard camera"
> leaves security. Root cause, in plain language, with the evidence it relied on.

---

## Scene 6 — Fix + verify (2:02–2:32, ~30s)

**On screen:** Agent proposes a corrected prompt (restoring the full "media" and
"security" definitions), then calls `verify_fix` — which runs a REAL new
experiment through Phoenix. Show the green **"Fix verified (live re-evaluation)"**
table and the "overall after fix: 100%" line with the new experiment id. Optional
quick cut to the Phoenix UI showing the recovered experiment.

**VO:**
> It writes a corrected prompt that addresses the diagnosed cause — then it
> doesn't just claim victory, it verifies. It runs a real new evaluation through
> Phoenix and watches media and security recover, overall back to 100%. Detect,
> root-cause, fix, verify — closed loop, no human in the middle. The only gate is
> approval before that fixed prompt is promoted to production.

---

## Scene 7 — Close (2:32–2:50, ~18s)

**On screen:** The final `rich` view: the cyan **"Before → After"** table
(Category | Baseline | Regressed | Healed — media and security going red→green) above the
yellow **"Approval gate"** panel. Optional split with the now-green Phoenix
experiment. Fade to a one-line architecture card:
`Gemini 3 ⟶ ADK agent ⟵ Arize Phoenix MCP · Vertex AI Agent Engine`.

**VO:**
> A Gemini-3 agent that keeps your local LLM healthy. It's built on the same
> detect, heal, verify pattern as our infrastructure agent, generalized to AI
> quality. And the Arize Phoenix integration runs deep — Eval Sentinel senses
> and investigates through Phoenix and verifies through it too. That's Eval
> Sentinel.

---

## Shot list (capture these clips)

1. Title card (static, generated).
2. Phoenix experiments page — `smart-home-commands`, both experiments visible.
3. Phoenix per-category breakdown showing media and security dropping to 60%.
4. Terminal: typing + running `python -m src.run`; banner panel + MCP connect.
5. Terminal: PLAN statement + detect phase — `detect_regression` + the red
   "Regression detected" table.
6. Terminal: root-cause phase — `get_failing_examples("media")` / `("security")`
   evidence + the "narrowed media + over-broad other" diagnosis.
7. Terminal: fix phase — proposed corrected prompt.
8. Terminal: verify phase — `verify_fix` + the green recovery table.
9. Terminal: the cyan "Before → After" table + yellow "Approval gate" panel.
10. Phoenix UI: recovered experiment (green) + architecture card.

## Recording tips

- **Seed first, off camera:** run `python -m src.seed` before recording so the
  baseline (100%) and regressed (84%) experiments already exist in Phoenix. The
  video should open on the regression, not on seeding it.
- **Terminal:** large font (16–18pt), high-contrast dark theme, ~110 columns —
  the `rich` panels and tables read best on a dark background. Slow your typing
  or pre-type and paste, then hit enter on camera.
- **Pace the stream:** the agent emits tool calls and reasoning fast. Record at
  native speed, then in editing speed-ramp the quiet stretches 1.5–2× and hold
  full speed on the four key beats (detect, root-cause, fix, verify).
- **Let the pretty output carry it:** the colored tables already highlight what
  matters — the red regressed rows, the green recovery rows, the red→green
  Before → After columns. You barely need extra annotation; a light box on the
  regressed cell and the root-cause diagnosis line is enough.
- **Two browser tabs ready:** Phoenix experiments + per-category view, so the
  open and close cuts are instant.
- **Audio:** record VO separately and lay it over the captured screen; it's far
  cleaner than narrating live. Keep total under 3:00 — aim for 2:50 so you have
  trim margin.
- **Safety:** never show `.env`, API keys, or the Phoenix API key on screen.
  Clear scrollback before recording and keep secrets out of the terminal title.
