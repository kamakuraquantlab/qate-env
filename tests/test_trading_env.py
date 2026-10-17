import sys

import pytest
from qate.trading.config import StrategyConfig
from qate.trading.strategy import Strategy

from qate_env.trading_env import get_strategy_class, resolve_config_class

STRATEGY_MODULE = "fake_strategy"


@pytest.fixture
def strategy_module(tmp_path, monkeypatch):
    package = tmp_path / STRATEGY_MODULE
    package.mkdir()
    (package / "__init__.py").write_text("")
    (package / "config.py").write_text(
        "from qate.trading.config import StrategyConfig\n"
        "class Config(StrategyConfig):\n    pass\n"
    )
    (package / "v1.py").write_text(
        "from qate.trading.strategy import Strategy\n"
        "class Variant(Strategy):\n    pass\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    yield STRATEGY_MODULE
    for name in list(sys.modules):
        if name == STRATEGY_MODULE or name.startswith(STRATEGY_MODULE + "."):
            del sys.modules[name]


def test_a_strategys_config_class_is_found_by_convention(strategy_module):
    cls = resolve_config_class(strategy_module)
    assert cls.__name__ == "Config"
    assert issubclass(cls, StrategyConfig)


def test_a_missing_config_module_says_what_a_strategy_needs():
    with pytest.raises(RuntimeError, match="config"):
        resolve_config_class("not_a_strategy_package")


def test_a_variant_is_found_by_convention(strategy_module):
    cls = get_strategy_class(strategy_module, "v1")
    assert cls.__name__ == "Variant"
    assert issubclass(cls, Strategy)
