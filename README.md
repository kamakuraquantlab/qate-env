# qate-env

Trading environments for [qate](https://github.com/kamakuraquantlab/qate): where a
run is defined, which machine it is on, whose credentials it uses, and what it
recorded about itself.

`qate` is a library. It knows what an order book is, how a strategy is called, and
how an order is filled — and nothing at all about directories, hosts or keys. That
is this package. Keeping them apart is what lets `qate` be installed and
backtested with no notion of a deployment, and what makes "a backtest asks for no
credential" true by construction rather than by review.

```bash
pip install kamakuraquantlab-qate-env
```

## An environment is a directory

One directory per named environment, under `~/env` by default:

```
~/env/MY_LIVE_RUN/
  trading.json       # which strategy module and variant, and which key set
  config.json        # the strategy's Config
  params.json        # the parameters this run uses
  param_grid.json    # a search space, for an optimize sweep. Optional
  features.json      # feature flags. Optional
  .lock              # PID lock: one process per environment
  env.log            # rotating log
```

There is no index file naming what loads what. Each `<key>.json` is read by
whatever wants it, and the one class that cannot be known in advance — the
strategy's own `Config` — is resolved from the strategy module that `trading.json`
already names. See [knowledge/01_env.md](knowledge/01_env.md) for why there used
to be one and why it went.

```python
from qate_env import sys_env
from qate_env.env import Env
from qate_env.env_name import EnvName
from qate_env.trading_env import get_strategy_class, load_trading_env

env = Env(sys_env.get_env_root_dir(), EnvName("MY_LIVE_RUN"))
env.enter()                                   # chdir, log to env.log, take the lock

definition = load_trading_env(env)            # profile, config, params, grid, features
StrategyClass = get_strategy_class(
    definition.profile.strategy_module_name,
    definition.profile.variant,
)
strategy = StrategyClass(definition.config, definition.params)
```

## Layout

| Module | Holds |
|---|---|
| `qate_env.env` | `Env`: the directory and its lifecycle — load, chdir, lock, log |
| `qate_env.env_name` | `EnvName`: a validated uppercase name, and a real `str` |
| `qate_env.sys_env` | The machine: where environments live, which credentials exist |
| `qate_env.trading_env` | `TradingProfile`, `TradingEnv`, `load_trading_env`, and the two by-convention class lookups |
| `qate_env.configurator` | An environment's markets and venues, wired into a `qate.trading.runtime.Runtime` |
| `qate_env.run_log` | `RunLog`: what a run recorded about itself |

## Wiring a live run

`Configurator` turns a configuration into objects that can connect, by asking
`qate`'s registry for whatever adapter is installed. It names no venue itself.

```python
from qate.trading.runtime import Runtime
from qate_env.configurator import Configurator, GatewayName

runtime = Runtime(strategy)
Configurator(config, profile, gateway_name=GatewayName.PROD).configure(runtime)
runtime.start()
```

`GatewayName` is the *runner's* decision, not the environment's — a live runner
passes `PROD`, a paper or replay runner leaves it at `SIMULATOR`. It is not a field
in `trading.json`, because a field half its readers ignored was a field that went
stale.

## Settings

Three answers about the machine, each from a config file, an environment variable,
or a documented default. No path is hardcoded anywhere else.

| What | Default | Overridden by |
|---|---|---|
| Where environments live | `~/env` | `QATE_ENV_ROOT`, then `env_root_dir` in a `.qate.json` beside the running script |
| Where credentials live | `~/.qate` | `QATE_SECRET_DIR`, then `secret_dir` in that same `.qate.json` |
| A credential | — | `<secret dir>/<service>.keys`, INI, one section per named key set |

```ini
[DEFAULT]
API_KEY = ...
SECRET  = ...
```

A missing file raises `CredentialsNotFound` naming the path it looked for. Nothing
here invents a credential or falls back to an unauthenticated call, so a live run
fails at startup rather than part way through — and a backtest, which asks for
none, is never affected by their absence.

The variables are still spelled `QATE_*` and the directory is still `~/.qate`:
they name the framework, not the distribution, and every deployed host already
has them.

There is deliberately no market-data root. Neither `qate` nor this package reads
market data; the tool that downloaded it knows where it is.

## What a run recorded

`RunLog` is the provenance of a number — the environment, the library revision,
the configuration, the parameters — written as one JSON file so a figure in a
notebook can be traced back to the run that produced it.

It is *given* what it records, never asked for it. It used to read
`env.get("config")`, which returned something only after a particular load path
had run, so a caller that loaded its configuration any other way silently logged
`"config": null`. The provenance of a number is a bad place for a silent null.

## Who uses this

| | |
|---|---|
| [Enoshima](https://github.com/kamakuraquantlab/Enoshima) | Backtests an environment's definition without taking its lock |
| A live runner | Reads the same environment, passes `GatewayName.PROD`, and trades it |

`qate` itself does not, and that is the point of the split.

## Development

```bash
pip install -e '.[dev]'
pytest
```

## Licence

Apache 2.0. See [LICENSE.md](LICENSE.md).
