"""An environment is read by convention, and the convention is the whole contract.

There is no index naming what loads what, so these tests are what stops the
convention drifting: a strategy's `Config` comes from `<module>.config.Config`, its
`Variant` from `<module>.<variant>.Variant`, and everything else from a file named
after itself. A rename here would otherwise break deployed environments quietly,
because `dacite` ignores a field it does not recognise rather than failing.
"""

import json
import sys
from pathlib import Path

import pytest
from qate.core.ev_type import EventType
from qate.core.model import ExchangeName, Market
from qate.core.symbol import Symbol
from qate.trading.config import StrategyConfig
from qate.trading.strategy import Strategy

from qate_env.env import Env
from qate_env.env_name import EnvName
from qate_env.trading_env import (
    TradingProfile,
    get_strategy_class,
    load_trading_env,
    resolve_config_class,
)

STRATEGY_MODULE = "fake_strategy"

CONFIG_PY = """
from dataclasses import dataclass

from qate.core.ev_type import EventType
from qate.core.model import ExchangeName, Market, Symbol
from qate.trading.config import StrategyConfig


@dataclass
class Config(StrategyConfig):
    order_size: float = 0.0

    def get_exchanges(self) -> list[ExchangeName]:
        return [ExchangeName.GMO]

    def get_markets(self) -> list[tuple[Market, list[str]]]:
        return [(Market(ExchangeName.GMO, Symbol.BTC_SPOT), [EventType.MARKET_ORDER_BOOK])]
"""

V1_PY = """
from qate.trading.strategy import Strategy


class Variant(Strategy):
    pass
"""


@pytest.fixture
def strategy_module(tmp_path, monkeypatch):
    """A strategy package on the path, laid out the way a real one is."""
    package = tmp_path / STRATEGY_MODULE
    package.mkdir()
    (package / "__init__.py").write_text("")
    (package / "config.py").write_text(CONFIG_PY)
    (package / "v1.py").write_text(V1_PY)
    monkeypatch.syspath_prepend(str(tmp_path))

    yield STRATEGY_MODULE

    for name in list(sys.modules):
        if name == STRATEGY_MODULE or name.startswith(STRATEGY_MODULE + "."):
            del sys.modules[name]


@pytest.fixture
def env(tmp_path):
    env = Env(str(tmp_path / "env_root"), EnvName("EXAMPLE_ENV"))
    env.setup()
    return env


def write_files(env: Env, **files):
    for name, content in files.items():
        (Path(env.work_dir) / name).write_text(json.dumps(content))


def write_trading(env: Env, strategy_module: str, variant: str = "v1"):
    env.save_object(
        "trading.json",
        TradingProfile(strategy_module_name=strategy_module, variant=variant),
    )


def test_a_strategys_config_class_is_found_by_convention(strategy_module):
    cls = resolve_config_class(strategy_module)
    assert cls.__name__ == "Config"
    assert issubclass(cls, StrategyConfig)


def test_a_missing_config_module_says_what_a_strategy_needs():
    """The error has to name the convention: there is no index to go and look at."""
    with pytest.raises(RuntimeError, match="config"):
        resolve_config_class("not_a_strategy_package")


def test_a_variant_is_found_by_convention(strategy_module):
    cls = get_strategy_class(strategy_module, "v1")
    assert cls.__name__ == "Variant"
    assert issubclass(cls, Strategy)


def test_an_environment_loads_into_the_classes_its_readers_expect(env, strategy_module):
    write_trading(env, strategy_module)
    write_files(
        env,
        **{
            "config.json": {"order_size": 0.01},
            "params.json": {"spread": 0.0005},
            "param_grid.json": [{"spread": [0.0005, 0.001]}],
        },
    )

    definition = load_trading_env(env)

    assert definition.profile.strategy_name == f"{strategy_module}.v1"
    assert definition.config.order_size == 0.01
    assert definition.config.get_markets() == [
        (Market(ExchangeName.GMO, Symbol.BTC_SPOT), [EventType.MARKET_ORDER_BOOK])
    ]
    assert definition.params == {"spread": 0.0005}
    assert definition.param_grid == [{"spread": [0.0005, 0.001]}]
    # Optional, and absent here: a missing file is None rather than an error.
    assert definition.features is None


def test_an_environment_with_no_params_still_loads(env, strategy_module):
    """`params.json` is optional and falls back to empty; the other two are not."""
    write_trading(env, strategy_module)
    write_files(env, **{"config.json": {"order_size": 0.01}})

    assert load_trading_env(env).params == {}


@pytest.mark.parametrize("missing", ["trading.json", "config.json"])
def test_the_two_required_files_fail_by_name(env, strategy_module, missing):
    """Named in the error, with the directory: the usual cause is the wrong env."""
    write_trading(env, strategy_module)
    write_files(env, **{"config.json": {"order_size": 0.01}})
    (Path(env.work_dir) / missing).unlink()

    with pytest.raises(RuntimeError, match=missing):
        load_trading_env(env)


def test_a_profile_naming_no_strategy_is_refused(env):
    """Empty `strategy_module_name` would otherwise fail later, importing `.v1`."""
    env.save_object("trading.json", TradingProfile())

    with pytest.raises(RuntimeError, match="strategy_module_name"):
        load_trading_env(env)


def test_an_unknown_field_in_trading_json_is_ignored(env, strategy_module):
    """Why a rename here is dangerous, held as a test rather than as a warning.

    `chat_config_key` was renamed to `reporter_config_key` once, and an un-renamed
    file loads exactly like this: no error, the default instead of the value, and a
    strategy trading with its notifications switched off.
    """
    write_files(
        env,
        **{
            "trading.json": {
                "strategy_module_name": strategy_module,
                "variant": "v1",
                "chat_config_key": "SOME_KEY",
            },
            "config.json": {"order_size": 0.01},
        },
    )

    assert load_trading_env(env).profile.reporter_config_key is None
