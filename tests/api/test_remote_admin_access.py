import base64

from fastapi.testclient import TestClient

from free_claude_code.config.loader import clear_settings_cache
from tests.api.support import create_test_app


def _basic(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {token}"


def _remote_client(app) -> TestClient:
    return TestClient(
        app,
        base_url="https://api.lingxilearn.cn",
        client=("203.0.113.10", 50000),
    )


def _configure_remote(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("FCC_ADMIN_REMOTE_ENABLED", "true")
    monkeypatch.setenv("FCC_ADMIN_REMOTE_HOST", "api.lingxilearn.cn")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "admin-secret")
    clear_settings_cache()


def test_remote_admin_requires_basic_auth(monkeypatch, tmp_path):
    _configure_remote(monkeypatch, tmp_path)
    client = _remote_client(create_test_app())

    response = client.get("/admin")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == 'Basic realm="FCC Admin"'


def test_remote_admin_accepts_configured_host_and_token(monkeypatch, tmp_path):
    _configure_remote(monkeypatch, tmp_path)
    client = _remote_client(create_test_app())

    response = client.get(
        "/admin",
        headers={"Authorization": _basic("admin", "admin-secret")},
    )

    assert response.status_code == 200


def test_remote_admin_rejects_wrong_password(monkeypatch, tmp_path):
    _configure_remote(monkeypatch, tmp_path)
    client = _remote_client(create_test_app())

    response = client.get(
        "/admin",
        headers={"Authorization": _basic("admin", "wrong")},
    )

    assert response.status_code == 401


def test_remote_admin_rejects_other_host(monkeypatch, tmp_path):
    _configure_remote(monkeypatch, tmp_path)
    client = TestClient(
        create_test_app(),
        base_url="https://attacker.example",
        client=("203.0.113.10", 50000),
    )

    response = client.get(
        "/admin",
        headers={"Authorization": _basic("admin", "admin-secret")},
    )

    assert response.status_code == 403


def test_remote_admin_rejects_cross_origin(monkeypatch, tmp_path):
    _configure_remote(monkeypatch, tmp_path)
    client = _remote_client(create_test_app())

    response = client.get(
        "/admin/api/config",
        headers={
            "Authorization": _basic("admin", "admin-secret"),
            "Origin": "https://attacker.example",
        },
    )

    assert response.status_code == 403
