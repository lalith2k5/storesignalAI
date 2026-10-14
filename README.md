# StoreSignal AI

Multilingual retail operations early-warning and incident-resolution intelligence system.

## Quick start

    brew install python@3.11 make cmake libomp uv
    make setup
    make synth
    make all       # unified -> train -> detect -> eval
    make ui        # launch Streamlit

## Definition of Done

- Reproducibility: make all && make eval from clean
- Evidence: real macro-F1, escalation precision, lead time
- Interface: UI shows live pipeline outputs
- Determinism: reset+rebuild reproduces identical metrics

## Swapping in real data

Replace data/raw/*.jsonl, data/reference/*.csv, data/eval/*. Do not touch code.
Never train or tune on data/eval/hidden_labels.parquet.


## Real-Data Robustness Check

Supplementary to the synthetic R5 evaluation: the pipeline was run on
20,000 real Google Play India food-delivery reviews (Kaggle:
swoyam2609/google-play-india-reviews) with no code changes.

See `reports/real_data_report.md` for details. Headline:

- 20,000 real multilingual records processed
- 2,940 policy escalations raised
- 36.4 percent routed to human review (expected on out-of-distribution text)
- Language mix preserved: 98.5 percent English, 1.3 percent Hinglish, 0.3 percent Hindi

This is NOT an evaluation - the dataset has no ground-truth labels.
It demonstrates that the pipeline runs unchanged on real, code-mixed
Indian retail text. The synthetic R5 evaluation remains the primary
evidence for the four Definition of Done gates.

To reproduce: python scripts/convert_google_play.py and python scripts/run_real_data.py
