# 23 — Tree Spec: Framework (Backend)

> Source of truth for backend framework status. Tick boxes as items land.
> Last reviewed: 2026-05-03.

## Legend

- `[x]` done and covered by tests
- `[ ]` not done
- `[!]` blocked / needs decision
- `→ ADR-NNNN` references a binding decision

## 1. Architecture skeleton — DONE

- [x] FastAPI + SQLAlchemy 2 imperative + asyncpg + Alembic
- [x] Module Registry + topo sort + lifecycle hooks
- [x] BaseRepository with tenant filter
- [x] Auto-CRUD (5 endpoints / model)
- [x] JWT + bcrypt + TOTP 2FA
- [x] RBAC: `ir_model_access` + `ir_rule` (cache loaded at startup)
- [x] AI Action Registry + RapidFuzz resolver
- [x] `GET /api/base/ui-config`
- [x] Lifespan startup + Alembic upgrade head

## 2. Wave 1 — Foundations

- [x] 2.1 Repository hooks (before/after create/write/unlink) — PR 3
- [x] 2.2 `created_by_id` / `modified_by_id` columns — PR 3
- [x] 2.3 `ir_audit_log` (mandatory, opt-out) → ADR-0010 — PR 3
- [x] 2.4a EventBus (in-process) — PR 3
- [x] 2.4b Postgres Outbox + dispatcher + webhooks table — PR 4
- [ ] 2.5 Many2one resolution in API responses (`{field}__name`)
- [ ] 2.6 Move `_seed_crm_defaults` out of `api.py` to `modules/crm/bootstrap.py`
- [x] 2.7 `migrate` service in compose + Alembic advisory lock — PR 2

## 3. Wave 2 — Cross-cutting infra

- [x] 3.1 Redis cache layer abstraction → ADR-0003 — PR 6
- [ ] 3.2 Move RBAC cache from in-memory to Redis (next pass)
- [x] 3.3 JWT `jti` revocation list in Redis — PR 6
- [ ] 3.4 Idempotency keys in Redis (next pass)
- [x] 3.5 Rate limit token buckets (per-IP active, tenant/user wiring next pass) — PR 6
- [x] 3.6 Celery 5 + Beat → ADR-0013, ADR-0015 — PR 5
- [x] 3.7 Outbox drainer Celery task with retry + dead-letter — PR 5
- [x] 3.8 Realtime: SSE endpoint `/api/realtime/subscribe` — PR 7
- [x] 3.9 Realtime: Redis Pub/Sub backplane → ADR-0014 — PR 7
- [ ] 3.10 Presence (`presence:topic:` sorted set in Redis) — next pass

## 4. Wave 3 — AI layer (engine baseline)

- [x] 4.1 Provider ABC + Anthropic + OpenAI + Ollama implementations → ADR-0009 — PR 8
- [x] 4.2 `ir_ai_credential` table + Fernet at-rest encryption → ADR-0004 — PR 8
- [x] 4.3 BYOK CRUD endpoints (`POST/GET/DELETE /api/ai/credentials`) — PR 8
- [x] 4.4 Provider ping on credential creation — PR 8
- [x] 4.5 `AIModuleConfig` + `AIRegistry` (per-module `ai.py`) — PR 8
- [ ] 4.6 `AIContextBuilder` (RBAC-scoped tools and data) — wired via `tools.build_tools` in PR 8; advanced scoping in PR 11
- [x] 4.7 Tools: ActionTool, QueryTool, semantic_search → ADR-0005 — PR 8
- [x] 4.8 `pgvector` extension + `ir_embedding` table + HNSW index — PR 8
- [ ] 4.9 Outbox-driven embedding refresh on `record.{created,updated,deleted}` — next pass
- [x] 4.10 `/api/ai/chat` endpoint (non-streaming MVP; streaming in PR 11) — PR 8
- [x] 4.11 `/api/ai/dashboard` endpoint (scaffolded chart spec; AI exec in PR 11) — PR 8
- [x] 4.12 Budget guard (`ai:budget:tenant:{id}:{yyyymm}` in Redis) — PR 8
- [x] 4.13 PII redaction pipeline before remote provider calls — PR 8

## 5. Wave 4 — Canonical CRM

- [ ] 5.1 Rename `crm.customer` → `crm.person` (with `kind` enum)
- [ ] 5.2 Rename `crm.opportunity` → `crm.lead`
- [ ] 5.3 Drop `crm.pipeline` (re-introduce in v0.3 if needed) → ADR-0008
- [ ] 5.4 Add `crm.stage`
- [ ] 5.5 Add `crm.team` (leader + members)
- [ ] 5.6 Demo `crm/actions.py` covering create / move stage / assign team
- [ ] 5.7 Demo `crm/ai.py` (suggested prompts, dashboards)
- [ ] 5.8 `crm/bootstrap.py` seeds default stages and one team per tenant
- [ ] 5.9 Aggregate endpoint `/api/base/aggregate`

## 6. Wave 5 — Portal scope

- [ ] 6.1 `portal_users` table + auth flow → ADR-0007
- [ ] 6.2 Share-link issuance endpoint (`POST /api/auth/share`)
- [ ] 6.3 JWT scope enforcement middleware
- [ ] 6.4 `<portal>` view declaration parser
- [ ] 6.5 `/api/portal/*` routes that filter by `aud` claim

## 7. Wave 6 — Operational hardening

- [x] 7.1 Liveness + readiness endpoints (`/api/health/{live,ready}`)
- [x] 7.2 Prometheus exporter (`prometheus_client`) at `/metrics`
- [x] 7.3 Structured JSON logger with `request_id` (tenant_id/user_id ctx wired in later waves)
- [ ] 7.4 OpenTelemetry instrumentation (opt-in)
- [x] 7.5 PgBouncer in compose → ADR-0012
- [x] 7.6 Gunicorn + UvicornWorker in production Dockerfile → ADR-0011
- [ ] 7.7 Backup container running `pg_dump` cron to S3
- [ ] 7.8 Sentinel / Cluster fallback documented (deferred)
- [x] 7.9 One-shot `migrate` service in compose
- [x] 7.10 Alembic `pg_advisory_lock` helper

## 8. Test coverage gates

- [ ] 8.1 `orbiteus_core/` ≥ 90%
- [ ] 8.2 `modules/base/` ≥ 85%
- [ ] 8.3 `modules/auth/` ≥ 85%
- [ ] 8.4 `modules/crm/` ≥ 80%
- [ ] 8.5 Realtime end-to-end test (two clients see one update)
- [ ] 8.6 AI tool call audit row matches actor=ai
