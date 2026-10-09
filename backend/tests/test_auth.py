import os
import subprocess
import sys

import bcrypt
import pytest

from app.core.security import hash_password, verify_password
from app.models import User
from conftest import BACKEND


def test_new_account_can_register_and_login(api):
    registered = api.client.post("/auth/register", json={"username": "daniel", "password": "correct-password-123"})
    assert registered.status_code == 201
    assert "password_hash" not in registered.json()["user"]
    logged_in = api.client.post("/auth/login", json={"identifier": "daniel", "password": "correct-password-123"})
    assert logged_in.status_code == 200
    assert logged_in.json()["user"]["id"] == registered.json()["user"]["id"]
    assert logged_in.json()["access_token"]
    assert api.client.post("/auth/login", json={"identifier": "daniel", "password": "incorrect-password"}).status_code == 401


def test_registration_prevents_username_phone_namespace_collisions(api):
    assert api.client.post(
        "/auth/register", json={"username": "13900000002", "password": "test-password-123"}
    ).status_code in {400, 409, 422}
    assert api.client.post(
        "/auth/register", json={"username": "daniel", "phone": "alice", "password": "test-password-123"}
    ).status_code in {400, 409, 422}


def test_legacy_namespace_collision_returns_controlled_error(api, password_hash):
    with api.session() as db:
        db.add(User(username="13900000002", password_hash=password_hash))
        db.commit()
    response = api.client.post("/auth/login", json={"identifier": "13900000002", "password": "test-password-123"})
    assert response.status_code in {400, 401, 409}
    assert isinstance(response.json()["detail"], str)


@pytest.mark.parametrize("prefix", ["a" * 72, "芒" * 40])
def test_long_password_suffix_is_significant(prefix):
    hashed = hash_password(prefix + "X")
    assert verify_password(prefix + "X", hashed)
    assert not verify_password(prefix + "Y", hashed)


def test_valid_legacy_bcrypt_is_upgraded_on_login(api):
    legacy = bcrypt.hashpw(b"legacy-password", bcrypt.gensalt()).decode()
    with api.session() as db:
        db.get(User, 1).password_hash = legacy
        db.commit()
    response = api.client.post("/auth/login", json={"identifier": "alice", "password": "legacy-password"})
    assert response.status_code == 200
    with api.session() as db:
        updated = db.get(User, 1).password_hash
    assert updated != legacy
    assert verify_password("legacy-password", updated)


def test_legacy_bcrypt_never_accepts_an_unverified_long_suffix():
    legacy = bcrypt.hashpw(b"a" * 72, bcrypt.gensalt()).decode()
    assert not verify_password("a" * 72 + "unexpected suffix", legacy)


def test_logout_revokes_old_token_without_revoking_other_sessions(api):
    another_login = api.client.post("/auth/login", json={"identifier": "alice", "password": "test-password-123"})
    assert another_login.status_code == 200
    newer_headers = {"Authorization": f"Bearer {another_login.json()['access_token']}"}
    assert api.client.post("/auth/logout", headers=api.headers()).status_code == 200
    assert api.client.get("/rooms/mine", headers=api.headers()).status_code == 401
    assert api.send().status_code == 401
    assert api.client.get("/rooms/mine", headers=newer_headers).status_code == 200


def test_production_without_jwt_secret_refuses_startup(tmp_path):
    environment = dict(os.environ)
    environment.update(APP_ENV="production", JWT_SECRET_KEY="", PYTHONPATH=str(BACKEND))
    result = subprocess.run(
        [sys.executable, "-c", "import app.core.config"],
        cwd=tmp_path, env=environment, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    assert "JWT_SECRET_KEY" in result.stderr
