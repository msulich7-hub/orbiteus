# 04 — Data Model

## Two base classes

### `BaseModel` — business records

Every business table inherits these columns:

| Column | Type | Purpose |
|---|---|---|
| `id` | UUID v4 | Primary key |
| `tenant_id` | UUID | Multi-tenant isolation (NOT NULL) |
| `company_id` | UUID NULL | Secondary segmentation |
| `create_date` | timestamptz | Auto on create |
| `write_date` | timestamptz | Auto on update |
| `created_by_id` | UUID NULL | User who created (planned: framework wave 1) |
| `modified_by_id` | UUID NULL | User who last modified (planned) |
| `active` | bool, default true | Soft delete flag |
| `custom_fields` | JSONB | Per-tenant extensions without migrations |

Helper: `make_base_columns()` in `orbiteus_core/mapper.py`.

### `SystemModel` — engine tables

Used only by framework / `modules/base`. No `tenant_id`.

| Column | Type |
|---|---|
| `id` | UUID v4 |
| `create_date` | timestamptz |
| `write_date` | timestamptz |

Helper: `make_system_columns()`.

## Naming rules

- Table names: `<module>_<plural>` for business (`crm_persons`, `hr_employees`).
- Table names: `ir_<thing>` for system (`ir_model_access`, `ir_audit_log`, `ir_outbox`).
- Model dotted names: `<module>.<singular>` (`crm.person`, `hr.employee`).
- Column names: `snake_case`. FKs end with `_id`.

## Foreign keys across modules

**No SQLAlchemy `relationship()` across modules.** Use UUID FK only:

```python
person_id = Column(UUID(as_uuid=True))   # FK conceptually, no relationship()
```

Resolution to display values is done through:

- `BaseRepository.resolve_many2one()` (planned: framework wave 2)
- API response post-processor injecting `{field}__name` and `{field}__display`

This keeps modules independent and supports later splits into separate services
without Python refactor.

## `custom_fields` JSONB

Tenants extend models without migrations:

- `BaseRepository.create()` accepts `custom_fields={"region": "EU-West"}`.
- Frontend reads `custom_fields_def` from `ui-config` per tenant.
- Indexed via `gin (custom_fields jsonb_path_ops)` for filterable keys.

Use `custom_fields` for tenant-specific extensions; new fields shared by all
tenants belong in `mapping.py` with an Alembic migration.

## System tables shipped by `modules/base`

| Table | Purpose |
|---|---|
| `ir_model_access` | Role × model × CRUD matrix |
| `ir_rule` | Record-level domain rules |
| `ir_sequence` | Atomic numbering generator |
| `ir_attachment` | Files associated with records |
| `ir_message` | Chatter / notes thread |
| `ir_activity` | Scheduled follow-ups |
| `ir_cron` | Scheduled jobs (mapped to Celery Beat) |
| `ir_audit_log` | Mandatory CRUD audit |
| `ir_outbox` | Side-effect intents (drained by Celery worker) |
| `ir_embedding` | pgvector vectors per (model, record_id) |
| `ir_ai_credential` | BYOK encrypted provider keys per tenant |
| `ir_ui_menu` | Sidebar menu entries |
| `ir_config_param` | Branding and runtime parameters |

## Migrations policy

- Alembic with `op.create_table` / `op.add_column`.
- Always provide `downgrade()`.
- Run inside the `migrate` service (single-shot) — not in app entrypoint.
- Use `pg_try_advisory_lock(<arbitrary_id>)` at the top of `upgrade()` to be safe
  against concurrent runs.
- Breaking schema changes follow `21-release-and-versioning.md` deprecation policy.

## Indexing rules

- `(tenant_id, <hot_filter_columns>)` composite index on every business table.
- B-tree on FK columns used in joins or filters.
- HNSW index on `ir_embedding.vector` (parameters in `15-ai-layer.md`).
- GIN on `custom_fields jsonb_path_ops` per business table.
