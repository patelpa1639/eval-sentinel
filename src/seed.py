"""Seed a realistic eval regression into Arize Phoenix for Eval Sentinel to catch.

Domain: a SMART-HOME command router — the kind of classifier a homelabber runs
on a local LLM to route voice/text commands to the right subsystem.

Creates a `smart-home-commands` dataset, then runs two experiments:
  1. BASELINE  — a well-specified prompt with per-category keyword hints (high
     accuracy across all five categories).
  2. REGRESSED — the SAME model, but a SUBTLE, plausible "prompt cleanup" a
     homelabber might actually make:
       (a) narrows `media` to "watching TV/movies or playing music for
           entertainment", which quietly drops volume/announcement commands; and
       (b) adds an over-broad rule that ANY question or status check
           ("did X", "is X", "show me X", "what is X") is `other`, which quietly
           pulls camera/door status checks out of `security`.
     Both edits READ as reasonable simplifications, but together they sink the
     `media` and `security` categories while lights/climate/other stay perfect.

The gap between these is the regression Eval Sentinel detects, root-causes,
fixes (revert to the well-scoped baseline prompt), and verifies.

Why a subtle PROMPT regression rather than a MODEL swap:
  The project's pitch is "homelabbers swap local LLMs and quality silently
  drops". We empirically tested a model swap (strong vs weaker Gemini variants)
  on this command set: every model available in the project's `global` Vertex
  location — down to `gemini-2.5-flash-lite` — scored ~100% on a 5-way
  smart-home routing task, so a model swap produced NO reliable dip. Per the
  reliability-first design, we fall back to a subtle, genuinely-plausible prompt
  wording change that DOES reproduce reliably (~84-88% overall, spread across the
  media + security categories). The classifier model is held FIXED across
  baseline/regressed so the regression is unambiguously the prompt.

Two evaluators are attached to every experiment:
  - exact_match: the gold metric (predicted label == ground-truth label).
  - llm_judge:   a cheap Gemini "is this routing reasonable?" second opinion, so
                 the agent can reason over more than exact-match alone.

Run:  ./.venv/bin/python -m src.seed
"""

import os

from dotenv import load_dotenv

load_dotenv()

from google import genai
from phoenix.client import Client

PHX = Client(base_url=os.environ["PHOENIX_COLLECTOR_ENDPOINT"])
GENAI = genai.Client(vertexai=True, project=os.environ["GOOGLE_CLOUD_PROJECT"], location="global")

# The strong classifier model, held fixed across baseline + regressed so the only
# variable is the prompt. The fix/verify path re-runs with this same model.
BASELINE_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
# A cheaper model for the LLM-as-judge second opinion (kept small on purpose).
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "gemini-2.5-flash-lite")

CATEGORIES = ["lights", "climate", "media", "security", "other"]

# --- Dataset: smart-home commands with ground-truth subsystem labels ----------
COMMANDS = [
    ("turn on the living room lights", "lights"),
    ("dim the bedroom lamp to 30%", "lights"),
    ("switch off all the lights downstairs", "lights"),
    ("set the kitchen lights to warm white", "lights"),
    ("turn the porch light on at sunset", "lights"),
    ("set the thermostat to 68 degrees", "climate"),
    ("make it warmer in here", "climate"),
    ("turn on the AC in the bedroom", "climate"),
    ("lower the temperature by 3 degrees", "climate"),
    ("switch the house to eco heating tonight", "climate"),
    ("play jazz in the kitchen", "media"),
    ("pause the living room TV", "media"),
    ("turn up the volume in the office", "media"),
    ("skip to the next song", "media"),
    ("play the news on the bedroom speaker", "media"),
    ("lock the front door", "security"),
    ("arm the alarm when we leave", "security"),
    ("show me the backyard camera", "security"),
    ("did the garage door close?", "security"),
    ("unlock the side gate for the delivery", "security"),
    ("what's the weather tomorrow?", "other"),
    ("set a timer for 10 minutes", "other"),
    ("add milk to the shopping list", "other"),
    ("what time is it in Tokyo?", "other"),
    ("tell me a joke", "other"),
]

BASELINE_PROMPT = (
    "You are a smart-home command router. Classify the command into exactly one "
    "category:\n"
    "- lights: turning lights on/off, dimming, brightness, bulb color\n"
    "- climate: thermostat, temperature, heating, cooling, AC, fans\n"
    "- media: music, TV, speakers, volume, playback\n"
    "- security: locks, alarms, cameras, doors, gates\n"
    "- other: anything not controlling a smart-home device (weather, timers, "
    "lists, general questions)\n"
    "Respond with ONLY the single lowercase category word."
)

# The regression: a SUBTLE, plausible "prompt cleanup". (a) `media` is narrowed
# to entertainment-only, so volume/announcement commands quietly fall to `other`;
# (b) an over-broad "any question/status check is other" rule quietly pulls
# camera/door status checks out of `security`. No single clause is obviously
# wrong — it reads like a reasonable simplification — which is exactly why it is
# a believable silent regression for Eval Sentinel to root-cause.
REGRESSED_PROMPT = (
    "You are a smart-home command router. Classify the command into exactly one "
    "category:\n"
    "- lights: turning lights on/off, dimming, brightness, bulb color\n"
    "- climate: thermostat, temperature, heating, cooling, AC, fans\n"
    "- media: watching TV/movies or playing music for entertainment\n"
    "- security: locks, alarms, cameras, doors, gates\n"
    "- other: anything else, including any question or status check (e.g. 'did "
    "X', 'is X', 'show me X', 'what is X'), weather, timers, lists, volume, and "
    "announcements\n"
    "Respond with ONLY the single lowercase category word."
)


def classify(prompt: str, command: str, model: str = BASELINE_MODEL) -> str:
    r = GENAI.models.generate_content(model=model, contents=f"{prompt}\n\nCommand: {command}")
    word = (r.text or "").strip().lower().split()[0] if r.text else ""
    return word if word in CATEGORIES else "other"


def make_task(prompt: str, model: str = BASELINE_MODEL):
    def task(example) -> str:
        inp = example["input"]
        command = inp["command"] if isinstance(inp, dict) else str(inp)
        return classify(prompt, command, model=model)
    return task


def exact_match(output, expected) -> float:
    """Gold metric: predicted label == ground-truth label."""
    exp = expected.get("label") if isinstance(expected, dict) else str(expected)
    return 1.0 if str(output).strip().lower() == str(exp).strip().lower() else 0.0


def llm_judge(input, output, expected) -> float:
    """Cheap LLM-as-judge second opinion: does the routing look reasonable?

    A small Gemini model scores whether `output` is a defensible category for the
    command, independent of the exact gold label. This surfaces "wrong-but-close"
    vs "wrong-and-nonsensical" routings so the agent can reason about more than
    exact match. Kept to ONE short call per row and fails OPEN (returns 1.0) so a
    judge hiccup never masks a real exact-match miss.
    """
    command = input.get("command") if isinstance(input, dict) else str(input)
    gold = expected.get("label") if isinstance(expected, dict) else str(expected)
    predicted = str(output).strip().lower()
    judge_prompt = (
        "You are grading a smart-home command router. Categories: lights, "
        "climate, media, security, other.\n"
        f'Command: "{command}"\n'
        f"Gold category: {gold}\n"
        f"Router predicted: {predicted}\n"
        "Is the predicted category a REASONABLE routing for this command? "
        "Answer with ONLY 'yes' or 'no'."
    )
    try:
        r = GENAI.models.generate_content(model=JUDGE_MODEL, contents=judge_prompt)
        verdict = (r.text or "").strip().lower()
        return 1.0 if verdict.startswith("y") else 0.0
    except Exception:
        return 1.0  # fail open — never let a judge error mask an exact-match miss


def main():
    print("Creating dataset 'smart-home-commands' ...")
    try:
        ds = PHX.datasets.create_dataset(
            name="smart-home-commands",
            inputs=[{"command": c} for c, _ in COMMANDS],
            outputs=[{"label": lbl} for _, lbl in COMMANDS],
            dataset_description="Smart-home command routing for a local-LLM voice assistant (Eval Sentinel demo).",
        )
    except Exception as exc:
        # Dataset already exists (re-seed): reuse it so experiments line up.
        print(f"  (dataset exists, reusing: {str(exc)[:80]})")
        ds = PHX.datasets.get_dataset(dataset="smart-home-commands")
    print(f"  dataset id: {ds.id}  ({len(COMMANDS)} examples)")

    print(f"\nRunning BASELINE experiment (model={BASELINE_MODEL}) ...")
    PHX.experiments.run_experiment(
        dataset=ds,
        task=make_task(BASELINE_PROMPT),
        evaluators={"exact_match": exact_match, "llm_judge": llm_judge},
        experiment_name="router-baseline",
        experiment_metadata={
            "prompt": BASELINE_PROMPT,
            "prompt_version": "v1-baseline",
            "model": BASELINE_MODEL,
        },
    )

    print(f"\nRunning REGRESSED experiment (planted prompt regression, model={BASELINE_MODEL}) ...")
    PHX.experiments.run_experiment(
        dataset=ds,
        task=make_task(REGRESSED_PROMPT),
        evaluators={"exact_match": exact_match, "llm_judge": llm_judge},
        experiment_name="router-current",
        experiment_metadata={
            "prompt": REGRESSED_PROMPT,
            "prompt_version": "v2-current",
            "model": BASELINE_MODEL,
        },
    )

    print("\nDone. Two experiments on 'smart-home-commands' — baseline vs current.")


if __name__ == "__main__":
    main()
