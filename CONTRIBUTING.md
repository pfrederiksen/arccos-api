# Contributing

Thanks for your interest in improving this library.

## Getting Started

```bash
git clone https://github.com/pfrederiksen/arccos-api.git
cd arccos-api
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest                       # runs with coverage (configured in pyproject.toml)
pytest -k "test_login"       # run specific tests
```

Coverage is enforced at 80% minimum. The HTML report is generated at `htmlcov/index.html`.

Tests are fully mocked — no real Arccos account needed.

## Adding a New Endpoint

1. Find the endpoint in `docs/openapi.yaml` (or add it if undocumented)
2. Add a method to the appropriate resource in `arccos/resources/`
3. Write a test in `tests/` using a mocked `HttpClient`
4. Update `README.md` if it's a significant new capability

## Documenting New Endpoints

When you discover a new Arccos endpoint:

1. Add it to `docs/openapi.yaml` following the existing pattern
2. Note whether it requires auth (`security: [BearerAuth: []]`)
3. Document known request/response fields — use `additionalProperties: true` for unknown fields
4. Add a comment if the endpoint behavior is surprising or undocumented

## Code Style

- `ruff check arccos/` must pass
- Docstrings on all public methods (Google style)
- Type hints on function signatures

## Reverse Engineering Notes

The Arccos Dashboard bundles are at:
- `https://dashboard.arccosgolf.com/main.*.bundle.js` (main app)
- `https://dashboard.arccosgolf.com/571.*.bundle.js` (vendor chunk)

Useful search patterns in the bundle:
- `AT({key:"..."}` — API call with a named endpoint key
- `buildUrl(` — dynamic URL construction
- `authentication.${l}` and `api.${l}` — base URL templates

The full endpoint config is a large object literal in the main bundle. Search for
`authenticate:!0` to find authenticated endpoints, or `method:"POST"` for mutating ones.
