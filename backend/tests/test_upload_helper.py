import io
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile

from app.routers.upload import save_upload


def _upload(name: str, data: bytes) -> UploadFile:
    return UploadFile(filename=name, file=io.BytesIO(data))


def test_save_upload_writes_the_file_with_its_prefix(tmp_path):
    path, name = save_upload(_upload("case.pdf", b"%PDF-1.4 body"), tmp_path, "check-7")
    assert name == "case.pdf"
    assert path == Path(tmp_path) / "check-7_case.pdf"
    assert path.read_bytes() == b"%PDF-1.4 body"


def test_save_upload_rejects_a_disallowed_extension(tmp_path):
    with pytest.raises(HTTPException) as exc:
        save_upload(_upload("notes.txt", b"hello"), tmp_path, "check-7")
    assert exc.value.status_code == 400


def test_save_upload_rejects_a_file_whose_bytes_do_not_match_its_extension(tmp_path):
    with pytest.raises(HTTPException) as exc:
        save_upload(_upload("case.pdf", b"not a pdf at all"), tmp_path, "check-7")
    assert exc.value.status_code == 400
    assert list(Path(tmp_path).iterdir()) == []


def test_save_upload_rejects_an_empty_file(tmp_path):
    with pytest.raises(HTTPException) as exc:
        save_upload(_upload("case.pdf", b""), tmp_path, "check-7")
    assert exc.value.status_code == 400
