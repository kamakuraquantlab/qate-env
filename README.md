# qate-env

Environment directories and gateway construction for
[qate](https://github.com/kamakuraquantlab/qate): which machine a run is on,
whose credentials a live gateway uses, and what a run recorded about itself.

`qate` is a library. It knows what an order book is, how a strategy is called, and
how an order is filled — and nothing at all about directories, hosts or keys. That
is this package. Keeping them apart is what lets `qate` be installed and
backtested with no notion of a deployment, and what makes "a backtest asks for no
credential" true by construction rather than by review.

```bash
pip install kamakuraquantlab-qate-env
```

## An environment is a directory

One directory per named environment, under `~/env` by default. The application
owns the files inside it. For example, K2 owns `k2.json` and its strategy files;
Enoshima owns `enoshima.json` and its strategy parameter grid.

```
~/env/MY_LIVE_RUN/
  strategy_config.json
  features.json        # optional list of enabled feature names
  k2.json or enoshima.json
  ...                # other application-owned files
  .lock              # PID lock: one process per environment
  env.log            # rotating log
```

There is no universal trading-environment schema here. Each application loads
its own definition. The shared convention is only how a strategy class is found:
`Config` from `<module>.config` and `Variant` from `<module>.<variant>`.

`features.json` is an optional JSON array. Every name present is enabled for the
life of the process; absent names are disabled:

```json
["USE_GMO_ASYNC"]
```

```python
from qate_env import sys_env
from qate_env.env import Env
from qate_env.env_name import EnvName
from qate_env.trading_env import get_strategy_class, resolve_config_class

env = Env(sys_env.get_env_root_dir(), EnvName("MY_LIVE_RUN"))
env.enter()                                   # chdir, log to env.log, take the lock

ConfigClass = resolve_config_class("my_strategy")
StrategyClass = get_strategy_class("my_strategy", "v1")
# The application loads its JSON into ConfigClass and supplies its own params.
```

## Layout

| Module | Holds |
|---|---|
| `qate_env.env` | `Env`: the directory and its lifecycle — load, chdir, lock, log |
| `qate_env.env_name` | `EnvName`: a validated uppercase name, and a real `str` |
| `qate_env.sys_env` | The machine: where environments live, which credentials exist |
| `qate_env.trading_env` | The two by-convention strategy class lookups |
| `qate_env.configurator` | A strategy config's markets and venues, wired into a qate runtime |
| `qate_env.run_log` | `RunLog`: what a run recorded about itself |

## Wiring a live run

`Configurator` turns a configuration into objects that can connect, by asking
`qate`'s registry for whatever adapter is installed. It names no venue itself.

```python
from qate.trading.runtime import Runtime
from qate_env.configurator import Configurator, GatewayConfig, GatewayMode

runtime = Runtime(strategy)
gateway = GatewayConfig(GatewayMode.PROD, config_key="DEFAULT")
Configurator(config, gateway).configure(runtime)
runtime.start()
```

`GatewayConfig` is constructed by the runner. qate-env does not know which
application file supplied its mode or credential key. `PROD` requires a key;
`SIMULATOR` builds simulated execution; `NONE` configures market data without an
execution gateway. The latter two forbid a credential key.

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
| [Enoshima](https://github.com/kamakuraquantlab/Enoshima) | Uses the directory lifecycle and class-resolution convention |
| A live runner | Builds a `GatewayConfig`, resolves credentials, and trades |

`qate` itself does not, and that is the point of the split.

## Development

```bash
pip install -e '.[dev]'
pytest
```

## Licence

Apache 2.0. See [LICENSE.md](LICENSE.md).
