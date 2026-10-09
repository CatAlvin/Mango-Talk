from uuid import uuid4

import pytest
from sqlalchemy import func, select
from starlette.websockets import WebSocketDisconnect

from app.models import ChatRoomMember, Message, User
from conftest import receive_event


@pytest.mark.parametrize("payload", [
    [],
    123,
    {"action": "send_message", "data": []},
    {"action": "send_message", "data": {"content": 123}},
    {"action": "send_message", "data": {"content": "Hello", "attachments": "wrong"}},
])
def test_malformed_input_reports_error_and_connection_can_continue(api, payload):
    with api.websocket() as socket:
        assert receive_event(socket)["event"] == "connected"
        socket.send_json(payload)
        error = receive_event(socket)
        assert error["event"] == "error"
        assert error["data"]["message"]
        socket.send_json({"action": "ping"})
        assert receive_event(socket)["event"] == "pong"
        socket.send_json({"action": "send_message", "data": {"content": "Still connected", "client_message_id": str(uuid4())}})
        message = receive_event(socket)
        assert message["event"] == "new_message"
        assert message["data"]["content"] == "Still connected"


def test_nonmember_cannot_open_websocket(api):
    with pytest.raises(WebSocketDisconnect) as error:
        with api.websocket(user="carol"):
            pass
    assert error.value.code == 1008


def test_disabled_account_cannot_keep_sending_on_existing_socket(api):
    with api.websocket() as socket:
        assert receive_event(socket)["event"] == "connected"
        with api.session() as db:
            db.get(User, 1).is_active = False
            db.commit()
        socket.send_json({"action": "send_message", "data": {"content": "Blocked", "client_message_id": str(uuid4())}})
        try:
            assert receive_event(socket)["event"] == "error"
            with pytest.raises(WebSocketDisconnect) as error:
                receive_event(socket)
        except WebSocketDisconnect as closed:
            assert closed.code == 1008
        else:
            assert error.value.code == 1008
    with api.session() as db:
        assert db.scalar(select(func.count(Message.id))) == 0


def test_member_muted_after_connect_cannot_send(api):
    with api.websocket() as socket:
        assert receive_event(socket)["event"] == "connected"
        with api.session() as db:
            membership = db.scalar(select(ChatRoomMember).where(ChatRoomMember.room_id == 10, ChatRoomMember.user_id == 1))
            membership.is_muted = True
            db.commit()
        socket.send_json({"action": "send_message", "data": {"content": "Blocked", "client_message_id": str(uuid4())}})
        assert receive_event(socket)["event"] == "error"
    assert api.send(content="Also blocked").status_code == 403


def test_http_send_and_recall_broadcast_to_online_members(api):
    with api.websocket(user="bob") as socket:
        assert receive_event(socket)["event"] == "connected"
        sent = api.send(content="Sent over HTTP")
        assert sent.status_code == 201
        event = receive_event(socket)
        assert event["event"] == "new_message"
        assert event["data"]["id"] == sent.json()["data"]["id"]
        assert event["data"]["client_message_id"] == sent.json()["data"]["client_message_id"]
        recalled = api.client.post(f"/messages/{event['data']['id']}/recall", headers=api.headers())
        assert recalled.status_code == 200
        recall_event = receive_event(socket)
        assert recall_event["event"] == "message_recalled"
        assert recall_event["data"]["id"] == event["data"]["id"]


def test_invalid_json_does_not_disconnect_authenticated_socket(api):
    with api.websocket() as socket:
        assert receive_event(socket)["event"] == "connected"
        socket.send_text("{not valid json")
        assert receive_event(socket)["event"] == "error"
        socket.send_json({"action": "ping"})
        assert receive_event(socket)["event"] == "pong"


def test_user_socket_receives_created_rooms_and_updates_for_other_rooms(api):
    with api.user_socket("bob") as member_socket, api.user_socket("carol") as outsider_socket:
        assert receive_event(member_socket)["event"] == "connected"
        assert receive_event(outsider_socket)["event"] == "connected"
        created = api.client.post("/rooms/group", headers=api.headers(), json={"name": "Product team", "member_user_ids": [2]})
        assert created.status_code == 201
        new_room = created.json()["room"]["id"]
        event = receive_event(member_socket)
        assert event["event"] == "room_created"
        assert event["data"]["room_id"] == new_room
        sent = api.send(room=new_room, content="New room update")
        assert sent.status_code == 201
        update = receive_event(member_socket)
        assert update["event"] == "room_updated"
        assert update["data"]["room_id"] == new_room
        assert update["data"]["message"]["id"] == sent.json()["data"]["id"]
        outsider_socket.send_json({"action": "ping"})
        assert receive_event(outsider_socket)["event"] == "pong"


def test_existing_socket_cannot_continue_after_logout(api):
    with api.websocket() as socket:
        assert receive_event(socket)["event"] == "connected"
        assert api.client.post("/auth/logout", headers=api.headers()).status_code == 200
        socket.send_json({"action": "ping"})
        assert receive_event(socket)["event"] == "error"
        with pytest.raises(WebSocketDisconnect) as error:
            receive_event(socket)
        assert error.value.code == 1008
