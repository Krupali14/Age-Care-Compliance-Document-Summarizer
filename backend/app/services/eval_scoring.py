from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from app.models import ActionItem, Deadline, EvalRun, Obligation, Risk, Section

MATCH_THRESHOLD = 75

# A finding is "grounded" when its wording is carried by the section it was taken
# from. Summarising rewords things, so this sits well below an exact-match score;
# what it catches is a finding whose words appear nowhere in its source.
GROUNDING_THRESHOLD = 55

# Sections shorter than this are table-of-contents fragments rather than content and
# are never sent for extraction, so counting them would understate coverage.
# Kept in step with processing.EXTRACTABLE_MIN_CHARS.
EXTRACTABLE_MIN_CHARS = 40

AUTO_REF = "auto"


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

    if not ground_truth:
        # Averaging over no categories divides by zero; refuse the run instead.
        raise ValueError("ground_truth must contain at least one category")

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


def _findings(db: Session, document_id: int) -> list[tuple[int | None, str]]:
    """Every extracted finding for a document, as (section_id, text)."""
    rows: list[tuple[int | None, str]] = []
    for obligation in db.query(Obligation).filter(Obligation.document_id == document_id):
        rows.append((obligation.section_id, obligation.text))
    for risk in db.query(Risk).filter(Risk.document_id == document_id):
        rows.append((risk.section_id, risk.text))
    for deadline in db.query(Deadline).filter(Deadline.document_id == document_id):
        rows.append((deadline.section_id, deadline.description))
    for action in db.query(ActionItem).filter(ActionItem.document_id == document_id):
        rows.append((action.section_id, action.text))
    return rows


def run_auto_eval(db: Session, document_id: int) -> EvalRun:
    """Score a document against itself, with no hand-annotated ground truth.

    run_eval() needs someone to have written down the correct answers, which nobody
    has for a document a user just uploaded. These two measures need only the
    document and what was extracted from it, so they can run as soon as processing
    finishes:

      grounding — the share of findings whose wording is supported by the section
                  they cite. This is the check against invented content: a finding
                  whose words appear nowhere in its source does not count.
      coverage  — the share of extractable sections that yielded a finding. Low is
                  not automatically wrong (a section of definitions carries no
                  obligations), but a sharp drop means stretches of a document
                  produced nothing at all.
    """
    sections = {
        s.id: s.raw_text for s in db.query(Section).filter(Section.document_id == document_id)
    }
    extractable = {
        sid for sid, text in sections.items() if len((text or "").strip()) >= EXTRACTABLE_MIN_CHARS
    }
    findings = _findings(db, document_id)

    if findings:
        grounded = sum(
            1
            for section_id, text in findings
            if fuzz.token_set_ratio((text or "").lower(), (sections.get(section_id) or "").lower())
            >= GROUNDING_THRESHOLD
        )
        grounding = grounded / len(findings)
    else:
        # Nothing extracted means nothing invented, but nothing supported either.
        grounding = 0.0

    covered = {section_id for section_id, _ in findings if section_id in extractable}
    coverage = len(covered) / len(extractable) if extractable else 0.0

    overall = 0.0 if grounding + coverage == 0 else 2 * grounding * coverage / (grounding + coverage)

    run = EvalRun(
        document_id=document_id,
        precision=grounding,
        recall=coverage,
        f1=overall,
        ground_truth_ref=AUTO_REF,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run
