"""Seed a realistic eval regression into Arize Phoenix for Eval Sentinel to catch.

Creates a support-ticket classification dataset, then runs two experiments:
  1. BASELINE  — a well-specified prompt  (high accuracy)
  2. REGRESSED — a "simplified" prompt that drops the billing<->account
     disambiguation rule (accuracy tanks on those categories)

The gap between these two experiments is the regression Eval Sentinel detects,
root-causes, and fixes.

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

CATEGORIES = ["billing", "account", "technical", "other"]

# --- Dataset: support tickets with ground-truth labels -----------------------
TICKETS = [
    ("I was charged twice for my subscription this month, please refund one.", "billing"),
    ("My invoice shows the wrong amount, I upgraded mid-cycle.", "billing"),
    ("Can I get a receipt for last year's payments for taxes?", "billing"),
    ("Why did my price go up? I was on the $20 plan.", "billing"),
    ("My card was declined but I was still charged a pending amount.", "billing"),
    ("I want a refund for the annual plan I bought yesterday.", "billing"),
    ("I can't log in, it says my password is incorrect.", "account"),
    ("Please reset my password, the email link expired.", "account"),
    ("I want to cancel my account and delete my data.", "account"),
    ("How do I change the email address on my profile?", "account"),
    ("I'm locked out after too many login attempts.", "account"),
    ("Can you merge my two accounts into one?", "account"),
    ("The app crashes every time I open the reports tab.", "technical"),
    ("Export to CSV produces an empty file.", "technical"),
    ("The dashboard charts won't load, just a spinner forever.", "technical"),
    ("API returns 500 errors on the /search endpoint.", "technical"),
    ("Dark mode toggle does nothing on mobile.", "technical"),
    ("Page is extremely slow, takes 30 seconds to load.", "technical"),
    ("Do you have an office in Berlin?", "other"),
    ("Just wanted to say your product is great, thanks!", "other"),
    ("Are you hiring engineers right now?", "other"),
    ("Can I get a sticker pack?", "other"),
    ("What's your company's mission statement?", "other"),
    ("Is there a podcast where you discuss your roadmap?", "other"),
]

BASELINE_PROMPT = (
    "You are a support ticket classifier. Classify the ticket into exactly one "
    "category:\n"
    "- billing: charges, refunds, invoices, payments, pricing, receipts\n"
    "- account: login, password resets, profile changes, cancellations, account access\n"
    "- technical: bugs, errors, crashes, broken features, performance\n"
    "- other: anything that doesn't fit the above\n"
    "Respond with ONLY the single lowercase category word."
)

# The regression: a bad edit folded billing UNDER account ("treat billing as
# part of account"), so billing tickets get systematically mislabeled as account.
# This is a real, explainable misconfiguration for Eval Sentinel to root-cause.
REGRESSED_PROMPT = (
    "You are a support ticket classifier. Classify the ticket into exactly one "
    "category:\n"
    "- account: login, password resets, profile changes, cancellations, account "
    "access, AND all billing, payments, refunds, invoices, and pricing questions "
    "(treat billing matters as part of account)\n"
    "- billing: only enterprise contract negotiations\n"
    "- technical: bugs, errors, crashes, broken features, performance\n"
    "- other: anything that doesn't fit the above\n"
    "Respond with ONLY the single lowercase category word."
)


def classify(prompt: str, ticket: str) -> str:
    r = GENAI.models.generate_content(model=MODEL, contents=f"{prompt}\n\nTicket: {ticket}")
    word = (r.text or "").strip().lower().split()[0] if r.text else ""
    return word if word in CATEGORIES else "other"


def make_task(prompt: str):
    def task(example) -> str:
        ticket = example["input"]["ticket"] if isinstance(example["input"], dict) else str(example["input"])
        return classify(prompt, ticket)
    return task


def exact_match(output, expected) -> float:
    exp = expected.get("label") if isinstance(expected, dict) else str(expected)
    return 1.0 if str(output).strip().lower() == str(exp).strip().lower() else 0.0


def main():
    print("Creating dataset 'support-tickets' ...")
    ds = PHX.datasets.create_dataset(
        name="support-tickets",
        inputs=[{"ticket": t} for t, _ in TICKETS],
        outputs=[{"label": lbl} for _, lbl in TICKETS],
        dataset_description="Support ticket intent classification for Eval Sentinel demo.",
    )
    print(f"  dataset id: {ds.id}  ({len(TICKETS)} examples)")

    print("\nRunning BASELINE experiment ...")
    PHX.experiments.run_experiment(
        dataset=ds,
        task=make_task(BASELINE_PROMPT),
        evaluators={"exact_match": exact_match},
        experiment_name="classifier-baseline",
        experiment_metadata={"prompt": BASELINE_PROMPT, "prompt_version": "v1-baseline"},
    )

    print("\nRunning REGRESSED experiment (planted regression) ...")
    PHX.experiments.run_experiment(
        dataset=ds,
        task=make_task(REGRESSED_PROMPT),
        evaluators={"exact_match": exact_match},
        experiment_name="classifier-current",
        experiment_metadata={"prompt": REGRESSED_PROMPT, "prompt_version": "v2-current"},
    )

    print("\nDone. Two experiments on 'support-tickets' — baseline vs current.")


if __name__ == "__main__":
    main()
