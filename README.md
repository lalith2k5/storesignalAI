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
