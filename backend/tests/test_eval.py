def test_score_category_exact_match():
    from app.services.eval_scoring import score_category
    predicted = ["Staff must report incidents within 24 hours"]
    ground_truth = ["Staff must report incidents within 24 hours"]
    precision, recall, f1 = score_category(predicted, ground_truth)
    assert precision == 1.0
    assert recall == 1.0
    assert f1 == 1.0


def test_score_category_partial_match_uses_fuzzy_threshold():
    from app.services.eval_scoring import score_category
    predicted = ["Staff should report incidents inside 24 hrs", "Unrelated extracted line"]
    ground_truth = ["Staff must report incidents within 24 hours"]
    precision, recall, f1 = score_category(predicted, ground_truth)
    assert 0 < precision < 1
    assert recall == 1.0


def test_score_category_no_match():
    from app.services.eval_scoring import score_category
    precision, recall, f1 = score_category(["completely different"], ["Staff must report incidents"])
    assert precision == 0.0
    assert recall == 0.0
    assert f1 == 0.0


def _auth_header(client, email="a@b.com"):
    client.post("/api/auth/register", json={"email": email, "password": "secret123"})
    resp = client.post("/api/auth/login", data={"username": email, "password": "secret123"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_post_eval_scores_document_and_persists_run(client, db_session, tmp_path, monkeypatch):
    import io
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers = _auth_header(client)
    upload_resp = client.post("/api/upload", headers=headers, files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")})
    doc_id = upload_resp.json()["id"]

    from app.models import Section, Obligation
    section = Section(document_id=doc_id, heading="H", order_idx=0, page_ref=None, raw_text="text")
    db_session.add(section)
    db_session.flush()
    db_session.add(Obligation(document_id=doc_id, section_id=section.id, text="Staff must report incidents within 24 hours", responsible_role=None, priority=None))
    db_session.commit()

    resp = client.post(
        f"/api/documents/{doc_id}/eval",
        headers=headers,
        json={"ground_truth": {"obligations": ["Staff must report incidents within 24 hours"], "risks": []}},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["precision"] == 1.0
    assert body["recall"] == 1.0
    assert body["f1"] == 1.0
    assert body["ground_truth_ref"] == "api"

    list_resp = client.get(f"/api/documents/{doc_id}/eval", headers=headers)
    assert len(list_resp.json()) == 1


def test_post_eval_not_owned_returns_404(client, tmp_path, monkeypatch):
    import io
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers_a = _auth_header(client, "a@b.com")
    headers_b = _auth_header(client, "b@b.com")
    upload_resp = client.post("/api/upload", headers=headers_a, files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")})
    doc_id = upload_resp.json()["id"]

    resp = client.post(f"/api/documents/{doc_id}/eval", headers=headers_b, json={"ground_truth": {"obligations": []}})
    assert resp.status_code == 404


def _doc_with_findings(db):
    """A document whose findings are grounded in their sections, plus one that isn't."""
    from app.models import Document, Obligation, Risk, Section, User

    user = db.query(User).filter_by(email="a@b.com").first()
    if user is None:
        user = User(email="a@b.com", hashed_password="h")
        db.add(user)
        db.flush()
    doc = Document(user_id=user.id, filename="d.pdf", file_type="pdf", status="done")
    db.add(doc)
    db.flush()

    grounded_section = Section(
        document_id=doc.id, heading="Incidents", order_idx=0, page_ref=None,
        raw_text="The registered provider must notify the Commission of a reportable incident within 24 hours.",
    )
    quiet_section = Section(
        document_id=doc.id, heading="Definitions", order_idx=1, page_ref=None,
        raw_text="In this document, 'provider' means an approved provider of aged care services.",
    )
    toc_fragment = Section(
        document_id=doc.id, heading="Contents", order_idx=2, page_ref=None, raw_text="ii Act 2024",
    )
    db.add_all([grounded_section, quiet_section, toc_fragment])
    db.flush()

    db.add(Obligation(
        document_id=doc.id, section_id=grounded_section.id,
        text="The registered provider must notify the Commission of a reportable incident.",
    ))
    db.add(Risk(
        document_id=doc.id, section_id=grounded_section.id,
        text="Bananas are delivered to the wrong warehouse in Belgium", severity="high",
    ))
    db.commit()
    return doc, grounded_section, quiet_section, toc_fragment


def test_auto_eval_scores_grounding_and_coverage_without_ground_truth(db_session):
    """The automatic run needs no hand-annotated answers: it measures how well each
    finding is supported by the section it cites, and how much of the document
    produced findings at all."""
    from app.services.eval_scoring import AUTO_REF, run_auto_eval

    doc, grounded, quiet, toc = _doc_with_findings(db_session)
    run = run_auto_eval(db_session, doc.id)

    # One of the two findings is carried by its section; the invented one is not.
    assert run.precision == 0.5
    # Two sections are long enough to extract from; one of them produced findings.
    # The table-of-contents fragment is not counted against coverage.
    assert run.recall == 0.5
    assert run.f1 == 0.5
    assert run.ground_truth_ref == AUTO_REF


def test_auto_eval_persists_the_run(db_session):
    from app.models import EvalRun
    from app.services.eval_scoring import run_auto_eval

    doc, *_ = _doc_with_findings(db_session)
    run_auto_eval(db_session, doc.id)
    run_auto_eval(db_session, doc.id)

    stored = db_session.query(EvalRun).filter_by(document_id=doc.id).all()
    assert len(stored) == 2, "each evaluation is stored, so runs can be compared over time"


def test_auto_eval_endpoint_creates_and_returns_a_run(client, db_session, tmp_path, monkeypatch):
    import io
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers = _auth_header(client, "auto@b.com")
    from unittest.mock import patch
    with patch("app.services.processing.parse_document", return_value=[]):
        doc_id = client.post(
            "/api/upload", headers=headers,
            files={"file": ("d.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
        ).json()["id"]

    from app.models import Document
    doc = db_session.query(Document).filter_by(id=doc_id).one()
    doc.status = "done"
    db_session.commit()

    resp = client.post(f"/api/documents/{doc_id}/eval/auto", headers=headers)
    assert resp.status_code == 201
    assert resp.json()["ground_truth_ref"] == "auto"

    listed = client.get(f"/api/documents/{doc_id}/eval", headers=headers).json()
    assert len(listed) == 1


def test_auto_eval_refuses_a_document_that_is_not_finished(client, db_session, tmp_path, monkeypatch):
    """Scoring a half-processed document would report a meaningless number."""
    import io
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers = _auth_header(client, "pending@b.com")
    from unittest.mock import patch
    with patch("app.services.processing.parse_document", side_effect=RuntimeError("boom")):
        doc_id = client.post(
            "/api/upload", headers=headers,
            files={"file": ("d.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
        ).json()["id"]

    resp = client.post(f"/api/documents/{doc_id}/eval/auto", headers=headers)
    assert resp.status_code == 409


def test_ground_truth_eval_rejects_empty_ground_truth(client, tmp_path, monkeypatch):
    """Averaging over no categories divided by zero and returned a 500."""
    import io
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers = _auth_header(client, "empty@b.com")
    from unittest.mock import patch
    with patch("app.services.processing.parse_document", return_value=[]):
        doc_id = client.post(
            "/api/upload", headers=headers,
            files={"file": ("d.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
        ).json()["id"]

    resp = client.post(f"/api/documents/{doc_id}/eval", headers=headers, json={"ground_truth": {}})
    assert resp.status_code == 400
