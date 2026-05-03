# 34 — Inventory & Status: Code vs Documentation

> Honest snapshot of what exists in the codebase today versus what the new
> documentation requires.
>
> Last reviewed: 2026-05-03 (after PR 3 — `feat/repo-hooks-and-audit`).
> Owner: keep updated each release; refresh on every wave close.

## Legend

- **DONE** — implemented and covered by tests
- **PARTIAL** — exists but incomplete or untested
- **STUB** — model/table exists, behavior not implemented
- **MISSING** — not present in the codebase

## Backend framework (`orbiteus_core/`)

| Concern | Status | Path | Gap vs docs |
|---|---|---|---|
| Module Registry + topo sort | DONE | `registry.py` | — |
| BaseRepository (tenant filter, RBAC, soft delete, hooks, audit, attribution) | DONE | `repository.py` | extended in PR 3 |
| AutoRouter (5 CRUD endpoints) | DONE | `auto_router.py` | — |
| ui-config builder | DONE | `ui_config.py` | needs `relation` for many2one |
| RBAC: `ir_model_access` + `ir_rule` cache | PARTIAL | `security/rbac.py` | in-memory dict; needs Redis (ADR-0003) |
| JWT + bcrypt | DONE | `security/{tokens,passwords}.py` | TTL 60min; needs 15min + jti revocation |
| TOTP 2FA | DONE | `security/tokens.py` | recovery codes MISSING |
| AI Action Registry + RapidFuzz | DONE | `ai/{action,registry,resolver,router}.py` | — |
| **Audit log (`ir_audit_log`)** | DONE | `modules/base/model/{domain,mapping}.py`, migration `a1f3c0e1b002` | mandatory; opt-out via `AUDIT_OPTOUT_MODELS` |
| **EventBus (in-process)** | DONE | `orbiteus_core/events.py` | sync error isolation, decorator subscribe |
| **Postgres Outbox (`ir_outbox`)** | MISSING | — | PR 4 |
| **Repository hooks (before/after)** | DONE | `BaseRepository._before_/_after_*` + EventBus | tests in `tests/test_eventbus.py` |
| **created_by / modified_by columns** | DONE | `make_base_columns`, `BaseModel` | populated in `BaseRepository.create/update/delete` |
| **FK resolution `{field}__name`** | MISSING | — | needed for CRM-MVP |
| **Sequences `next_val()`** | STUB | `IrSequence` row only | core wave 2 |
| **Attachments upload/download** | STUB | `IrAttachment` row only | core wave 3 |
| **Mail/SMTP send** | STUB | `IrMailTemplate` row only | core wave 3 |
| **Activities/chatter** | MISSING | — | core wave 3 |
| **Workflow engine (generic)** | MISSING | CRM-specific via Temporal | core wave 3 |
| **Computed fields** | MISSING | — | core wave 3 |
| **Onchange engine** | MISSING | — | core wave 3 |
| **Aggregate endpoint** | MISSING | — | needed for AI dashboard |
| **CSV import/export** | MISSING | — | core wave 3 |
| **Server actions / cron exec** | STUB | `IrCron` + Temporal stub | replace with Celery Beat |
| **Cache abstraction (Redis)** | PARTIAL | `redis-py` dep + `REDIS_URL` env wired in compose | abstraction lib in PR 6 |
| **Realtime (SSE) + Pub/Sub backplane** | MISSING | — | PR 7 |
| **PgBouncer integration** | DONE (compose) | `docker-compose.prod.yml`, transaction mode | runtime test in PR 7 |
| **Gunicorn + UvicornWorker entrypoint** | DONE | `backend/entrypoint.sh`, `Dockerfile.prod` | — |
| **Migrate one-shot service** | DONE | `entrypoint-migrate.sh`, prod compose `migrate` service | — |
| **Celery 5 + Beat** | STUB | placeholder services in prod compose | real impl in PR 5 |
| **Health endpoints** | DONE | `orbiteus_core/health.py` (`/api/health/{live,ready}`) | — |
| **Prometheus `/metrics`** | DONE | `orbiteus_core/observability/metrics.py` | series expanded in PR 13 |
| **JSON logging + request_id** | DONE | `orbiteus_core/observability/{logging,middleware}.py` | tenant_id/user_id ctx wired in PR 6 |
| **Alembic advisory lock helper** | DONE | `orbiteus_core/alembic_lock.py` | applied in next migration |
| **AI providers (Anthropic/OpenAI/Ollama)** | MISSING | only Action resolver | core wave 4 |
| **`ir_ai_credential` (BYOK)** | MISSING | — | core wave 4 |
| **`AIModuleConfig` registry + `ai.py`** | MISSING | — | core wave 4 |
| **pgvector + `ir_embedding`** | MISSING | — | core wave 4 |
| **`/api/ai/chat`, `/dashboard`** | MISSING | — | core wave 4 |
| **Field-level RBAC** | MISSING | — | post-v1.0 |
| **Multi-company switch endpoint** | MISSING | — | post-v1.0 |
| **PDF reports** | MISSING | — | post-v1.0 |
| **Currency conversion** | MISSING | move to `modules/finance` |
| **Temporal (worker.py)** | STUB | empty `WORKFLOWS` | replace with Celery |

## Modules (`backend/modules/`)

| Module | Status | Notes |
|---|---|---|
| `base` | DONE (basic) | Users, Companies, Partners, ir_*; needs `ir_audit_log`, `ir_outbox`, `ir_embedding`, `ir_ai_credential` |
| `auth` | DONE (basic) | login/refresh/2FA; missing share-link issuance, 15min/jti |
| `crm` | PARTIAL | Customer/Opportunity/Pipeline/Stage; **rename pending** to Person/Lead/Stage/Team (ADR-0008) |
| `hr`, `project`, `social` | NOT STARTED | docs/spec.md only; mark as `Layer: PRODUCT (sample)` post-v1.0 |

## Admin UI (`admin-ui/`)

| Concern | Status | Path | Gap vs docs |
|---|---|---|---|
| Mantine 8, Next.js 14 setup | DONE | — | — |
| AppShellLayout + sidebar | DONE | `components/AppShellLayout.tsx` | i18n cleanup needed |
| Login + JWT flow | DONE | `app/login/page.tsx` | will split into `/welcome` + `/login` |
| Welcome landing | DONE (under `/login`) | same | move to `/welcome`, `/login` becomes form-only |
| Dynamic catch-all routes | DONE | `app/[module]/[model]/...` | — |
| ResourceList | DONE | `components/ResourceList.tsx` | column widget rendering MISSING |
| ResourceForm | DONE | `components/ResourceForm.tsx` | many2one resolution MISSING |
| ResourceKanban | DONE | `components/ResourceKanban.tsx` | card enhancement MISSING |
| ResourceCalendar | PARTIAL | `components/ResourceCalendar.tsx` | not wired to view types yet |
| ResourceGraph | PARTIAL | `components/ResourceGraph.tsx` | needs aggregate endpoint |
| Command Palette ⌘K | DONE | `components/CommandPalette.tsx` | — |
| Branding | DONE | `lib/branding.tsx` | — |
| **Hardcoded CRM/base/technical pages** | TO DELETE | `app/{crm,base,technical}/*` | violates "zero TSX per module" |
| **Many2one widget** | PARTIAL | `widgets/Many2OneField.tsx` | needs FK resolution from API |
| **Badge widget** | PARTIAL | `widgets/StatusBadge.tsx` | not wired to lists |
| **Monetary widget** | MISSING | — | core CRM-MVP |
| **Statusbar widget** | PARTIAL | `widgets/StatusbarField.tsx` | not wired to lead.stage |
| **`packages/ui` workspace** | MISSING | flat `admin-ui/` only | core wave 5 |
| **`<PromptInput>`** | MISSING | — | core wave 5 |
| **`<AIChatPanel>`** | MISSING | — | core wave 5 |
| **`<AIDashboard>`** | MISSING | — | core wave 5 |
| **Toasts (success/error/403/404)** | PARTIAL | scattered | unify in `lib/api.ts` |
| **Empty states + loading skeletons** | MISSING | — | polish phase |
| **Polish strings** | LEAK | several files | EN-only cleanup |
| **Vitest setup** | DONE (basic) | one test | needs RTL setup + coverage |
| **Playwright E2E** | MISSING | — | post-v1.0 acceptable |

## Portal UI (`portal-ui/`)

Status: **MISSING (not scaffolded)**. Wave 6.

## Infrastructure

| Concern | Status | Path | Gap |
|---|---|---|---|
| Dockerfile (backend dev) | DONE | `backend/Dockerfile` | — |
| Dockerfile (backend prod) | DONE | `backend/Dockerfile.prod` | needs Gunicorn |
| Dockerfile (admin-ui prod) | DONE | `admin-ui/Dockerfile.prod` | — |
| docker-compose.yml | DONE (dev only) | — | needs profiles + `migrate` + `worker` + `redis` |
| docker-compose.demo.yml | DONE | — | one-off; will be regenerated |
| docker-compose.prod.yml | MISSING | — | core wave 2 |
| nginx vhost (demo) | DONE | `deploy/demo/nginx-*.conf` | needs `proxy_buffering off` for SSE |
| Alembic migrations | DONE | `backend/migrations/` | initial only; future ones expected |
| Redis service in compose | MISSING | — | core wave 2 |
| PgBouncer service | MISSING | — | core wave 2 |
| Celery worker service | MISSING | — | core wave 2 |
| pgvector image | MISSING | uses plain `postgres:16-alpine` | core wave 4 |

## Tests

| Suite | Files | Coverage |
|---|---|---|
| Backend smoke (auth, CRM, RBAC, registry, ui-config) | 9 | ≈ 30 tests, real Postgres |
| Frontend unit | 1 (`viewParser.test.ts`) | low |
| Docs | `tests/test_docs.py` | 12 tests, green |
| Observability | `tests/test_observability.py` | 6 tests, green |
| Compose | `tests/test_compose.py` | 9 tests, green |
| Dockerfile prod | `tests/test_dockerfile_prod.py` | 6 tests, green |
| E2E | none | needed before v1.0 |

## Summary score against documentation

| Layer | Coverage of "to-be" docs |
|---|---|
| `orbiteus_core` framework | ~55% (PR 2: health, metrics, JSON logs, alembic lock done) |
| `modules/base` | ~60% (system tables, no audit/outbox/embed/credential) |
| `modules/auth` | ~70% |
| `modules/crm` | ~50% (rename pending) |
| Admin UI | ~55% (renderer works, AI + widgets missing) |
| Portal UI | 0% |
| Infrastructure | ~75% (dev + prod compose, PgBouncer, Redis, Gunicorn, migrate service) |
| Observability / rate limit / backups / GDPR | ~20% (logs + metrics + health done; rate limit + backups + GDPR pending) |

## What "core 100% closed" means

See `35-core-definition-of-done.md`.
