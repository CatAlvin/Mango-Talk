from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select

from app.models import Message
from conftest import receive_event


def test_latest_window_and_cursor_pages_cover_every_message(api):
    with api.session() as db:
        db.add_all([
            Message(
                id=index, room_id=10, sender_id=1, content=f"Message {index}",
                created_at=datetime(2026, 1, 1) + timedelta(seconds=index),
            )
            for index in range(1, 126)
        ])
        db.commit()

    latest = api.client.get("/messages/room/10", headers=api.headers())
    assert latest.status_code == 200
    assert [item["id"] for item in latest.json()] == list(range(76, 126))

    pages = [latest.json()]
    while pages[-1]:
        cursor = pages[-1][0]["id"]
        response = api.client.get(
            "/messages/room/10", headers=api.headers(),
            params={"before_id": cursor},
        )
        assert response.status_code == 200
        batch = response.json()
        assert all(item["id"] < cursor for item in batch)
        pages.append(batch)
    assert [item["id"] for page in reversed(pages) for item in page] == list(range(1, 126))

    recovered = []
    cursor = 13
    while True:
        response = api.client.get(
            "/messages/room/10", headers=api.headers(), params={"after_id": cursor, "limit": 31}
        )
        assert response.status_code == 200
        batch = response.json()
        if not batch:
            break
        assert all(item["id"] > cursor for item in batch)
        recovered.extend(item["id"] for item in batch)
        cursor = batch[-1]["id"]
    assert recovered == list(range(14, 126))


def test_cursor_directions_cannot_be_combined(api):
    response = api.client.get(
        "/messages/room/10", headers=api.headers(), params={"before_id": 8, "after_id": 2}
    )
    assert response.status_code == 400


def test_nonmembers_cannot_read_send_or_recall(api):
    sent = api.send(content="Private conversation")
    assert sent.status_code == 201
    message_id = sent.json()["data"]["id"]
    assert api.client.get("/messages/room/10", headers=api.headers("carol")).status_code == 403
    assert api.send(user="carol").status_code == 403
    assert api.client.post(f"/messages/{message_id}/recall", headers=api.headers("carol")).status_code == 403
    assert api.client.post(f"/messages/{message_id}/recall", headers=api.headers("bob")).status_code == 403
    assert api.client.get("/messages/room/10").status_code == 401


def test_idempotent_retry_and_room_sender_scope(api):
    client_id = str(uuid4())
    first = api.send(content="One message", client_message_id=client_id)
    retry = api.send(content="One message", client_message_id=client_id)
    assert first.status_code == 201
    assert retry.status_code in {200, 201}
    first_message = first.json()["data"]
    assert retry.json()["data"]["id"] == first_message["id"]
    assert first_message["client_message_id"] == client_id
    assert api.send(content="Changed", client_message_id=client_id).status_code == 409

    another_room = api.send(room=20, content="One message", client_message_id=client_id)
    another_sender = api.send(user="bob", content="One message", client_message_id=client_id)
    assert another_room.status_code == another_sender.status_code == 201
    assert len({first_message["id"], another_room.json()["data"]["id"], another_sender.json()["data"]["id"]}) == 3
    with api.session() as db:
        assert db.scalar(select(func.count(Message.id))) == 3


def test_http_and_websocket_share_idempotency(api):
    client_id = str(uuid4())
    with api.websocket() as socket:
        assert receive_event(socket)["event"] == "connected"
        socket.send_json({"action": "send_message", "data": {"content": "Retry me", "client_message_id": client_id}})
        initial = receive_event(socket)
        assert initial["event"] == "new_message"
        retry = api.send(content="Retry me", client_message_id=client_id)
        assert retry.status_code in {200, 201}
        assert retry.json()["data"]["id"] == initial["data"]["id"]
    with api.session() as db:
        assert db.scalar(select(func.count(Message.id))) == 1


def test_idempotency_rejects_changed_reply_or_attachment(api):
    original = api.send(content="Original").json()["data"]["id"]
    another_original = api.send(content="Another original").json()["data"]["id"]
    reply_key = str(uuid4())
    reply = api.send(content="Reply", reply_to_message_id=original, client_message_id=reply_key)
    assert reply.status_code == 201
    assert api.send(
        content="Reply", reply_to_message_id=another_original, client_message_id=reply_key
    ).status_code == 409

    first_upload = api.upload().json()["data"]["upload_id"]
    second_upload = api.upload(name="another.txt", body=b"different").json()["data"]["upload_id"]
    file_key = str(uuid4())
    first = api.send(content=None, message_type="file", attachments=[{"upload_id": first_upload}], client_message_id=file_key)
    assert first.status_code == 201
    retry = api.send(content=None, message_type="file", attachments=[{"upload_id": first_upload}], client_message_id=file_key)
    assert retry.status_code in {200, 201}
    assert retry.json()["data"]["id"] == first.json()["data"]["id"]
    assert api.send(
        content=None, message_type="file", attachments=[{"upload_id": second_upload}], client_message_id=file_key
    ).status_code == 409


def test_recall_hides_text_and_reply_preview(api):
    sent = api.send(content="Private original text")
    original = sent.json()["data"]["id"]
    reply = api.send(user="bob", content="Reply", reply_to_message_id=original)
    assert reply.status_code == 201
    assert reply.json()["data"]["replied_message"]["content"] == "Private original text"
    recalled = api.client.post(f"/messages/{original}/recall", headers=api.headers())
    assert recalled.status_code == 200
    assert recalled.json()["data"]["content"] is None
    assert recalled.json()["data"]["attachments"] == []
    history = api.client.get("/messages/room/10", headers=api.headers("bob")).json()
    assert history[0]["is_recalled"] is True
    assert history[0]["content"] is None
    assert history[1]["replied_message"]["content"] is None
    assert history[1]["replied_message"]["attachments"] == []


def test_reply_cannot_point_to_another_room(api):
    original = api.send(room=20).json()["data"]["id"]
    assert api.send(reply_to_message_id=original).status_code == 400


def test_context_contains_target_and_never_returns_another_rooms_messages(api):
    with api.session() as db:
        db.add_all([
            Message(id=index, room_id=10 if index % 2 else 30, sender_id=1, content=f"Message {index}")
            for index in range(1, 121)
        ])
        db.commit()
    response = api.client.get("/messages/61/context", headers=api.headers("bob"), params={"limit": 11})
    assert response.status_code == 200
    messages = response.json()
    assert len(messages) == 11
    assert [item["id"] for item in messages] == list(range(51, 72, 2))
    assert all(item["room_id"] == 10 for item in messages)
    assert api.client.get("/messages/62/context", headers=api.headers("bob")).status_code == 403
    assert api.client.get("/messages/61/context", headers=api.headers("carol")).status_code == 403


def test_sync_refreshes_recalled_messages_and_filters_foreign_ids(api):
    upload_id = api.upload().json()["data"]["upload_id"]
    private = api.send(content="Private attachment", message_type="file", attachments=[{"upload_id": upload_id}]).json()["data"]["id"]
    foreign = api.send(room=30, content="Other private room").json()["data"]["id"]
    assert api.client.post(f"/messages/{private}/recall", headers=api.headers()).status_code == 200
    response = api.client.post(
        "/messages/room/10/sync", headers=api.headers("bob"), json={"ids": [foreign, private, private, 99999]}
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == private
    assert response.json()[0]["is_recalled"] is True
    assert response.json()[0]["content"] is None
    assert response.json()[0]["attachments"] == []
    assert api.client.post("/messages/room/10/sync", headers=api.headers("carol"), json={"ids": [private]}).status_code == 403
