.PHONY: profile verify verify-integration
PYTHON ?= .venv/bin/python

profile:
	$(PYTHON) scripts/profile_dataset.py --input data/raw --output docs/source-profile.json

verify:
	PYTHON="$(PYTHON)" bash scripts/check.sh unit

verify-integration:
	PYTHON="$(PYTHON)" bash scripts/check.sh integration
