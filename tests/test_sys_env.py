"""Machine settings: the resolution order, and the failure.

Both halves matter to a deployment. The order is what lets a checkout keep its
environments beside itself instead of in `$HOME`, and the failure is what stops a
live run starting without the credential it needs -- an unauthenticated fallback
would place an order and be refused by the venue instead, which is a worse place to
find out.
"""

import pytest

from qate_env import sys_env
from qate_env.sys_env import CredentialsNotFound

KEYS = """
[DEFAULT]
API_KEY = default-key
SECRET = default-secret

[OTHER]
API_KEY = other-key
SECRET = other-secret
"""


@pytest.fixture
def secret_dir(tmp_path, monkeypatch):
    path = tmp_path / "secrets"
    path.mkdir()
    monkeypatch.setenv(sys_env.SECRET_DIR_VAR, str(path))
    # `.qate.json` beside the running script wins over the variable, and under
    # pytest that script is pytest's own. Point it at a directory with no such file.
    monkeypatch.setattr(sys_env.sys, "argv", [str(tmp_path / "runner.py")])
    return path


def test_the_env_var_overrides_the_default_root(tmp_path, monkeypatch):
    monkeypatch.setattr(sys_env.sys, "argv", [str(tmp_path / "runner.py")])
    monkeypatch.setenv(sys_env.ENV_ROOT_VAR, "~/somewhere/else")
    assert sys_env.get_env_root_dir() == (tmp_path.home() / "somewhere/else")


def test_a_script_config_beats_the_env_var(tmp_path, monkeypatch):
    """`.qate.json` beside the script is how one host runs two checkouts."""
    script_dir = tmp_path / "checkout"
    script_dir.mkdir()
    (script_dir / sys_env.CONFIG_FILE_NAME).write_text('{"env_root_dir": "/srv/envs"}')
    monkeypatch.setattr(sys_env.sys, "argv", [str(script_dir / "runner.py")])
    monkeypatch.setenv(sys_env.ENV_ROOT_VAR, "/ignored")

    assert str(sys_env.get_env_root_dir()) == "/srv/envs"


def test_api_keys_come_from_the_named_section(secret_dir):
    (secret_dir / "gmo.keys").write_text(KEYS)

    assert sys_env.get_api_keys("GMO") == ("default-key", "default-secret")
    assert sys_env.get_api_keys("GMO", "OTHER") == ("other-key", "other-secret")


def test_a_missing_file_names_the_path_it_looked_for(secret_dir):
    """The whole point of the exception: a path to go and look at."""
    with pytest.raises(CredentialsNotFound, match=str(secret_dir / "gmo.keys")):
        sys_env.get_api_keys("GMO")


def test_a_missing_section_is_refused_rather_than_defaulted(secret_dir):
    """configparser's DEFAULT section makes every section look present. It is not."""
    (secret_dir / "gmo.keys").write_text("[OTHER]\nAPI_KEY = k\nSECRET = s\n")

    with pytest.raises(CredentialsNotFound):
        sys_env.get_api_keys("GMO", "MISSING")


def test_a_section_missing_a_field_is_refused(secret_dir):
    """Half a credential fails here, not at the venue."""
    (secret_dir / "gmo.keys").write_text("[DEFAULT]\nAPI_KEY = k\n")

    with pytest.raises(CredentialsNotFound):
        sys_env.get_api_keys("GMO")
