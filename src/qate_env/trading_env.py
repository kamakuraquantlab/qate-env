import importlib
from typing import Type

from qate.trading.config import StrategyConfig
from qate.trading.strategy import Strategy

CONFIG_MODULE = "config"
CONFIG_CLASS = "Config"


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
