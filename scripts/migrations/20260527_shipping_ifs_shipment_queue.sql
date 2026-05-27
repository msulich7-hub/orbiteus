-- IFS inbound queue (Orbiteus shipping.ifs_queue)
-- Apply on Postgres when not using metadata.create_all on empty DB.
-- Idempotent: safe to re-run.

CREATE TABLE IF NOT EXISTS shipping_ifs_shipment_queue (
    id UUID PRIMARY KEY,
    tenant_id UUID,
    company_id UUID,
    create_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    write_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    custom_fields JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by_id UUID,
    modified_by_id UUID,
    ifs_shipment_id VARCHAR(64) NOT NULL,
    ifs_sid VARCHAR(16) NOT NULL DEFAULT '',
    objstate VARCHAR(64) NOT NULL DEFAULT '',
    payload_json TEXT NOT NULL DEFAULT '{}',
    state VARCHAR(32) NOT NULL DEFAULT 'queued',
    error_message TEXT NOT NULL DEFAULT ''
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_shipping_ifs_shipment_queue_ifs_id
    ON shipping_ifs_shipment_queue (ifs_shipment_id);

CREATE INDEX IF NOT EXISTS ix_shipping_ifs_shipment_queue_state
    ON shipping_ifs_shipment_queue (state);

CREATE INDEX IF NOT EXISTS ix_shipping_ifs_shipment_queue_tenant
    ON shipping_ifs_shipment_queue (tenant_id);
