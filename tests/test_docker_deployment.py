from pathlib import Path


def test_compose_seeds_managed_config_without_process_owned_user_settings() -> None:
    compose = Path("compose.yaml").read_text(encoding="utf-8")

    assert "env_file:" not in compose
    assert "FCC_ENV_FILE: /run/fcc/bootstrap.env" in compose
    assert "source: ./.env" in compose
    assert "target: /run/fcc/bootstrap.env" in compose
    assert "read_only: true" in compose


def test_compose_admin_is_host_local_and_trusts_only_fixed_gateway() -> None:
    compose = Path("compose.yaml").read_text(encoding="utf-8")

    assert '"127.0.0.1:8082:8082"' in compose
    assert "FCC_ADMIN_TRUSTED_CLIENT_IPS: 172.30.0.1" in compose
    assert "subnet: 172.30.0.0/24" in compose
    assert "gateway: 172.30.0.1" in compose
