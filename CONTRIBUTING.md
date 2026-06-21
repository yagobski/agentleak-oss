# Contributing to AgentLeak OSS

Thanks for helping make agents safer. AgentLeak OSS is intentionally small and
dependency-light — keep contributions in that spirit.

> **Working on this with an AI agent?** Read [AGENTS.md](AGENTS.md) first — it's
> the architecture map, the invariants, and the "how to extend" guide.

## Setup (Python)

```bash
pip install -e ".[dev]"
pytest                       # run the tests
ruff check agentleak/        # lint
mypy agentleak/              # type-check
```

## Setup (web GUI)

The GUI is a React + Vite + Tailwind + shadcn/ui app in
`agentleak/web/frontend/`. The **built** bundle is committed to
`agentleak/web/static/` and shipped in the wheel, so end users never need Node.

```bash
cd agentleak/web/frontend
npm install
npm run dev          # Vite dev server; proxies /api → http://127.0.0.1:8000
                     # In another terminal: `agentleak serve`
npm run build        # type-check + build into ../static
```

After changing the frontend, run `npm run build` and commit the updated
`agentleak/web/static/` so the change ships. Then `pip install .` to refresh the
installed bundle and restart `agentleak serve`.

## Guidelines

- **No network, no LLM in the core.** Detection must stay local, deterministic,
  and explainable (regex + dictionaries). LLM-based detection, if ever added,
  belongs behind an optional extra — never a required dependency.
- **Privacy first.** Never log or persist raw sensitive values. Reports show
  redacted values by default.
- **Type everything.** New code should pass `mypy` and `ruff`.
- **Test what you add.** Keep coverage at or above 70%. Detectors need both
  positive cases and false-positive guards.

## Adding a detector

1. Subclass `agentleak.core.detector.Detector`, set `name`, implement `detect`.
2. Return `RawMatch` objects with a `data_type`, `severity`, `confidence`, and a
   `recommendation`.
3. Register it in `agentleak/detectors/__init__.py` if it's a built-in toggle.
4. Add tests in `tests/test_detectors.py` (detection **and** a clean-text guard).

## Adding a scenario

1. Define a `Scenario` under `agentleak/scenarios/`.
2. Bundle a **synthetic** trace under `agentleak/examples/`.
3. Add it to the registry and to `tests/test_scenarios.py`.

## Pull requests

Run the full check suite before opening a PR. Describe the leak class or channel
your change covers, and include a before/after of the score where relevant.
