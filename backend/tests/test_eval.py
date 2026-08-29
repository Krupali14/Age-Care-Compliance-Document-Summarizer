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
