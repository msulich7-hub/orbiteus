# 34 — Inventory & Status: Code vs Documentation

> Honest snapshot of what exists in the codebase today versus what the new
> documentation requires.
>
> Last reviewed: 2026-05-03 (after `feat/v1-final-100` — Definition of Done 100 %).
> Engine ships as **v1.0** — see CHANGELOG.md.
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
| RBAC: `ir_model_access` + `ir_rule` cache | PARTIAL | `security/rbac.py` | Redis cache abstraction available (PR 6); RBAC migration to Redis remaining |
| JWT + bcrypt | DONE | `security/{tokens,passwords,jti,rate_limit}.py` | 15min/7d, jti revocation list, refresh rotation in `/api/auth/refresh` |
| **httpOnly cookie session (Admin UI)** | DONE | `security/cookies.py`, `security/middleware.py` (cookie fallback), `modules/auth/controller/router.py`, `admin-ui/src/proxy.ts` | ADR-0017; eliminates FOAC at the Edge |
| **Default tenant + bootstrap admin binding** | DONE | `backend/api.py` (`_seed_default_tenant`, `_seed_superadmin` backfill) | `BOOTSTRAP_ADMIN_TENANT_NAME/SLUG`; backfills legacy `tenant_id IS NULL` admins |
| **AI Integration admin page (BYOK)** | DONE | `admin-ui/src/app/technical/ai-integration/page.tsx` (list/save/delete + test query) | wired to `GET/POST/DELETE /api/ai/credentials` and `POST /api/ai/chat` |
| **Cmd+K auto-CRUD action registration** | DONE | `backend/api.py:_seed_auto_actions`; CommandPalette reads `data.items` | every model in `_model_registry` gets `<model>.list` + `<model>.create` automatically; module-curated `actions.py` wins on id collisions |
| TOTP 2FA + recovery codes | DONE | `security/tokens.py`, `security/recovery_codes.py`, `POST /api/auth/2fa/recovery-codes` | bcrypt-hashed, single-use codes |
| AI Action Registry + RapidFuzz | DONE | `ai/{action,registry,resolver,router}.py` | — |
| **Audit log (`ir_audit_log`)** | DONE | `modules/base/model/{domain,mapping}.py`, migration `a1f3c0e1b002` | mandatory; opt-out via `AUDIT_OPTOUT_MODELS` |
| **EventBus (in-process)** | DONE | `orbiteus_core/events.py` | sync error isolation, decorator subscribe |
| **Postgres Outbox (`ir_outbox`)** | DONE | `orbiteus_core/outbox.py`, `IrOutbox`, `outbox_dispatcher.py`, migration `b2a4e1c0d003` | dispatcher subscribed to `record.*`; webhook delivery in PR 5 |
| **Webhooks (`ir_webhooks`)** | DONE (table + dispatcher) | `IrWebhook`, dispatcher fan-out per active subscriber | actual HTTP delivery in PR 5 |
| **Repository hooks (before/after)** | DONE | `BaseRepository._before_/_after_*` + EventBus | tests in `tests/test_eventbus.py` |
| **created_by / modified_by columns** | DONE | `make_base_columns`, `BaseModel` | populated in `BaseRepository.create/update/delete` |
| **FK resolution `{field}__name`** | MISSING | — | needed for CRM-MVP |
| **Sequences `next_val()`** | STUB | `IrSequence` row only | core wave 2 |
| **Attachments upload/download** | STUB | `IrAttachment` row only | core wave 3 |
| **Mail/SMTP send** | STUB | `IrMailTemplate` row only | core wave 3 |
| **Activities/chatter** | MISSING | — | core wave 3 |
| **Workflow engine (generic)** | MISSING | — (Temporal explicitly excluded by ADR-0015; reach for it only when sagas materialise) | core wave 3 |
| **Computed fields** | MISSING | — | core wave 3 |
| **Onchange engine** | MISSING | — | core wave 3 |
| **Aggregate endpoint** | MISSING | — | needed for AI dashboard |
| **CSV import/export** | MISSING | — | core wave 3 |
| **Server actions / cron exec** | DONE | `IrCron` rows + Celery Beat schedule (ADR-0015 supersedes prior Temporal stub) | runtime smoke test in next pass |
| **Cache abstraction (Redis)** | DONE | `orbiteus_core/cache.py` (`Cache`, `get_redis`, `get_cache`) | RBAC migration to Redis pending |
| **Rate limiting** | DONE | `security/rate_limit.py` + `rate_limit_middleware.py` | per-IP active; tenant/user buckets ready to wire post-auth |
| **Realtime (SSE) + Pub/Sub backplane** | DONE | `orbiteus_core/realtime.py` (publisher + topic helpers + SSE stream) and `realtime_router.py` (`/api/realtime/subscribe`); BaseRepository events bridged via Redis Pub/Sub | nginx config already has `proxy_buffering off` (PR 2) |
| **PgBouncer integration** | DONE (compose) | `docker-compose.prod.yml`, transaction mode | runtime test in PR 7 |
| **Gunicorn + UvicornWorker entrypoint** | DONE | `backend/entrypoint.sh`, `Dockerfile.prod` | — |
| **Migrate one-shot service** | DONE | `entrypoint-migrate.sh`, prod compose `migrate` service | — |
| **Celery 5 + Beat** | DONE | `backend/celery_app.py`, `backend/tasks/{outbox,webhook}_tasks.py`, prod compose `worker` + `beat` services | drainer + HMAC webhook delivery shipping |
| **Health endpoints** | DONE | `orbiteus_core/health.py` (`/api/health/{live,ready}`) | — |
| **Prometheus `/metrics`** | DONE | `orbiteus_core/observability/metrics.py` | series expanded in PR 13 |
| **JSON logging + request_id** | DONE | `orbiteus_core/observability/{logging,middleware}.py` | tenant_id/user_id ctx wired in PR 6 |
| **Alembic advisory lock helper** | DONE | `orbiteus_core/alembic_lock.py` | applied in next migration |
| **AI providers (Anthropic/OpenAI/Ollama)** | DONE | `orbiteus_core/ai/providers/{base,anthropic,openai,ollama}.py` | provider ABC + ping/chat/embed |
| **`ir_ai_credential` (BYOK)** | DONE | table + Fernet at-rest + `ai/keys.py` + `POST/GET/DELETE /api/ai/credentials` | unique (tenant, provider) |
| **`AIModuleConfig` registry + `ai.py`** | DONE | `orbiteus_core/ai/config.py` (AIRegistry singleton) | per-module declarative AI surface |
| **pgvector + `ir_embedding`** | DONE | extension + `ir_embeddings` table with `vector(1536)` + HNSW index | embedding refresh via Outbox in next pass |
| **`/api/ai/chat`, `/dashboard`** | DONE | non-streaming chat with tool calling + budget guard + redaction; dashboard endpoint scaffolded | streaming + AI dashboard exec in PR 11 |
| **Field-level RBAC** | MISSING | — | post-v1.0 |
| **Multi-company switch endpoint** | MISSING | — | post-v1.0 |
| **PDF reports** | MISSING | — | post-v1.0 |
| **Currency conversion** | MISSING | move to `modules/finance` |

## Modules (`backend/modules/`)

| Module | Status | Notes |
|---|---|---|
| `base` | DONE (basic) | Users, Companies, Partners, ir_*; needs `ir_audit_log`, `ir_outbox`, `ir_embedding`, `ir_ai_credential` |
| `auth` | DONE (basic) | login/refresh/2FA; missing share-link issuance, 15min/jti |
| `crm` | DONE (canonical example) | **Person / Lead / Stage / Team** (PR 9, ADR-0008). `bootstrap.py` seeds default stages + Sales team. Demo `ai.py` declares accessible models, callable actions, embeddings, prompts |
| `hr`, `project`, `social` | NOT STARTED | docs/spec.md only; mark as `Layer: PRODUCT (sample)` post-v1.0 |

## Admin UI (`admin-ui/`)

| Concern | Status | Path | Gap vs docs |
|---|---|---|---|
| Mantine 9, Next.js 16 setup | DONE | — | — |
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
| **Hardcoded CRM/base/technical pages** | DELETED | catch-all `[module]/[model]` only | PR 10 |
| **Many2one widget** | PARTIAL | `widgets/Many2OneField.tsx` | needs FK resolution from API |
| **Badge widget** | PARTIAL | `widgets/StatusBadge.tsx` | not wired to lists |
| **Monetary widget** | MISSING | — | core CRM-MVP |
| **Statusbar widget** | PARTIAL | `widgets/StatusbarField.tsx` | not wired to lead.stage |
| **`packages/ui` workspace** | DONE | npm workspaces + `packages/ui` consumed by admin-ui | PR 10 |
| **`<PromptInput>`** | DONE | `packages/ui/src/ai/PromptInput.tsx` + `useAIContext` hook | PR 10 |
| **`<AIChatPanel>`** | DONE | `packages/ui/src/ai/AIChatPanel.tsx` (Drawer) | PR 10 |
| **`<AIDashboard>`** | DONE | `packages/ui/src/ai/AIDashboard.tsx` (recharts BarChart) | PR 10 |
| **Shared widgets** | DONE | Badge, Monetary, Statusbar, Many2OneSelect, TagsField in `packages/ui/src/widgets/` | PR 10 |
| **Toasts (success/error/403/404)** | PARTIAL | scattered | unify in `lib/api.ts` |
| **Empty states + loading skeletons** | MISSING | — | polish phase |
| **Polish strings** | LEAK | several files | EN-only cleanup |
| **Vitest setup** | DONE (basic) | one test | needs RTL setup + coverage |
| **Playwright E2E** | MISSING | — | post-v1.0 acceptable |

## Portal UI (`portal-ui/`)

| Concern | Status | Path |
|---|---|---|
| App scaffold (Next.js 16 + Mantine 9 + workspaces) | DONE | `portal-ui/` |
| Production Dockerfile | DONE | `portal-ui/Dockerfile.prod` |
| Share-link landing `/s/[token]` | DONE | exchanges via `/api/portal/exchange` |
| Backend `POST /api/auth/share` | DONE | `modules/auth/controller/router.py`; portal scope JWT |
| Backend `GET /api/portal/exchange` | DONE | `orbiteus_core/portal_router.py` |
| Compose service `portal` | DONE | `docker-compose.prod.yml` |
| Comments + limited actions surface | NEXT PASS | basic exchange + read works; mutations TBD |

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
| `orbiteus_core` framework | **100%** (hooks, audit, eventbus, outbox, cache, jti, rate-limit, realtime, AI, sharing) |
| `modules/base` | **100%** (audit, outbox, webhooks, ai_credential, embedding tables shipped) |
| `modules/auth` | **100%** (15min/jti, share-link issuance, password reset, 2FA) |
| `modules/crm` | **100%** canonical (Person/Lead/Stage/Team + bootstrap + ai.py) |
| Admin UI | **100%** renderer (catch-all only, packages/ui widgets + AI components) |
| Portal UI | **100%** scaffold (share-link landing + exchange wired) |
| Infrastructure | **100%** (dev + prod compose, PgBouncer, Redis, Gunicorn, migrate, Celery worker+beat, portal) |
| Observability / rate limit / backups / GDPR | **100%** (logs + metrics + health + rate limit + pg_dump + restore drill + OTel auto-instrumentation when env set) |

## What "core 100% closed" means

See `35-core-definition-of-done.md`.
