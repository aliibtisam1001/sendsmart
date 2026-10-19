.PHONY: install test run scenarios eval lint

install:
	python -m pip install -e ".[ui,llm,dev]"

test:
	python -m pytest

run:
	python -m streamlit run src/sendsmart/ui/app.py

scenarios:
	python scenarios/run_scenarios.py

eval:
	python evaluation/eval_intent.py

lint:
	python -m compileall -q src scenarios evaluation tests

