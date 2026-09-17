from datetime import datetime, timedelta

from app.services.deadlines import bucket_for, parse_relative, resolve_due_at

from tests.test_documents import _auth_header

ANCHOR = datetime(2026, 9, 17, 14, 0, 0)  # uploaded at 2pm


def test_relative_timeframe_resolves_from_the_upload_time():
    # "within 4 hours" on a 2pm upload is due at 6pm the same day.
    assert resolve_due_at("within 4 hours of the incident", ANCHOR) == datetime(2026, 9, 17, 18, 0, 0)
    assert resolve_due_at("within 30 days", ANCHOR) == ANCHOR + timedelta(days=30)
    assert parse_relative("30 days and 4 hours after the incident") == timedelta(days=30, hours=4)
    assert parse_relative("as soon as practicable") is None


def test_minute_scale_timeframes_resolve_from_the_upload_time():
    # "within 30 minutes" on a 2pm upload is due at 2:30pm the same day.
    assert parse_relative("within 30 minutes of the incident") == timedelta(minutes=30)
    assert resolve_due_at("within 30 minutes of the incident", ANCHOR) == datetime(2026, 9, 17, 14, 30, 0)
    assert parse_relative("within 1 hour and 30 minutes") == timedelta(hours=1, minutes=30)


def test_calendar_dates_fall_due_at_the_end_of_their_day():
    assert resolve_due_at("2026-12-31", ANCHOR) == datetime(2026, 12, 31, 23, 59, 59)
    assert resolve_due_at("by 31 December 2026", ANCHOR) == datetime(2026, 12, 31, 23, 59, 59)
    assert resolve_due_at(None, ANCHOR) is None
    assert resolve_due_at("as soon as practicable", ANCHOR) is None


def test_buckets_follow_time_remaining():
    now = ANCHOR
    assert bucket_for(now - timedelta(minutes=1), now) == "overdue"
    assert bucket_for(now + timedelta(hours=4), now) == "within_24_hours"
    assert bucket_for(now + timedelta(days=3), now) == "within_7_days"
    assert bucket_for(now + timedelta(days=20), now) == "within_30_days"
    assert bucket_for(now + timedelta(days=200), now) == "later"
    assert bucket_for(None, now) == "no_date"


def _seed(session_local, due_date):
    from app.models import Deadline, Document, Section, User

    db = session_local()
    user = db.query(User).filter_by(email="a@b.com").one()
    doc = Document(user_id=user.id, filename="d.pdf", file_type="pdf", status="done",
                   uploaded_at=datetime.utcnow())
    db.add(doc)
    db.flush()
    section = Section(document_id=doc.id, heading="S", order_idx=0, page_ref=None, raw_text="t")
    db.add(section)
    db.flush()
    deadline = Deadline(document_id=doc.id, section_id=section.id, description="Report it", due_date=due_date)
    db.add(deadline)
    db.commit()
    return doc.id, deadline.id


def test_deadlines_endpoint_serves_due_at_bucket_and_status(client, session_local):
    headers = _auth_header(client)
    doc_id, _ = _seed(session_local, "within 4 hours of the incident")

    row = client.get(f"/api/deadlines/{doc_id}", headers=headers).json()[0]
    assert row["bucket"] == "within_24_hours"
    assert row["status"] == "not_started"
    assert row["due_at"] is not None


def test_deadline_status_can_be_set_and_is_rejected_when_unknown_or_not_owned(client, session_local):
    headers = _auth_header(client)
    other = _auth_header(client, "b@b.com")
    doc_id, deadline_id = _seed(session_local, "2026-12-31")

    assert client.patch(f"/api/deadlines/item/{deadline_id}", headers=headers, json={"status": "in_progress"}).status_code == 200
    assert client.get(f"/api/deadlines/{doc_id}", headers=headers).json()[0]["status"] == "in_progress"

    assert client.patch(f"/api/deadlines/item/{deadline_id}", headers=headers, json={"status": "invented"}).status_code == 422
    assert client.patch(f"/api/deadlines/item/{deadline_id}", headers=other, json={"status": "completed"}).status_code == 404
