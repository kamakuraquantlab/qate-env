# qate-env — Agent Entry Point

Trading environments for `qate`, part of Kamakura Quant Lab. Read
[README.md](README.md) first; this page holds the things that will cost you if you
miss them.

## What this package is for

`qate` is a library and must stay one: it knows events, orders, strategies and a
simulator, and knows nothing about directories, hosts or keys. Everything it would
have had to know lives here. The split is recent, and the question it answers for
every change is:

| Adding | Goes in | Not in |
|---|---|---|
| Anything that names a path, a host, or a credential | here | `qate` |
| A file an environment can contain | `trading_env.py` | |
| A way of turning configuration into live objects | `configurator.py` | |
| Anything a strategy's own code calls | `qate.trading` | here |
| A generic indicator, chart, gateway or risk rule | `qate` | here |
| A venue, or anything venue-specific | `qate-exchanges` | here |
| A way of reading recorded market data | the replayer (Enoshima) | here |

**`qate` must never import this package.** The dependency runs one way, and it is
what keeps a `pip install kamakuraquantlab-qate` free of any notion of a
deployment. A circular import would be the symptom; the real loss would be that
"a backtest asks for no credential" stops being checkable.

## The things that will cost you

- **No HTTP client and no WebSocket client may enter the dependency tree, at any
  depth.** Same rule as `qate`, and it matters more here: `Configurator` hands real
  credentials to a gateway, so this is the package where connectivity of its own
  would be worst. Venues arrive only through `qate`'s registry.
- **The settings names are frozen.** `QATE_ENV_ROOT`, `QATE_SECRET_DIR`, `.qate.json`,
  `~/.qate/<service>.keys`, `~/env`. They name the framework rather than this
  distribution, and every deployed host, daemon script and operator runbook already
  uses them. Renaming them to match the package would break hosts silently — a
  missing env var does not raise, it falls back to a default.
- **No credential may have a default.** `sys_env` raises `CredentialsNotFound`
  naming the file it looked for. It never falls back to an unauthenticated call.
- **`unlock()` must not raise.** Every caller runs it from a `finally`, usually
  while shutting down after something else went wrong, so an exception here
  replaces the interesting error with a complaint about a lock file. It logs.
- **`enter(daemon=True)` exits the process** the first time, after generating
  `start_*.sh` and `stop_*.sh` for the operator to read. That is deliberate and
  operators rely on it; it is not a startup failure.
- **A run log is given what it records, never asked for it.** `RunLog` used to read
  `env.get("config")`, which only returned anything after a particular load path
  had run — so a caller that loaded its config any other way silently logged
  `"config": null`. Pass it in.
- **`get_git_rev()` reads the directory `env.py` is in**, so a run log records
  *this* package's revision, not `qate`'s and not the strategy's. Logs written
  before the split record the revision of the one repository there was.
- **`GatewayName` is not a field in `trading.json`.** Whether a run reaches a venue
  is a property of the process doing the running, and it was an environment field
  once: collector envs claimed SIMULATOR, backtest envs claimed anything at all,
  and nothing kept any of it true. The runner passes it.
- **A strategy's two halves are found by name, not registered.** `Config` from
  `<module>.config.Config`, `Variant` from `<module>.<variant>.Variant`. There was
  an index (`desc.json`) and it went stale whenever code moved. Do not reintroduce
  one.
- **Fail fast.** Do not add runtime guards for logic bugs. Check only for dynamic
  errors: a missing file, a locked directory, a credential that is not there.

## Who depends on this

Enoshima (public) and the live runner (private) — and a change here reaches a host
on its next release, so prefer adding a field with a default over changing the
meaning of one. `dacite` ignores unknown fields in an environment's JSON, which
means a renamed field does not fail loudly: it loads as the default and the run
behaves differently. That has happened once already, with `chat_config_key` →
`reporter_config_key`.

## Before publishing

```bash
pytest
rm -rf dist && python3 -m build
cd dist && unzip -q *.whl && tar xzf *.tar.gz
grep -rniE 'AKIA|s3://|BEGIN [A-Z ]*PRIVATE KEY|/home/|api[_-]?key *=' .
cd .. && python3 -m twine check dist/*
python3 -m twine upload --config-file .pypirc dist/*
```

Scan the sdist as well as the wheel, which is what the `tar xzf` is for: `twine
upload dist/*` ships both, and the sdist carries `tests/` while the wheel does not.

`--config-file .pypirc` is not optional. `.pypirc` here holds this project's upload
token and nothing else's; twine ignores it without the flag and falls back to
`~/.pypirc`. It is gitignored, and it must stay that way -- this is a public
repository.

The scan is on the wheel, not the repository: what ships is the wheel. Add the
private names of whatever ecosystem this serves — repositories, strategies,
warehouse roots, production environment names — to the pattern; that list belongs
with the private code, not in a public file.

This package is the likeliest of the public ones to leak something, because
credentials and machine layout are its subject. The failure to look for is not a
key in the source. It is an example, a test fixture or a default that quietly
documents a real deployment: a real `EnvName`, a real secret path, a real host.
