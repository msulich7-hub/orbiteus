# 31 — Backups & Disaster Recovery

## Goals

- **RPO** (Recovery Point Objective): ≤ 1 hour.
- **RTO** (Recovery Time Objective): ≤ 4 hours.

Both achievable on a single host with `pg_dump` + WAL archiving and a tested
restore drill.

## What gets backed up

- PostgreSQL data (full + WAL).
- Attachment storage (`/var/orbiteus/attachments` or S3 path).
- `.env*` files (encrypted, off-host).
- Alembic migration history (in repo).

## What does not need backup

- Redis (transient state — RBAC cache, presence, rate limit counters).
  Outbox dedup keys are durable in Postgres, not Redis.
- Build artifacts (rebuilt from source).

## Tools

| Layer | Tool |
|---|---|
| Postgres logical | `pg_dump` (cron) |
| Postgres physical + WAL | `pgbackrest` (recommended) |
| Object storage | S3-compatible (Backblaze B2, Wasabi, R2) |
| Encryption | `age` or `gpg` (asymmetric) |

`pg_dump` for nightly full + `pgbackrest` for hourly incremental + WAL.

## Schedules

- **Hourly:** WAL archive to S3.
- **Daily 02:00 UTC:** full `pg_dump` → S3 bucket `orbiteus-backups/<env>/<date>/`.
- **Weekly:** verification restore into an isolated container (smoke).
- **Monthly:** full DR drill — restore on a fresh host, run smoke E2E,
  document timing.

## Retention

| Tier | Retention |
|---|---|
| Hourly WAL | 14 days |
| Daily full | 90 days |
| Monthly full | 24 months |
| Annual archive | 7 years (compliance) |

Configurable per tenant if regulatory requirements differ.

## Restore runbook

```
# 1. Provision a fresh Postgres instance
# 2. Decrypt the latest full backup
age -d -i ~/.age/key < backup.tar.zst.age | tar -xJ
# 3. Restore
pg_restore -d orbiteus -j 8 backup.dump
# 4. Apply WAL since backup
# 5. Bring up the rest of the stack against the restored DB
docker compose -f docker-compose.prod.yml up -d
# 6. Run smoke E2E
pytest backend/tests/smoke/
```

## Attachment restore

- S3 bucket versioning enabled.
- Cross-region replication (optional, recommended for production).
- File listing kept in `ir_attachment` rows; if S3 is gone, `ir_attachment`
  remains as an audit trail.

## Disaster scenarios

| Scenario | Response |
|---|---|
| Single host down | Spin up new VPS, restore latest full + WAL, point DNS |
| Postgres data corruption | Restore from last known good full + WAL |
| Ransomware on host | Wipe, restore from off-host backups (encrypted at rest) |
| S3 region outage | Failover to second region (if cross-region replication on) |
| Complete provider loss | Restore on a different cloud — backups are portable |

## Tests

- Restore drill is part of the **monthly** ops cadence; results recorded in
  an internal runbook.
- The CI build runs a synthetic restore: `pg_dump` of a fixture DB →
  `pg_restore` → schema diff zero.

## What backups do not protect against

- Logical mistakes captured before the backup (e.g. `DELETE FROM crm_persons`
  followed by a backup). Use audit log + soft delete defaults to mitigate.
- Recovery of redacted PII (audit redaction is one-way).
- Restoring an `AI_SECRET_KEY` you lost; keep the key in a separate, durable
  secret store (e.g. password manager + paper printout in a safe).
