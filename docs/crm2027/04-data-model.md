# 04 — Data Model: Object Catalog & Field-Type System

> The complete CRM 2027 data model: the field-type system, the standard object
> catalog (code-first), the metadata/custom layer (runtime), and relations.
> Notation follows the Orbiteus convention — every object is a `BaseModel`
> (carries `id`, `tenant_id`, `company_id`, `create_date`, `write_date`,
> `active`, `custom_fields`, `created_by_id`, `modified_by_id`) unless marked
> `SystemModel`.

## 1. Field-type system

Each field type is a registered class (`orbiteus_core/fields/`) declaring
storage, schema, validation, widget, filter operators, audit formatter, and AI
serialization. This is the contract every object below builds on.

| Type | Storage | Widget | Notes |
|---|---|---|---|
| `text` | varchar | TextInput | single line |
| `long_text` | text | Textarea | |
| `rich_text` | jsonb/html | RichEditor | sanitized HTML; mentions support |
| `integer` | integer | NumberInput | |
| `number` | numeric | NumberInput | precision/scale configurable |
| `boolean` | boolean | Switch | |
| `date` | date | DatePicker | |
| `datetime` | timestamptz | DateTimePicker | tz-aware |
| `duration` | interval/int(min) | DurationInput | minutes under the hood |
| `select` | varchar + `selection_values` | Select/Badge | colored options |
| `multi_select` | jsonb[] | MultiSelect/Tags | |
| `email` | varchar | EmailInput | validated |
| `emails` | jsonb[] | EmailsField | primary + additional (Twenty parity) |
| `phone` | varchar | PhoneInput | E.164 normalize |
| `phones` | jsonb[] | PhonesField | primary + additional |
| `url` | varchar | LinkInput | |
| `links` | jsonb[] | LinksField | label + url list |
| `address` | jsonb | AddressField | street/city/postcode/country/geo |
| `full_name` | jsonb | FullNameField | first/last (Twenty parity) |
| `currency` / `monetary` | numeric + currency_code | MonetaryField | reuses existing widget |
| `percent` | numeric | PercentInput | 0–100 |
| `rating` | integer | RatingField | 0–5 stars |
| `uuid` | uuid | hidden/readonly | |
| `actor` | jsonb | ActorChip | who/what did it (user/ai/system) — Twenty parity |
| `relation` | uuid FK / join table | Many2One / Many2Many / One2Many | typed via `ir_relation` |
| `json` | jsonb | JsonField | raw/structured |
| `attachment` | FK → `ir_attachment` | AttachmentField | drag-drop |
| `geolocation` | jsonb (lat/lng) | MapField | |
| `formula` / `computed` | virtual | readonly | derived; dependency graph (later wave) |
| `rollup` / `aggregate` | virtual | readonly | aggregate over a relation (later wave) |

Each type round-trips through audit diffs and AI tool serialization so new types
are instantly auditable and AI-addressable.

## 2. Standard object catalog (code-first)

Objects already present in the engine are marked **(exists)**; objects to add are
marked **(new)** or **(promote)** (exists elsewhere, promote to core/CRM).

### 2.1 People & accounts

#### `crm.organization` (exists) — B2B account
Keep current fields; add: `email`(emails), `phone`(phones), `links`, `address`
(structured), `annual_revenue`(monetary), `employee_count`(integer),
`lifecycle_stage`(select), `owner_id`(relation→user), `parent_org_id`
(relation→self), `domain`(text, for enrichment/dedup).

#### `crm.person` (exists) — contact
Keep; add: `full_name`(full_name), `emails`, `phones`, `links`,
`job_title`(text), `address`, `linkedin`(url), `owner_id`,
`lifecycle_stage`(select), `do_not_contact`(boolean), `birthday`(date).

### 2.2 Pipeline & revenue

#### `crm.pipeline` (exists), `crm.stage` (exists), `crm.team` (exists)
Keep as-is (Pipedrive-class). Add to stage: `kanban_color`(text),
`is_default_for_new`(boolean).

#### `crm.lead` (exists) — deal / opportunity
Keep (lifecycle + UTM + scoring + rotting). Add: `currency_code`(text),
`weighted_revenue`(formula = expected_revenue × probability),
`closed_at`(datetime), `won`(boolean), `lost`(boolean),
`primary_contact_id`(relation→person), `source_id`(relation→`crm.source`),
`campaign_id`(relation→`crm.campaign`), `next_activity_id`(relation→activity).

#### `crm.prospect` (exists), `crm.stage_history` (exists)
Keep.

#### `crm.product` (new) — sellable item/catalog
`name`, `sku`(text), `description`(long_text), `unit_price`(monetary),
`currency_code`, `cost`(monetary), `tax_rate`(percent), `category`(select),
`is_active`(boolean), `uom`(text). *(Distinct from `inventory.product`; cross-module
link by UUID FK if both installed — no cross-module import.)*

#### `crm.price_book` (new) + `crm.price_book_entry` (new)
Tiered/segmented pricing: `price_book`(name, currency, is_default);
`price_book_entry`(price_book_id, product_id, unit_price, min_qty).

#### `crm.quote` (new) — proposal / CPQ header
`name`/number (via `ir_sequence`), `lead_id`(relation), `organization_id`,
`person_id`, `status`(select: draft/sent/accepted/rejected/expired),
`valid_until`(date), `currency_code`, `subtotal`/`tax`/`total`(monetary, rollup),
`terms`(rich_text), `pdf_attachment_id`(attachment).

#### `crm.quote_line` (new) — line item
`quote_id`(relation), `product_id`(relation), `description`, `quantity`(number),
`unit_price`(monetary), `discount`(percent), `tax_rate`(percent),
`line_total`(formula).

#### `crm.contract` / `crm.subscription` (new, later wave)
`name`, `organization_id`, `quote_id`, `status`(select), `start_date`,
`end_date`, `mrr`/`arr`(monetary), `renewal_date`, `auto_renew`(boolean).

### 2.3 Activities & collaboration

#### `crm.activity` (exists) — promote to unified task/event
Keep; add: `reminder_at`(datetime), `priority`(select), `location`(text),
`participants_json`(multi_select user ids), `recurrence_rule`(text, RFC 5545),
`calendar_event_id`(relation→`comms.calendar_event`).

#### `mail.message` (new, core primitive) — note / comment / chatter
`res_model`(text), `res_id`(uuid), `kind`(select: note/comment/log),
`body`(rich_text), `author_id`(relation→user/actor), `mentions_json`(multi_select),
`parent_id`(relation→self, threading), `attachment_ids`(relation→ir_attachment).

#### `notification` (new, core primitive)
`user_id`, `kind`(select), `title`, `body`, `res_model`, `res_id`, `is_read`,
`channel`(select: in_app/email), `created_at`. Delivered via outbox (email) +
realtime (in-app).

#### `ir_attachment` (exists) — finish admin-UI drag-drop upload.

### 2.4 Communications

#### `comms.email_message` (promote from `crm.email_log`)
`thread_id`(relation), `direction`(select), `from`/`to`/`cc`/`bcc`(emails),
`subject`, `body`(rich_text), `sent_at`/`received_at`, `provider_message_id`,
`res_model`/`res_id`(linked record), `mailbox_id`(relation), `is_read`.

#### `comms.email_thread` (new)
`subject`, `participants_json`, `last_message_at`, `res_model`/`res_id`.

#### `comms.mailbox` (new) — connected account
`user_id`, `provider`(select: gmail/imap/smtp), `email`, `oauth_token`(encrypted),
`sync_state`(select), `last_synced_at`, `folders_json`.

#### `comms.calendar_event` (new)
`calendar_id`(relation), `title`, `start`/`end`(datetime), `attendees_json`,
`location`, `provider_event_id`, `res_model`/`res_id`, `recurrence_rule`.

#### `comms.calendar` (new) — connected calendar
`user_id`, `provider`(select: google/caldav), `oauth_token`(encrypted),
`sync_state`, `last_synced_at`.

#### `ir_mail_template` (exists) — finish template-driven send.

### 2.5 Automation & intelligence

#### `crm.automation_rule` (exists) → promote to `workflow.automation` (new)
`name`, `object`(text), `trigger`(select), `trigger_config`(json),
`condition_json`(filter DSL), `actions_json`(ordered action list),
`is_active`(boolean), `run_count`(integer), `last_run_at`(datetime).

#### `workflow.run` (new) — execution log
`automation_id`, `trigger_payload_json`, `status`(select: pending/running/done/
failed/dead), `step`(integer), `error`(text), `outbox_ref`. Audited + outbox-driven.

#### `crm.scoring_model` (new)
`name`, `object`(text: lead/prospect), `rules_json`(field → weight),
`is_active`. Recompute via outbox; writes `score` + `score_updated_at`.

#### `ir_embedding` (exists) — finish refresh + retrieval.

### 2.6 Analytics & marketing

#### `analytics.dashboard` (new) + `analytics.widget` (new)
`dashboard`(name, owner, is_shared, layout_json);
`widget`(dashboard_id, kind: kpi/bar/line/pie/table/funnel, query_json from the
filter/aggregate DSL, title, position).

#### `analytics.report` (new)
`name`, `object`, `query_json`, `schedule`(cron via ir_cron),
`recipients_json`, `format`(select: csv/pdf).

#### `crm.goal` (new) — quota/target
`name`, `user_id`/`team_id`, `metric`(select: revenue/deals/activities),
`period`(select), `target`(number), `actual`(rollup).

#### `crm.campaign` (new, later wave) + `crm.segment` (new, later wave)
`campaign`(name, channel, budget, start/end, utm defaults, status);
`segment`(name, object, filter_json, member_count rollup).

#### `crm.source` (new) — lead source dimension
`name`, `category`(select), `is_active`.

### 2.7 Platform

#### `ir_view` (promote from `crm.queue`) — saved views (see ch. 03 §4).
#### `favorite` (new), `recent_view` (new) — per-user pins + recents.
#### `api_key` (new) — programmatic tokens (hashed), scoped per tenant + role.
#### `ir_webhook` (exists) — keep; add per-event subscription UI.
#### `tag` / `label` (promote) — first-class tags object (currently JSONB lists).

## 3. Metadata / custom layer (runtime)

These are `SystemModel`/tenant-scoped registry tables that let users extend the
model at runtime (see [`03-architecture-strategy.md`](./03-architecture-strategy.md)):

- `ir_model` (exists) — all objects, standard + custom.
- `ir_model_field` (exists, extend) — all fields, with `storage`(jsonb/column),
  `widget`, `default_json`, `group_id`, `help`.
- `ir_custom_object` (new) — tenant custom objects + storage strategy.
- `ir_field_group` (new) — record-page field grouping.
- `ir_relation` (new) — typed relations + m2m join metadata.

Custom fields default to **JSONB storage** in `custom_fields`; opt-in
**materialization** creates physical columns/tables via the advisory-locked
`MetadataService` (background, audited).

## 4. Relations map (high level)

```
organization 1───* person
organization 1───* lead          person 1───* lead (primary_contact)
pipeline    1───* stage          stage 1───* lead
lead        1───* quote          quote 1───* quote_line  ──* product
lead        1───* activity       *───* product via quote_line
lead        *───1 campaign  ──* source
record(any) 1───* mail.message (timeline)   record(any) 1───* activity
record(any) 1───* email_message (via thread)  mailbox 1───* email_message
user        1───* favorite / recent_view / notification / mailbox / calendar
automation  1───* workflow.run
dashboard   1───* widget
```

All relations are UUID FKs (or m2m join tables described in `ir_relation`). Per
the hard rules, cross-*module* relations (e.g. CRM ↔ inventory) are UUID FKs
only — never Python imports across modules.

## 5. Sequences & numbering

Quotes, contracts, and reports use `ir_sequence` (exists) for human-readable
numbers (e.g. `Q-2027-00042`), configurable per tenant.

## 6. Migration & compatibility notes

- Extending existing CRM objects with new fields uses Alembic migrations
  (standard) or runtime JSONB (custom).
- `crm.email_log` → `comms.email_message`: dual-write window, then deprecate,
  per the engine's migration convention (see
  [`../26-canonical-crm.md`](../26-canonical-crm.md) for the pattern).
- `crm.automation_rule` → `workflow.automation`: keep the table, add columns,
  migrate rule JSON into the new actions schema.
- `crm.queue` → `ir_view`: promote to core; migrate rows.

The per-task migration steps live in [`06-task-backlog.md`](./06-task-backlog.md).
