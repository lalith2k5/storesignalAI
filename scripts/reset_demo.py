"""Reset pipeline outputs (keeps raw data + models + reference)."""
from pathlib import Path
import shutil
from storesignal.config import ROOT

PROC = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"

if __name__ == "__main__":
    for d in (PROC, REPORTS):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)
    print("Reset complete. Run the pipeline to regenerate outputs.")
