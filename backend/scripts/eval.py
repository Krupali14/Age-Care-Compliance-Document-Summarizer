import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.services.eval_scoring import run_eval as run_eval_scoring


def run_eval(document_id: int, ground_truth_path: str) -> None:
    ground_truth = json.loads(Path(ground_truth_path).read_text())
    db = SessionLocal()
    try:
        run = run_eval_scoring(db, document_id, ground_truth, ground_truth_path)
        print(f"OVERALL: precision={run.precision:.2f} recall={run.recall:.2f} f1={run.f1:.2f}")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/eval.py <document_id> <ground_truth_path>")
        sys.exit(1)
    run_eval(int(sys.argv[1]), sys.argv[2])
