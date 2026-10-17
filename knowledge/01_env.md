# Environment boundaries

`qate-env` owns the lifecycle of a named environment directory, machine-local
credential lookup, run provenance, and construction of exchange components. It
does not define one universal set of files inside an environment.

K2 and Enoshima have different jobs and therefore own different schemas. K2
loads `k2.json`, `strategy_config.json`, and `strategy_instance_*.json`.
Enoshima loads `enoshima.json`, `strategy_config.json`, and
`strategy_param_grid.json`. `Env.load_object` is the shared typed JSON reader.

## Strategy classes by convention

A strategy package contains `config.py` with `Config` and one module per variant
with a class named `Variant`. The two helpers in `qate_env.trading_env` resolve
those classes:

```python
from qate_env.trading_env import get_strategy_class, resolve_config_class

Config = resolve_config_class("my_strategy")
Variant = get_strategy_class("my_strategy", "v1")
```

The application decides which module and variant to pass and which JSON is
deserialized into `Config`. There is no registry or profile file in qate-env.

## Gateway construction

The runner makes the decision to connect or simulate:

```python
from qate_env.configurator import Configurator, GatewayConfig, GatewayMode

gateway_config = GatewayConfig(GatewayMode.PROD, config_key="DEFAULT")
Configurator(strategy_config, gateway_config).configure(runtime)
```

`PROD` requires a credential key. `SIMULATOR` builds simulated execution and
`NONE` builds no execution gateway; both require the key to be `None`.
`Configurator` reads markets and exchanges from `StrategyConfig`, asks qate's
registry for installed adapters, and attaches the resulting components to the
runtime. The application file from which `GatewayConfig` came is deliberately
unknown here.

## Directory lifecycle

`Env.visit()` changes to the environment directory and configures its rotating
log. `Env.enter()` additionally takes its process lock; `leave()` releases it.
Loaders that only inspect a definition may use `Env.load_object` without entering
the directory.

Credentials have no default. `sys_env.get_api_keys` either returns the named key
set or raises with the file it attempted to read. A simulator never asks for
credentials.
