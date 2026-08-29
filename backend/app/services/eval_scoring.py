from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from app.models import ActionItem, Deadline, EvalRun, Obligation, Risk

MATCH_THRESHOLD = 75


def score_category(predicted: list[str], ground_truth: list[str]) -> tuple[float, float, float]:
    if not predicted and not ground_truth:
        return 1.0, 1.0, 1.0
    if not predicted or not ground_truth:
        return 0.0, 0.0, 0.0

    matched_predicted = set()
    matched_truth = set()
    for i, p in enumerate(predicted):
        for j, g in enumerate(ground_truth):
            if j in matched_truth:
                continue
            if fuzz.token_sort_ratio(p, g) >= MATCH_THRESHOLD:
                matched_predicted.add(i)
                matched_truth.add(j)
                break

    precision = len(matched_predicted) / len(predicted)
    recall = len(matched_truth) / len(ground_truth)
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return precision, recall, f1


def run_eval(db: Session, document_id: int, ground_truth: dict[str, list[str]], ground_truth_ref: str) -> EvalRun:
    """Score a document's extracted rows against hand-annotated ground truth,
    persist an EvalRun row, and return it. Shared by scripts/eval.py and the
    POST /api/documents/{id}/eval endpoint so both stay in sync."""
    predicted = {
        "obligations": [o.text for o in db.query(Obligation).filter(Obligation.document_id == document_id)],
        "risks": [r.text for r in db.query(Risk).filter(Risk.document_id == document_id)],
        "deadlines": [d.description for d in db.query(Deadline).filter(Deadline.document_id == document_id)],
        "action_items": [a.text for a in db.query(ActionItem).filter(ActionItem.document_id == document_id)],
    }

    overall_p, overall_r, overall_f1 = [], [], []
    for category, gt_items in ground_truth.items():
        p, r, f1 = score_category(predicted.get(category, []), gt_items)
        overall_p.append(p)
        overall_r.append(r)
        overall_f1.append(f1)

    avg_p = sum(overall_p) / len(overall_p)
    avg_r = sum(overall_r) / len(overall_r)
    avg_f1 = sum(overall_f1) / len(overall_f1)

    run = EvalRun(document_id=document_id, precision=avg_p, recall=avg_r, f1=avg_f1, ground_truth_ref=ground_truth_ref)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run
