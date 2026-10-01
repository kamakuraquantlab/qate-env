"""What an environment says about a run, loaded from its files.

The classes an environment's JSON deserializes into, and the one function that
reads the lot. `Env` is the directory; this is what is written in it.

The strategy's own `Config` class is the one thing that cannot be known in
advance, and it is resolved from the strategy module rather than named in an
index -- see `resolve_config_class`.
"""

import importlib
from dataclasses import dataclass, field
from logging import getLogger
from typing import Type

from qate.trading.config import StrategyConfig
from qate.trading.strategy import Strategy

from .env import Env

LOG = getLogger(__name__)

CONFIG_MODULE = "config"
CONFIG_CLASS = "Config"

CONFIG_FILE = "config.json"
TRADING_FILE = "trading.json"
PARAMS_FILE = "params.json"
PARAM_GRID_FILE = "param_grid.json"
FEATURES_FILE = "features.json"


@dataclass
class TradingProfile:
    """Which strategy an environment runs, and under which credentials.

    Deliberately not which *gateway*. That is a property of the process doing the
    running -- a live runner trades, a backtest simulates -- not of the environment,
    and a field that half the readers ignored was a field that went stale: a
    collector env claiming SIMULATOR, a backtest env claiming anything at all.
    `Configurator` takes it as an argument instead.
    """

    strategy_module_name: str | None = None
    variant: str = "v0"
    trading_config_key: str = "DEFAULT"
    reporter_config_key: str | None = None
    """Which credentials a `Reporter` should be built from, if any.

    Named after `Reporter`, not after Discord or chat. The field was
    `chat_config_key` when the only destination was a chat bot; the destination is
    now whatever the runner decides to add, and a name that says "chat" would send
    every reader looking for a chat interface that no longer exists.
    """

    @property
    def strategy_name(self):
        return f"{self.strategy_module_name}.{self.variant}"


@dataclass
class TradingEnv:
    """Everything an environment says about a run, loaded.

    Loaded by convention rather than through `desc.json`'s module map. The map
    named a class per file, which bought nothing -- every reader already knows it
    wants a `TradingProfile` and a dict -- and cost a file that goes stale when
    code moves. The one genuinely unknown class, the strategy's `Config`, is
    resolved from the strategy module, which `trading.json` already names.
    """

    profile: TradingProfile
    config: StrategyConfig
    params: dict = field(default_factory=dict)
    param_grid: list | None = None
    features: dict | None = None


def resolve_config_class(strategy_module_name: str) -> Type[StrategyConfig]:
    """A strategy's `Config`, by the convention every strategy already follows.

    `<strategy_module>.config.Config`, which is what qate's
    `knowledge/03_writing_strategy.md` documents and what an environment's
    `config.json` deserializes into.
    """
    module_name = f"{strategy_module_name}.{CONFIG_MODULE}"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        raise RuntimeError(
            f"Cannot load {module_name}. A strategy package needs a `config` module "
            f"holding a `Config` class; see qate's knowledge/03_writing_strategy.md."
        ) from e
    if not hasattr(module, CONFIG_CLASS):
        raise RuntimeError(f"{module_name} has no {CONFIG_CLASS} class")
    return getattr(module, CONFIG_CLASS)


def get_strategy_class(module_name: str, variant_name: str) -> Type[Strategy]:
    """A strategy's `Variant`, by the same convention `resolve_config_class` uses.

    One class per variant file, named `Variant`. Both halves of a strategy are
    found by name rather than registered, which is what lets `trading.json` name a
    strategy this package has never heard of.
    """
    module = importlib.import_module(module_name + "." + variant_name)
    return module.Variant


def load_trading_env(env: Env) -> TradingEnv:
    """Read an environment's configuration files. Nothing is entered or locked."""
    profile: TradingProfile = env.load_object(TRADING_FILE, TradingProfile)
    if profile is None:
        raise RuntimeError(f"No {TRADING_FILE} in {env.work_dir}")
    if not profile.strategy_module_name:
        raise RuntimeError(f"{TRADING_FILE} in {env.work_dir} names no strategy_module_name")

    config = env.load_object(CONFIG_FILE, resolve_config_class(profile.strategy_module_name))
    if config is None:
        raise RuntimeError(f"No {CONFIG_FILE} in {env.work_dir}")

    return TradingEnv(
        profile=profile,
        config=config,
        params=env.load_object(PARAMS_FILE) or {},
        param_grid=env.load_object(PARAM_GRID_FILE),
        features=env.load_object(FEATURES_FILE),
    )
