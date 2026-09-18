import io

from tests.test_documents import _auth_header


def _document(client, session_local, headers):
    from app.models import Document, Obligation, Section, User

    db = session_local()
    user = db.query(User).filter_by(email="a@b.com").one()
    doc = Document(user_id=user.id, filename="policy.pdf", file_type="pdf", status="done")
    db.add(doc)
    db.flush()
    section = Section(document_id=doc.id, heading="Part 3", order_idx=0, page_ref=None, raw_text="x")
    db.add(section)
    db.flush()
    db.add(Obligation(document_id=doc.id, section_id=section.id, text="Notify the family", responsible_role="RN", priority="high"))
    db.commit()
    return doc.id


def test_upload_creates_a_check_and_schedules_it(client, session_local, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers = _auth_header(client)
    doc_id = _document(client, session_local, headers)

    resp = client.post(
        f"/api/compliance-checks/{doc_id}",
        headers=headers,
        files={"file": ("case.pdf", io.BytesIO(b"%PDF-1.4 evidence"), "application/pdf")},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "pending"

    listed = client.get(f"/api/compliance-checks/{doc_id}", headers=headers).json()
    assert len(listed) == 1
    assert listed[0]["filename"] == "case.pdf"


def test_upload_rejects_a_file_that_is_not_a_pdf_or_docx(client, session_local, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers = _auth_header(client)
    doc_id = _document(client, session_local, headers)

    resp = client.post(
        f"/api/compliance-checks/{doc_id}",
        headers=headers,
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert resp.status_code == 400


def test_checks_are_scoped_to_the_documents_owner(client, session_local, tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers = _auth_header(client)
    other = _auth_header(client, "b@b.com")
    doc_id = _document(client, session_local, headers)

    assert client.get(f"/api/compliance-checks/{doc_id}", headers=other).status_code == 404
    resp = client.post(
        f"/api/compliance-checks/{doc_id}",
        headers=other,
        files={"file": ("case.pdf", io.BytesIO(b"%PDF-1.4 evidence"), "application/pdf")},
    )
    assert resp.status_code == 404


def test_findings_are_served_and_a_check_can_be_deleted(client, session_local, tmp_path, monkeypatch):
    from app.models import CheckFinding, ComplianceCheck

    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers = _auth_header(client)
    other = _auth_header(client, "b@b.com")
    doc_id = _document(client, session_local, headers)

    db = session_local()
    check = ComplianceCheck(document_id=doc_id, filename="case.pdf", file_type="pdf", status="done")
    db.add(check)
    db.flush()
    db.add(CheckFinding(check_id=check.id, kind="obligation", source_id=1, section_id=None,
                        requirement="Notify the family", verdict="done",
                        evidence="Family notified at 3:30pm.", note="Notified promptly."))
    db.commit()
    check_id = check.id

    body = client.get(f"/api/compliance-checks/item/{check_id}", headers=headers).json()
    assert body["findings"][0]["verdict"] == "done"
    assert body["counts"]["done"] == 1

    # The uploaded case study itself — the most PII-dense file in the system —
    # must go with the row, not be left on the volume with nothing pointing at it.
    check_file = tmp_path / f"check{check_id}_case.pdf"
    check_file.write_bytes(b"%PDF-1.4")

    assert client.get(f"/api/compliance-checks/item/{check_id}", headers=other).status_code == 404
    assert client.delete(f"/api/compliance-checks/item/{check_id}", headers=headers).status_code == 204
    assert client.get(f"/api/compliance-checks/item/{check_id}", headers=headers).status_code == 404
    assert not check_file.exists()


def test_deleting_a_running_check_is_rejected(client, session_local, tmp_path, monkeypatch):
    from app.models import ComplianceCheck

    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    headers = _auth_header(client)
    doc_id = _document(client, session_local, headers)

    db = session_local()
    check = ComplianceCheck(document_id=doc_id, filename="case.pdf", file_type="pdf", status="processing")
    db.add(check)
    db.commit()
    check_id = check.id

    resp = client.delete(f"/api/compliance-checks/item/{check_id}", headers=headers)
    assert resp.status_code == 409

    # The row survives so run_check, still writing to it, is not left orphaning
    # findings against a deleted check.
    assert client.get(f"/api/compliance-checks/item/{check_id}", headers=headers).status_code == 200
