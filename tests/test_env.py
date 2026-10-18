from qate.core import features

from qate_env.env import FEATURES_FILE_NAME, Env
from qate_env.env_name import EnvName


def test_enter_loads_features_from_the_environment(monkeypatch, tmp_path):
    env = Env(str(tmp_path), EnvName("EXAMPLE"), work_dir=tmp_path)
    configured = ["DISABLE_INVENTORY_HEALTH_CHECK"]

    monkeypatch.setattr(env, "visit", lambda: None)
    monkeypatch.setattr(env, "lock", lambda: None)
    monkeypatch.setattr(
        env,
        "load_object",
        lambda file_name: configured if file_name == FEATURES_FILE_NAME else None,
    )
    monkeypatch.setattr(features, "_ENABLED", frozenset())

    env.enter()

    assert features.get("DISABLE_INVENTORY_HEALTH_CHECK")


def test_enter_clears_features_when_the_environment_has_no_feature_file(monkeypatch, tmp_path):
    env = Env(str(tmp_path), EnvName("EXAMPLE"), work_dir=tmp_path)

    monkeypatch.setattr(env, "visit", lambda: None)
    monkeypatch.setattr(env, "lock", lambda: None)
    monkeypatch.setattr(env, "load_object", lambda file_name: None)
    monkeypatch.setattr(features, "_ENABLED", frozenset({"OLD_FEATURE"}))

    env.enter()

    assert not features.get("OLD_FEATURE")
