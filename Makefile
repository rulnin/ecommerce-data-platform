.PHONY: profile verify

profile:
	python3 scripts/profile_dataset.py --input data/raw --output docs/source-profile.json

verify:
	python3 -m compileall -q scripts
	python3 -m unittest discover -s tests/unit -v
