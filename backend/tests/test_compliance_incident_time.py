from datetime import datetime

from app.services.compliance_check import find_incident_datetime

FALLBACK = datetime(2026, 9, 17, 9, 0)


def test_a_stated_date_and_time_is_used():
    text = "The medication error occurred on 14 September 2026 at 3:10pm in Wing B."
    assert find_incident_datetime(text, FALLBACK) == (datetime(2026, 9, 14, 15, 10), "stated")


def test_a_24_hour_clock_is_understood():
    text = "Incident date: 14 September 2026. Time of incident: 15:10."
    assert find_incident_datetime(text, FALLBACK) == (datetime(2026, 9, 14, 15, 10), "stated")


def test_a_date_with_no_time_starts_at_midnight():
    text = "The fall occurred on 14 September 2026 and was reported the same day."
    assert find_incident_datetime(text, FALLBACK) == (datetime(2026, 9, 14, 0, 0), "stated")


def test_no_date_at_all_falls_back_to_the_upload_time():
    assert find_incident_datetime("A resident was unwell.", FALLBACK) == (FALLBACK, "upload_time")


def test_a_time_in_the_same_sentence_as_a_trigger_word_is_preferred():
    text = "08:00 - resident woke. 08:30 - breakfast. 09:15 - fall occurred. Incident date: 14 September 2026."
    assert find_incident_datetime(text, FALLBACK) == (datetime(2026, 9, 14, 9, 15), "stated")


def test_a_time_in_the_same_sentence_as_the_date_is_preferred_over_first_time():
    text = "Incident date: 14 September 2026, 15:10."
    assert find_incident_datetime(text, FALLBACK) == (datetime(2026, 9, 14, 15, 10), "stated")


def test_the_first_time_is_used_if_no_trigger_word_or_date_sentence_time():
    text = "08:00 - shift started. The medication error occurred on 14 September 2026."
    assert find_incident_datetime(text, FALLBACK) == (datetime(2026, 9, 14, 8, 0), "stated")


def test_dot_form_time_is_not_split_across_sentence_boundary():
    text = "The fall occurred at 3.10pm on 14 September 2026."
    assert find_incident_datetime(text, FALLBACK) == (datetime(2026, 9, 14, 15, 10), "stated")


def test_trigger_word_time_beats_date_sentence_time_when_both_are_present():
    text = "The error was discovered at 3.10pm. Incident date: 14 September 2026, 9:00am."
    assert find_incident_datetime(text, FALLBACK) == (datetime(2026, 9, 14, 15, 10), "stated")


def test_the_trigger_sentences_own_date_is_used_not_an_earlier_report_date():
    """A report header date and the incident's own date can differ — the incident's
    sentence names its own date, and that is the one relative deadlines must hang
    off, not whatever date happens to appear earliest in the document."""
    text = "Report date: 18 September 2026. The fall occurred on 14 September 2026 at 9:15am."
    assert find_incident_datetime(text, FALLBACK) == (datetime(2026, 9, 14, 9, 15), "stated")
