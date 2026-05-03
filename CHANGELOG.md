# Changelog

All notable changes to Orbiteus are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [SemVer](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-05-03 (engine v1.0)

First **Engine v1.0** — boring tech stack, AI-native, ready for adopters.

### Added

- **Documentation foundation** — 36 numbered chapters in `docs/`, 16 ADRs,
  `pre-prompt.md` for AI agents, validator (`scripts/check_docs.py`).
- **Production HTTP server** — Gunicorn + UvicornWorker with tunable
  workers / timeout / max-requests (ADR-0011).
- **Connection pooling** — PgBouncer in transaction mode in front of
  Postgres 16 (ADR-0012).
- **One-shot migrate service** in `docker-compose.prod.yml`; backend
  depends on its successful completion. Alembic upgrades wrapped in
  `pg_advisory_lock` for multi-replica safety.
- **Observability** — JSON logging with `request_id`/`tenant_id`/`actor`
  context vars, `/metrics` Prometheus endpoint, `/api/health/live` and
  `/api/health/ready`.
- **Repository hooks + audit log (mandatory, opt-out)** — every CRUD writes
  `ir_audit_log` with `actor=user|ai|system`, redacted diff (ADR-0010).
- **EventBus + Postgres Outbox** — durable side-effect queue committed
  atomically with the business transaction (ADR-0010).
- **Celery 5 + Beat** — outbox drainer, HMAC webhook delivery,
  release-stuck-processing schedule (ADR-0013, ADR-0015).
- **Redis cache + rate limit + JWT `jti` revocation** — tighter auth
  defaults (15 min access / 7 day refresh + rotation flag).
- **Realtime SSE** — `/api/realtime/subscribe` with Redis Pub/Sub
  cross-replica fan-out and topic RBAC (ADR-0006, ADR-0014).
- **AI layer (BYOK)** — Fernet-encrypted `ir_ai_credential`, Anthropic /
  OpenAI / Ollama provider adapters, `AIModuleConfig` registry per module,
  `pgvector` embeddings with HNSW index, `/api/ai/credentials`,
  `/api/ai/chat`, `/api/ai/dashboard`, monthly token budget guard, PII
  redaction (ADR-0004, ADR-0005, ADR-0009).
- **Canonical CRM** — Person / Lead / Stage / Team replaces
  Customer / Opportunity / Pipeline. `crm/bootstrap.py` seeds default
  stages + Sales team. Demo `ai.py` declares accessible models, callable
  actions, embeddings, suggested prompts (ADR-0008).
- **Admin UI cleanup** — npm workspaces with `packages/ui` shared widgets
  (Badge / Monetary / Statusbar / Many2OneSelect / TagsField) and AI
  components (`<PromptInput>`, `<AIChatPanel>`, `<AIDashboard>`). All
  hardcoded module pages removed; only catch-all routes remain (ADR-0016).
- **Portal UI** — separate Next.js app at `portal-ui/` with share-link
  exchange (`/s/[token]`) backed by `POST /api/auth/share` and
  `GET /api/portal/exchange` (ADR-0007).
- **Backups** — `scripts/backup_db.sh` (pg_dump + gzip + retention) and
  `scripts/restore_drill.sh` (schema-diff drill).

### Changed

- **No Temporal in MVP** (ADR-0015). `worker.py` and
  `orbiteus_core/temporal.py` removed; replaced by Celery + Outbox.
- **Mantine 8 is the only design system** for both apps (ADR-0002).
- Default Postgres image is **`pgvector/pgvector:pg16`** in dev and prod
  compose.

### Removed

- Hardcoded admin-ui pages under `app/{crm,base,technical}/*`.
- `Sidebar.tsx` (replaced by `AppShellLayout` dynamic sidebar).
- Temporal Python SDK dependency.

### Migrations

Three new Alembic revisions ship with this release:

1. `a1f3c0e1b002_audit_log_and_attribution` — `ir_audit_log` +
   `created_by_id`/`modified_by_id` on every business table.
2. `b2a4e1c0d003_outbox_and_webhooks` — `ir_outbox` + `ir_webhooks`.
3. `c3b5d2e1c004_ai_credentials_and_embeddings` — pgvector extension,
   `ir_ai_credentials`, `ir_embeddings` with HNSW index.
4. `d4c0a1f2e005_canonical_crm` — drops legacy
   `crm_customers`/`crm_opportunities`/`crm_pipelines`, recreates
   `crm_stages`, creates `crm_persons`/`crm_teams`/`crm_leads`.

Adopters running v0.x must back up first and run `alembic upgrade head`
inside the new `migrate` compose service.

### Security

- JWT `jti` revocation list on logout / refresh rotation.
- Provider keys encrypted at rest with Fernet (`AI_SECRET_KEY` from env).
- All migrations guarded by `pg_advisory_lock(11534116837)`.
- Production refuses to start with default `SECRET_KEY` /
  `BOOTSTRAP_ADMIN_PASSWORD` (existing safeguard, retained).

### Tests + CI

- 126/126 top-level tests green.
- `scripts/check_docs.py` link & structure validator.
- GitHub Actions workflow `docs.yml` enforces docs validator on PR.
