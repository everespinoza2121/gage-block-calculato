# Gage Block Calculator

A small Flask tool for CNC machinists that recommends the closest practical
gage-block stack for a desired inch measurement.

**Release: v1.0.0**

## Start here

The calculator is a Flask application, not a standalone HTML page. From the
repository root, start it with:

```bash
python3 main.py
```

Keep that terminal running, then open **<http://127.0.0.1:5000/>**.

> **Important:** Do not use Website/Open on `templates/index.html` and do not
> open that file directly. A `file://` page cannot call the Flask API. Always
> use the `http://127.0.0.1:5000/` address printed by the running server.

The calculator models one of each of the 80 block sizes listed in `main.py`. It
searches stacks of up to five blocks and ranks results by:

1. smallest absolute deviation from the target;
2. fewest blocks; and
3. stable largest-first inventory order when a tie remains.

Measurements are calculated as integer microinches, so displayed totals and
deviations do not contain binary floating-point rounding artifacts.

## Supported input

- Range: `0.050000` through `1.000000` inches, inclusive
- Precision: up to six decimal places
- Result: exact match when available, otherwise the closest stack above or
  below the target

The inventory and five-block limit are a model, not a substitute for confirming
which calibrated blocks are physically available.

## First-time setup

Python 3.10 or newer is required. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

After setup, the normal launch workflow is always:

```bash
source .venv/bin/activate
python3 main.py
```

Then open **<http://127.0.0.1:5000/>**. Stop the server with `Ctrl+C` when
finished.

For a production-style local run, Gunicorn is also included:

```bash
gunicorn main:app
```

## Run tests

With the virtual environment active:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest
```

## API

`GET /gage-block?value=0.6453` returns formatted decimal strings so measurement
precision survives JSON transport:

```json
{
  "target": "0.645300",
  "blocks": ["0.400000", "0.145000", "0.100300"],
  "total": "0.645300",
  "deviation": "0.000000",
  "deviation_microinches": 0,
  "match_type": "exact",
  "block_count": 3
}
```

Invalid or out-of-range input returns HTTP `400` with an `error` message.

## Project structure

```text
main.py              Flask routes, validation, inventory, and calculation logic
templates/index.html Authoritative HTML/CSS/JavaScript interface
tests/test_main.py   Calculation and route tests
requirements.txt     Runtime dependencies
requirements-dev.txt Test dependencies
```
