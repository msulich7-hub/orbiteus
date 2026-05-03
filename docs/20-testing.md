# 20 — Testing

## Pyramid

```
           E2E (Playwright)         <- ~20 scenarios, smoke + critical paths
        Integration (pytest, real Postgres + Redis)   <- per module + cross-cutting
   Unit (pytest, Vitest)                              <- pure logic, no I/O
```

## Backend

- Framework: pytest + pytest-asyncio.
- Database: real PostgreSQL 16 (no SQLite for integration). Use the
  `docker-compose.test.yml` (or the test profile) to spin up a dedicated DB.
- Redis: real Redis 7.
- Fixtures (in `backend/tests/conftest.py`):
  - `db` — clean schema per session, advisory-locked.
  - `client` — `httpx.AsyncClient` against the running app.
  - `tenant`, `user`, `superadmin` — factory fixtures producing isolated rows.
  - `redis` — flushed at session start.

Coverage budgets:

- `orbiteus_core/`: ≥ 90%.
- `modules/base/`, `modules/auth/`: ≥ 85%.
- Canonical CRM: ≥ 80%.
- Other sample modules: ≥ 70%.

## Frontend

- Unit: Vitest + happy-dom.
- Component: Vitest + @testing-library/react.
- E2E: Playwright targeting the local prod build of admin-ui.

Component test must cover at least:

- Each registered widget renders for valid + invalid props.
- `ResourceList` paginates, sorts, filters via URL params.
- `ResourceForm` posts/puts the right payload shape.
- `<PromptInput>` falls back gracefully without an `ir_ai_credential`.

## E2E scenarios (critical path, must remain green)

- Login → create record → list → kanban move → form edit → delete.
- Welcome page renders without backend (graceful degradation).
- Realtime: two browsers see the same kanban move.
- AI: prompt input on a CRM lead returns an answer (mocked provider in CI).

## Snapshot testing

- `ui-config` golden file: snapshot saved per release tag; PR diff highlights
  unintended changes.
- Audit log row shape: snapshot for create/update/delete events.

## Performance smoke (lightweight)

- Locust scenario: 100 virtual users, 10 minutes, p95 < 300 ms on list endpoints.
- Run weekly in CI or before tagging a release.

## Documentation tests

- `scripts/check_docs.py` validates internal links, ADR cross-references, and
  the doc map in `pre-prompt.md`.
- Wrapped by `tests/test_docs.py` (pytest), runs on every CI build.

## Mocking policy

- **Never** mock the database in integration tests.
- **Never** mock `BaseRepository` in tests of code that uses it — use a real
  test DB with rolled-back transactions.
- AI provider calls are mocked via the `Provider` ABC's stub implementation
  in tests, except for nightly real-API smoke (env-gated).

## Conventions

- One test file per source file when sensible (`test_<source>.py`).
- Tests describe behavior, not implementation
  (`test_create_persists_record`, not `test_insert_calls_orm`).
- Async tests are the default; synchronous tests must justify the choice.
- Fixtures in `conftest.py`; no fixture imports between test files.

## Required green checks before merging

1. `pytest backend/tests/`
2. `vitest --run admin-ui/`
3. `python scripts/check_docs.py`
4. `npm run lint --workspace admin-ui`
5. `npm run build --workspace admin-ui`

CI runs all five on every PR (see `21-release-and-versioning.md`).
