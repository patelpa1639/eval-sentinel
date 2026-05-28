PY := .venv/bin/python
PYTEST := .venv/bin/pytest

.PHONY: test test-all seed demo deploy-dry

# Fast suite: smoke + integration, excluding slow/live tests (pytest.ini addopts).
test:
	$(PYTEST) -q

# Full suite including slow/live tests.
test-all:
	$(PYTEST) -q -m "slow or not slow"

# Seed the Phoenix dataset + baseline/current experiments.
seed:
	$(PY) -m src.seed

# Run the Eval Sentinel agent demo.
demo:
	$(PY) -m src.run

# Validate the Agent Engine deployment without actually deploying.
deploy-dry:
	$(PY) deployment/deploy.py --dry-run
