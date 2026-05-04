# 36 — Development Plan (Step-by-Step to v1.0)

> Sequenced PR plan from current state (≈45% engine coverage) to v1.0 release.
> Each PR is independently reviewable, ships green tests, and updates the
> matching docs.

## Constraints

- No PR ships without tests and updated docs.
- No PR breaks `main` (CI gate).
- Each PR < 1500 lines diff where possible.
- Boring tech only; new deps require an ADR.

## Sequence

PRs are ordered by dependency. Skipping ahead breaks downstream PRs.

---

### PR 0 (DONE) — `feat/docs-foundation`

Documentation skeleton, `pre-prompt.md`, ADRs 0001–0016, validator + tests.
Already merged-ready on branch.

---

### PR 1 — `feat/inventory-and-plan` (this branch)

- `docs/34-inventory-and-status.md` (this snapshot)
- `docs/35-core-definition-of-done.md`
- `docs/36-development-plan.md`
- Update `docs/README.md`, `docs/pre-prompt.md` doc map to include 34/35/36.

**Tests:** docs validator + pytest still green.

**DoD:** new tracker visible, ADRs untouched.

---

### PR 2 — `chore/repo-hygiene-and-prod-stack`

Boring infrastructure foundation that everything else builds on.

Backend:

- Replace `entrypoint.sh` `uvicorn` with **Gunicorn + UvicornWorker** for prod
  (`Dockerfile.prod`).
- Extract migrations into a one-shot `migrate` service in compose.
- Add `pg_try_advisory_lock` at top of every Alembic upgrade (helper).
- Add `prometheus_client` and `/metrics` endpoint (auth-gated).
- Add `/api/health/live` and `/api/health/ready` endpoints.
- Add structured JSON logger with `request_id` middleware.

Compose:

- Split into `docker-compose.yml` (dev profile) and `docker-compose.prod.yml`.
- New services in prod: `pgbouncer`, `redis`, `migrate`, `worker` (placeholder),
  `nginx`.
- Switch `db` image to `pgvector/pgvector:pg16`.
- nginx vhost gets `proxy_buffering off` on `/api/realtime/` (forward-compatible).

Tests:

- `tests/test_compose.py` — parses both compose files and asserts service set.
- `backend/tests/test_health.py` extended for `/live` + `/ready` shape.
- `backend/tests/test_metrics.py` — `/metrics` returns Prometheus exposition.

ADRs touched: 0011, 0012.

**DoD:** `docker compose --file docker-compose.prod.yml --env-file .env.prod up
-d --build` brings up the new services on a fresh checkout.

---

### PR 3 — `feat/repo-hooks-and-audit`

Foundation for everything else (audit, embeddings, realtime emit).

Backend:

- Add `before_create / after_create / before_write / after_write /
  before_unlink / after_unlink` hooks in `BaseRepository`.
- Add `created_by_id`, `modified_by_id` columns in `BaseModel` + Alembic
  migration.
- Add `ir_audit_log` table + Pydantic schemas + repository.
- Wire mandatory audit hook (opt-out list per module).
- Add `/api/base/audit-log` paginated endpoint.

Tests:

- `test_hooks.py` — before/after order, data flow.
- `test_audit.py` — every CRUD writes a row, diff shape, redaction of
  `password_hash`.
- `test_audit_optout.py` — `ir_audit_log` itself is excluded from logging.

ADRs: cite 0010.

**DoD:** running CRM CRUD writes `ir_audit_log` rows; tests prove diff and
opt-out.

---

### PR 4 — `feat/eventbus-and-outbox`

Backend:

- `orbiteus_core/events.py` — in-process EventBus (async pub/sub).
- `ir_outbox` table + repository + Pydantic schemas.
- Outbox writes happen inside the same transaction as business writes
  (BaseRepository emits `record.created/updated/deleted` to the EventBus,
  one subscriber writes to `ir_outbox` if a webhook subscriber exists).
- `ir_webhook` table (tenant_id, url, secret, event_mask).

Tests:

- `test_eventbus.py` — subscribers fire in order, errors isolated.
- `test_outbox.py` — atomic with business commit; rollback drops the outbox row.

**DoD:** create + `ir_webhook` row → outbox row appears in same transaction.

---

### PR 5 — `feat/celery-worker`

Backend / infra:

- Add `celery==5.x` + `redis` deps in `pyproject.toml`.
- `backend/celery_app.py` with Redis broker + result backend.
- Outbox drainer Celery task (idempotent, exponential backoff).
- Webhook delivery Celery task with HMAC-SHA256 signature.
- Celery Beat reads `ir_cron` and schedules.
- Compose: `worker` and `beat` services (separate replicas).
- Replace any leftover `worker.py` Temporal stubs with Celery (see ADR-0015);
  update README accordingly.

Tests:

- `test_outbox_drainer.py` — pending → done; failing → retry → dead after 10.
- `test_celery_beat.py` — `ir_cron` row schedules a recurring task.

ADRs: 0013, 0015.

**DoD:** webhook delivered to a local mock receiver after `record.updated`;
dead-letter visible.

---

### PR 6 — `feat/redis-cache-and-rate-limit`

Backend:

- `orbiteus_core/cache.py` — Redis-backed cache abstraction.
- Move RBAC cache from in-memory to Redis (TTL 60s; invalidate on rule change
  via EventBus).
- `orbiteus_core/security/jti.py` — JWT `jti` revocation in Redis.
- Reduce access TTL to 15 min, refresh TTL to 7 days; refresh rotation.
- Middleware: token bucket rate limit (tenant + user + IP).
- Idempotency-Key middleware (Redis stored).
- Logout endpoint hits revocation list.

Tests:

- `test_cache.py` — get/set/expire, redis flush isolation.
- `test_rbac_redis.py` — multi-replica cache invalidation.
- `test_jti_revocation.py` — logout invalidates token.
- `test_rate_limit.py` — exceeds bucket → `429` + `Retry-After`.

ADRs: 0003.

**DoD:** logout demonstrably blocks the token before TTL.

---

### PR 7 — `feat/realtime-sse`

Backend:

- `/api/realtime/subscribe` SSE endpoint.
- Redis Pub/Sub backplane.
- BaseRepository `after_create / after_write / after_delete` publishes events
  on tenant-scoped topics.
- Topic RBAC validation on subscribe.

nginx:

- Confirm `proxy_buffering off` and SSE headers.

Tests:

- `test_realtime_sse.py` — single client receives event from a different
  worker process.
- `test_realtime_rbac.py` — cross-tenant topic returns `403`.

ADRs: 0006, 0014.

**DoD:** two integration tests prove cross-replica fan-out and RBAC.

---

### PR 8 — `feat/ai-layer-byok-and-providers`

Backend:

- `orbiteus_core/ai/providers/{base,anthropic,openai,ollama}.py`.
- `ir_ai_credential` table + Fernet encryption (`AI_SECRET_KEY`).
- `POST/GET/DELETE /api/ai/credentials` (with provider ping on POST).
- `AIModuleConfig` dataclass + `AIRegistry`; load from each module's `ai.py`.
- `orbiteus_core/ai/context.py` — `AIContextBuilder`.
- `orbiteus_core/ai/tools.py` — Action, QueryTool, semantic_search.
- `orbiteus_core/ai/budget.py` — Redis counters per tenant per month.
- `orbiteus_core/ai/redaction.py` — PII redaction before remote calls.
- `pgvector` extension + `ir_embedding` table + HNSW index.
- Embeddings refresh via Outbox-driven Celery task.
- `/api/ai/chat` streaming endpoint with provider tool calling.
- `/api/ai/dashboard` endpoint.

Tests:

- `test_ai_credentials.py` — Fernet roundtrip, provider ping mocked.
- `test_ai_tools.py` — Action and QueryTool exposed correctly per RBAC.
- `test_ai_audit.py` — every tool call writes `ir_audit_log` with `actor=ai`.
- `test_ai_budget.py` — exceeding budget returns `429 AI Budget Exceeded`.
- `test_pgvector.py` — index creation and similarity ranking.
- `test_ai_dashboard.py` — chart spec response well-formed against aggregate.

ADRs: 0004, 0005, 0009.

**DoD:** with a mock provider, asking `<PromptInput>` "summarize this lead"
returns text and writes audit + (optional) budget rows.

---

### PR 9 — `feat/canonical-crm-rename`

Backend:

- New tables: `crm_persons`, `crm_leads`, `crm_stages`, `crm_teams`.
- Migration: backfill from old tables; dual-write briefly.
- `crm/bootstrap.py` seeds default stages and one team per tenant.
- Remove `_seed_crm_defaults` from `api.py` lifespan.
- Demo `crm/ai.py` and `crm/actions.py` aligned with new models.
- `/api/base/aggregate` endpoint.

Tests:

- Per-model auto-CRUD for new models.
- Migration test (fixture old DB → run migration → assert new shape).
- `test_crm_ai_demo.py` — AI moves a lead's stage with audit.

ADRs: 0008.

**DoD:** demo CRM works on the new schema; old tables removed in next PR.

---

### PR 10 — `chore/admin-ui-cleanup-and-monorepo`

Frontend:

- Add npm workspaces (`admin-ui`, `portal-ui`); colocate shared widgets under `admin-ui/src/orbiteus-ui/`.
- Remove all hardcoded pages: `app/crm/*`, `app/base/*`, `app/technical/*`.
- Deprecate `Sidebar.tsx`.
- Translate remaining Polish strings to English.
- Toast unification in `lib/api.ts`.
- Empty states + loading skeletons.
- Split routes: `/welcome` (public), `/login` (form), `/` (dashboard).

Tests:

- Vitest + RTL setup.
- Component tests for ResourceList, ResourceForm, CommandPalette.

ADRs: 0016.

**DoD:** zero TSX page files outside catch-all routes; no Polish leaks.

---

### PR 11 — `feat/admin-ui-widgets-and-ai`

Frontend (in `admin-ui/src/orbiteus-ui/`):

- Widgets: many2one (resolved), badge (status colors), monetary (locale +
  currency), statusbar (steps), tags (TagsInput), date display, readonly.
- AI components: `<PromptInput>`, `<AIChatPanel>`, `<AIDashboard>`,
  `useAIContext()`.
- Calendar view wired to `crm.lead.expected_close_date`.
- Graph view backed by `/api/base/aggregate`.
- Kanban card enhancement (badge + monetary + avatar).

Tests:

- One Vitest test per widget.
- Storybook-style snapshot of representative views.

**DoD:** CRM-MVP fully renders without TSX; AI panel functional with mocked
provider.

---

### PR 12 — `feat/portal-ui`

- Scaffold `portal-ui/` Next.js 16 app.
- Share-link issuance + exchange (`POST /api/auth/share`, `/s/[token]`).
- Portal scope JWT enforcement middleware (`scope=portal`).
- `<portal>` view declaration parser.
- Comments + limited actions surface.
- Realtime SSE for portal-scoped resources only.

Tests:

- Playwright E2E: share link → portal opens → comment → admin sees realtime.
- Negative tests: cross-tenant + non-declared model.

ADRs: 0007.

**DoD:** external link viewer can comment on a CRM lead read-only.

---

### PR 13 — `feat/observability-and-rate-limit-polish`

- Prometheus exporters for backend, Celery, Redis, Postgres.
- Optional Grafana dashboards in `deploy/grafana/`.
- OpenTelemetry instrumentation auto-on when `OTEL_EXPORTER_OTLP_ENDPOINT` set.
- Rate limit polish: per-route overrides, monitoring counters.

Tests:

- `test_metrics_shape.py` — required series exposed.
- Smoke test of OTel exporter against a local collector image.

**DoD:** demo grafana dashboard visible in dev compose with `monitor` profile.

---

### PR 14 — `feat/backups-and-runbook`

- `backup` service in prod compose: `pg_dump` + WAL archive to S3-compatible.
- Restore drill scripts in `scripts/restore_drill.sh`.
- `docs/runbooks/` with concrete commands.

**DoD:** restore drill executed against a throwaway VPS; timing recorded in
the runbook.

---

### PR 15 — `chore/release-1.0`

- Update `docs/34-inventory-and-status.md` to all-DONE.
- Update CHANGELOG with v1.0 release notes (migration steps from 0.x).
- Bump versions in `pyproject.toml` and `package.json` to `1.0.0`.
- Update README.md with public messaging.
- Tag `v1.0.0`.

**DoD:** v1.0 published; demo updated.

---

## Timing estimate

Order-of-magnitude only; assumes one senior backend + one senior frontend.

| Phase | PRs | Effort |
|---|---|---|
| Foundations + audit + outbox | PR 2–4 | 1 week |
| Workers + cache + realtime | PR 5–7 | 1 week |
| AI layer | PR 8 | 1 week |
| CRM rename + admin polish | PR 9–11 | 1 week |
| Portal + observability | PR 12–13 | 1 week |
| Backups + release | PR 14–15 | 0.5 week |

**Total: ~5–6 weeks of focused work** to v1.0 from current state.

## Operating principles for this push

1. **No detours.** Anything not on this plan goes into `28-open-questions.md`.
2. **Tests block merges.** No "hotfix without test" — even one-line changes
   come with a regression test.
3. **Docs are part of the PR.** A change without a doc update is incomplete.
4. **Boring tech filter.** Any new dep must be in `pre-prompt.md` § 3 or come
   with an ADR.
5. **Demo follows main.** Each merged PR is rebuilt on the demo host
   automatically.
6. **One reviewer minimum**, two for framework-layer changes.

## Risk register (top 5)

1. **Migration failures from old CRM** — mitigation: dual-write window,
   tested rollback; PR 9 owns this.
2. **Realtime fan-out across replicas** — mitigation: integration test runs
   two backend processes (PR 7).
3. **Scaling AI cost** — mitigation: budget guard + visibility from day 1
   (PR 8).
4. **Audit volume** — mitigation: monthly partitioning + retention policy
   (PR 14 documents this; PR 3 sets it up).
5. **Frontend dynamic renderer regressions** — mitigation: ui-config
   snapshot + RTL tests (PR 11).
