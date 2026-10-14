.PHONY: setup synth unified train detect eval ui reset all test clean

setup:
	uv venv --python 3.11 .venv
	uv pip install -e ".[dev]"

synth:
	python scripts/make_synthetic_data.py

unified:
	python scripts/build_unified.py

train:
	python scripts/train_baseline.py

detect:
	python scripts/run_detection.py

eval:
	python scripts/run_evaluation.py

ui:
	streamlit run src/storesignal/ui/app.py

reset:
	python scripts/reset_demo.py

all: unified train detect eval

test:
	pytest tests/ -v

clean:
	rm -rf data/processed/* reports/* models/*.joblib
