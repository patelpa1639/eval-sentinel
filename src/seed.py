"""Seed a realistic eval regression into Arize Phoenix for Eval Sentinel to catch.

Domain: a SMART-HOME command router — the kind of classifier a homelabber runs
on a local LLM (e.g. Gemma) to route voice/text commands to the right subsystem.

Creates a `smart-home-commands` dataset, then runs two experiments:
  1. BASELINE  — a well-specified prompt  (high accuracy)
  2. REGRESSED — a bad prompt edit that folds CLIMATE control under LIGHTS
     (so thermostat/AC commands get mislabeled 'lights' -> climate collapses)

The gap between these is the regression Eval Sentinel detects, root-causes,
fixes, and verifies.

Run:  ./.venv/bin/python -m src.seed
"""

import os

from dotenv import load_dotenv

load_dotenv()

from google import genai
from phoenix.client import Client

PHX = Client(base_url=os.environ["PHOENIX_COLLECTOR_ENDPOINT"])
GENAI = genai.Client(vertexai=True, project=os.environ["GOOGLE_CLOUD_PROJECT"], location="global")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")

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

# The regression: a bad edit folded CLIMATE control UNDER lights ("treat climate
# as part of lights"), so thermostat/AC commands get mislabeled 'lights'.
# A real, explainable misconfiguration for Eval Sentinel to root-cause.
REGRESSED_PROMPT = (
    "You are a smart-home command router. Classify the command into exactly one "
    "category:\n"
    "- lights: turning lights on/off, dimming, brightness, bulb color, AND all "
    "thermostat, temperature, heating, cooling, and AC commands (treat climate "
    "control as part of lights)\n"
    "- climate: only whole-home HVAC system installation requests\n"
    "- media: music, TV, speakers, volume, playback\n"
    "- security: locks, alarms, cameras, doors, gates\n"
    "- other: anything not controlling a smart-home device\n"
    "Respond with ONLY the single lowercase category word."
)


def classify(prompt: str, command: str) -> str:
    r = GENAI.models.generate_content(model=MODEL, contents=f"{prompt}\n\nCommand: {command}")
    word = (r.text or "").strip().lower().split()[0] if r.text else ""
    return word if word in CATEGORIES else "other"


def make_task(prompt: str):
    def task(example) -> str:
        inp = example["input"]
        command = inp["command"] if isinstance(inp, dict) else str(inp)
        return classify(prompt, command)
    return task


def exact_match(output, expected) -> float:
    exp = expected.get("label") if isinstance(expected, dict) else str(expected)
    return 1.0 if str(output).strip().lower() == str(exp).strip().lower() else 0.0


def main():
    print("Creating dataset 'smart-home-commands' ...")
    ds = PHX.datasets.create_dataset(
        name="smart-home-commands",
        inputs=[{"command": c} for c, _ in COMMANDS],
        outputs=[{"label": lbl} for _, lbl in COMMANDS],
        dataset_description="Smart-home command routing for a local-LLM voice assistant (Eval Sentinel demo).",
    )
    print(f"  dataset id: {ds.id}  ({len(COMMANDS)} examples)")

    print("\nRunning BASELINE experiment ...")
    PHX.experiments.run_experiment(
        dataset=ds,
        task=make_task(BASELINE_PROMPT),
        evaluators={"exact_match": exact_match},
        experiment_name="router-baseline",
        experiment_metadata={"prompt": BASELINE_PROMPT, "prompt_version": "v1-baseline"},
    )

    print("\nRunning REGRESSED experiment (planted regression) ...")
    PHX.experiments.run_experiment(
        dataset=ds,
        task=make_task(REGRESSED_PROMPT),
        evaluators={"exact_match": exact_match},
        experiment_name="router-current",
        experiment_metadata={"prompt": REGRESSED_PROMPT, "prompt_version": "v2-current"},
    )

    print("\nDone. Two experiments on 'smart-home-commands' — baseline vs current.")


if __name__ == "__main__":
    main()
