"""Trading environments: a named directory holding one run's configuration.

The half of a deployment that `qate` deliberately does not have. `qate` is a
library -- events, orders, strategies, a simulator -- and knows nothing about
where a run is defined, which machine it is on, or whose credentials it uses.
This package is all four of those answers, in one place, so that no other module
carries a path.

| Module | Holds |
|---|---|
| `env` | `Env`: the directory and its lifecycle -- load, chdir, lock, log |
| `env_name` | `EnvName`: a validated uppercase name |
| `sys_env` | The machine: where environments live, and which credentials exist |
| `trading_env` | The classes an environment's JSON loads into, and the loader |
| `configurator` | An environment's markets and venues, wired into a `Runtime` |
| `run_log` | What a run recorded about itself: provenance for a number |

It depends on `qate` and, like `qate`, brings no HTTP or WebSocket client: the
venues it wires come from whatever adapter package is installed.
"""
