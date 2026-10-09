from datetime import datetime

from app.models import ChatRoom, Message


def room_from_list(api, room_id=10, user="bob"):
    response = api.client.get("/rooms/mine", headers=api.headers(user))
    assert response.status_code == 200
    return next(item for item in response.json() if item["id"] == room_id)


def test_unread_excludes_own_recalled_and_read_messages(api):
    first = api.send(content="First").json()["data"]["id"]
    second = api.send(content="Second").json()["data"]["id"]
    api.send(user="bob", content="My own reply")
    assert room_from_list(api)["unread_count"] == 2
    assert room_from_list(api, user="alice")["unread_count"] == 1
    partial = api.client.post("/rooms/10/read", headers=api.headers("bob"), json={"message_id": first})
    assert partial.status_code == 200
    assert room_from_list(api)["unread_count"] == 1
    read = api.client.post("/rooms/10/read", headers=api.headers("bob"), json={"message_id": second})
    assert read.status_code == 200
    assert room_from_list(api)["unread_count"] == 0
    stale = api.client.post("/rooms/10/read", headers=api.headers("bob"), json={"message_id": first})
    assert stale.status_code == 200
    assert stale.json()["message_id"] == second

    newest = api.send(content="New arrival").json()["data"]["id"]
    assert room_from_list(api)["unread_count"] == 1
    assert api.client.post(f"/messages/{newest}/recall", headers=api.headers()).status_code == 200
    room = room_from_list(api)
    assert room["unread_count"] == 0
    assert room["last_message"]["id"] == newest
    assert room["last_message"]["is_recalled"] is True
    assert room["last_message"]["content"] is None


def test_mark_read_cannot_use_other_rooms_message_or_other_membership(api):
    wrong_room = api.send(room=20).json()["data"]["id"]
    assert api.client.post("/rooms/10/read", headers=api.headers("bob"), json={"message_id": wrong_room}).status_code == 400
    assert api.client.post("/rooms/10/read", headers=api.headers("carol"), json={"message_id": wrong_room}).status_code == 403


def test_room_list_orders_by_activity_and_includes_latest_summary(api):
    group_message = api.send(room=20, content="Group update").json()["data"]["id"]
    private_message = api.send(content="Private update").json()["data"]["id"]
    with api.session() as db:
        for room_id in (10, 20, 30):
            db.get(ChatRoom, room_id).created_at = datetime(2026, 1, 1)
        db.get(Message, group_message).created_at = datetime(2026, 1, 2)
        db.get(Message, private_message).created_at = datetime(2026, 1, 3)
        db.commit()
    response = api.client.get("/rooms/mine", headers=api.headers())
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [10, 20, 30]
    assert response.json()[0]["last_message"]["content"] == "Private update"
    assert response.json()[1]["last_message"]["content"] == "Group update"
    assert response.json()[2]["last_message"] is None


def test_private_room_is_shared_when_created_from_either_side(api):
    first = api.client.post("/rooms/private", headers=api.headers("bob"), json={"target_user_id": 3})
    second = api.client.post("/rooms/private", headers=api.headers("carol"), json={"target_user_id": 2})
    assert first.status_code == second.status_code == 200
    assert first.json()["room"]["id"] == second.json()["room"]["id"]
    assert api.client.post("/rooms/private", headers=api.headers(), json={"target_user_id": 1}).status_code == 400
