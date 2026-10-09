import struct
from urllib.parse import parse_qs, urlsplit
import zlib

from jose import jwt
import pytest
from sqlalchemy import delete

from app.core.config import settings
from app.models import ChatRoomMember, User


def png_chunk(kind, data):
    chunk = kind + data
    return struct.pack(">I", len(data)) + chunk + struct.pack(">I", zlib.crc32(chunk))


PNG = (
    b"\x89PNG\r\n\x1a\n"
    + png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
    + png_chunk(b"IDAT", zlib.compress(b"\0\0\0\0\xff"))
    + png_chunk(b"IEND", b"")
)


def access_url(api, upload_id, user="alice"):
    response = api.client.get(f"/uploads/{upload_id}/access", headers=api.headers(user))
    assert response.status_code == 200, response.text
    return response.json()["data"]["file_url"]


def test_upload_requires_authentication(api):
    response = api.client.post("/uploads", files={"file": ("notes.txt", b"notes", "text/plain")})
    assert response.status_code == 401


def test_upload_ownership_member_access_and_recall(api):
    uploaded = api.upload()
    assert uploaded.status_code == 201, uploaded.text
    data = uploaded.json()["data"]
    upload_id = data["upload_id"]
    assert data["file_size"] == len(b"Meeting notes")
    assert "storage_path" not in data
    initial_url = data["file_url"]
    assert api.client.get(initial_url).content == b"Meeting notes"
    assert api.client.get(f"/uploads/{upload_id}/access", headers=api.headers("bob")).status_code == 403
    assert api.send(user="bob", message_type="file", content=None, attachments=[{"upload_id": upload_id}]).status_code == 403

    sent = api.send(message_type="file", content=None, attachments=[{"upload_id": upload_id}])
    assert sent.status_code == 201, sent.text
    message = sent.json()["data"]
    assert message["attachments"][0]["upload_id"] == upload_id
    assert "storage_path" not in message["attachments"][0]
    member_url = access_url(api, upload_id, "bob")
    downloaded = api.client.get(member_url)
    assert downloaded.status_code == 200
    assert downloaded.content == b"Meeting notes"
    assert "attachment" in downloaded.headers.get("content-disposition", "")
    assert downloaded.headers.get("x-content-type-options") == "nosniff"
    assert api.client.get(f"/uploads/{upload_id}/access", headers=api.headers("carol")).status_code == 403
    assert api.send(room=20, message_type="file", content=None, attachments=[{"upload_id": upload_id}]).status_code in {400, 409}

    recalled = api.client.post(f"/messages/{message['id']}/recall", headers=api.headers())
    assert recalled.status_code == 200
    assert recalled.json()["data"]["attachments"] == []
    assert api.client.get(member_url).status_code in {403, 404, 410}
    assert api.client.get(initial_url).status_code in {403, 404, 410}
    assert api.client.get(f"/uploads/{upload_id}/access", headers=api.headers("bob")).status_code in {403, 404, 410}


def test_download_token_cannot_be_omitted_tampered_or_reused_for_another_file(api):
    first = api.upload().json()["data"]
    second = api.upload(name="second.txt", body=b"second").json()["data"]
    parsed = urlsplit(first["file_url"])
    token = parse_qs(parsed.query)["access_token"][0]
    assert api.client.get(parsed.path).status_code in {401, 403, 422}
    assert api.client.get(parsed.path, params={"access_token": token + "tampered"}).status_code in {401, 403}
    assert api.client.get(
        f"/uploads/{second['upload_id']}/download", params={"access_token": token}
    ).status_code in {401, 403}
    assert api.client.get(
        parsed.path, params={"access_token": api.tokens["alice"]}
    ).status_code in {401, 403}
    claims = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    expired = jwt.encode({**claims, "exp": 0}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    assert api.client.get(parsed.path, params={"access_token": expired}).status_code in {401, 403}


@pytest.mark.parametrize("revocation", ["disabled_account", "removed_member"])
def test_download_rechecks_access_after_a_signed_link_has_been_issued(api, revocation):
    upload_id = api.upload().json()["data"]["upload_id"]
    assert api.send(content=None, message_type="file", attachments=[{"upload_id": upload_id}]).status_code == 201
    member_url = access_url(api, upload_id, "bob")
    assert api.client.get(member_url).status_code == 200
    with api.session() as db:
        if revocation == "disabled_account":
            db.get(User, 2).is_active = False
        else:
            db.execute(delete(ChatRoomMember).where(ChatRoomMember.room_id == 10, ChatRoomMember.user_id == 2))
        db.commit()
    assert api.client.get(member_url).status_code == 403


@pytest.mark.parametrize("name,body,mime", [
    ("page.html", b"<!doctype html><title>Meeting</title>", "text/html"),
    ("page.htm", b"<html><body>Meeting</body></html>", "application/octet-stream"),
    ("drawing.svg", b'<svg xmlns="http://www.w3.org/2000/svg" />', "image/svg+xml"),
    ("fake.png", b"this is not an image", "image/png"),
    ("broken.png", b"\x89PNG\r\n\x1a\ninvalid image body", "image/png"),
    ("empty.txt", b"", "text/plain"),
])
def test_unsafe_or_invalid_uploads_are_rejected(api, name, body, mime):
    response = api.upload(name=name, body=body, mime=mime)
    assert response.status_code == 400
    assert isinstance(response.json()["detail"], str)


def test_valid_png_can_be_sent_as_image(api):
    uploaded = api.upload(name="pixel.png", body=PNG, mime="image/png")
    assert uploaded.status_code == 201, uploaded.text
    data = uploaded.json()["data"]
    assert data["attachment_type"] == "image"
    sent = api.send(content=None, message_type="image", attachments=[{"upload_id": data["upload_id"]}])
    assert sent.status_code == 201, sent.text
    assert api.client.get(sent.json()["data"]["attachments"][0]["file_url"]).status_code == 200
