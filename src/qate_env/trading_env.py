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
    strategy_module_name: str | None = None
    variant: str = "v0"
    trading_config_key: str = "DEFAULT"
    reporter_config_key: str | None = None

    @property
    def strategy_name(self):
        return f"{self.strategy_module_name}.{self.variant}"


@dataclass
class TradingEnv:
    profile: TradingProfile
    config: StrategyConfig
    params: dict = field(default_factory=dict)
    param_grid: list | None = None
    features: dict | None = None


def resolve_config_class(strategy_module_name: str) -> Type[StrategyConfig]:
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
    module = importlib.import_module(module_name + "." + variant_name)
    return module.Variant


def load_trading_env(env: Env) -> TradingEnv:
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
