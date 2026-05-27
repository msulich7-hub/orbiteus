/**
 * Shipping kiosk types — aligned with backend compose-preview / workspace APIs.
 * See `backend/modules/shipping/docs/ux-kiosk.md` §9.2.
 *
 * Endpoints may return 404 until SHP-004..007 land; UI uses optional chaining.
 */

export type ShpSuggestedMode = "auto" | "kiosk";

export type ShpQueueState = "queued" | "processing" | "dispatched" | "failed";

export type ShpHandlingUnitType = "pallet" | "parcel" | string;

export interface ShpRecipient {
  company_name?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  city?: string | null;
  postal_code?: string | null;
  zip?: string | null;
  country_code?: string | null;
  country?: string | null;
  address?: string | null;
  phone?: string | null;
  email?: string | null;
}

export interface ShpHandlingUnit {
  id: string;
  type?: ShpHandlingUnitType;
  pack_type?: string;
  qty?: number;
  weight_kg?: number;
  length_cm?: number;
  width_cm?: number;
  height_cm?: number;
}

export interface ShpWaybillPlan {
  index?: number;
  carrier_code?: string;
  hu_ids?: string[];
  weight_kg?: number;
  is_pallet?: boolean;
  force_carrier?: string | null;
  parcels?: unknown[];
}

export interface ShpSuggestedPlan {
  waybills?: ShpWaybillPlan[];
}

export interface ShpComposePreview {
  ifs_shipment_id?: string;
  queue_id?: string;
  dispatch_id?: string | null;
  state?: ShpQueueState | string;
  suggested_mode?: ShpSuggestedMode;
  suggested_carrier?: string | null;
  order_no?: string | null;
  order_id?: string | null;
  ifs_sid?: string | null;
  objstate?: string | null;
  total_weight_kg?: number | null;
  recipient?: ShpRecipient | null;
  handling_units?: ShpHandlingUnit[];
  suggested_plan?: ShpSuggestedPlan | null;
  blocking_errors?: string[];
  warnings?: string[];
}

export interface ShpComposePlanBody {
  order_id?: string | null;
  waybills: ShpWaybillPlan[];
}

export interface ShpComposePlanResponse {
  saved?: boolean;
  revision?: number;
}

export interface ShpDispatchPlanBody {
  order_id: string;
  waybills: ShpWaybillPlan[];
  print_labels?: boolean;
  force_carrier?: string | null;
}

export interface ShpWaybillJob {
  index?: number;
  outbox_id?: string;
  state?: string;
}

export interface ShpDispatchPlanResponse {
  ok?: boolean;
  outbox_batch_id?: string;
  waybill_jobs?: ShpWaybillJob[];
  ifs_shipment_id?: string;
  outbox_id?: string;
  state?: string;
}

export interface ShpDispatchStatusWaybill {
  index?: number;
  state?: string;
  tracking_number?: string | null;
  error_message?: string | null;
}

export interface ShpDispatchStatus {
  ifs_shipment_id?: string;
  queue_state?: string;
  waybills?: ShpDispatchStatusWaybill[];
}

export interface ShpAssignUnitBody {
  hu_id: string;
  waybill_index: number;
  qty?: number;
}

export interface ShpAssignUnitResponse {
  ok?: boolean;
  revision?: number;
}

/** Workspace draft for an in-flight dispatch (SHP-005). */
export interface ShpDispatchWorkspace {
  dispatch_id?: string;
  pool?: ShpHandlingUnit[];
  waybills?: ShpWaybillPlan[];
  revision?: number;
}

/** Row from `GET /api/shipping/ifs/queue`. */
export interface ShpIfsQueueRow {
  id: string;
  ifs_shipment_id: string;
  ifs_sid?: string;
  objstate?: string;
  state: string;
  payload_json?: string;
  error_message?: string;
  order_no?: string | null;
  forward_agent_id?: string | null;
  total_weight_kg?: number | null;
  line_count?: number;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ShpCarrierStatusResponse {
  configured_carriers?: string[];
  routing_defaults?: Record<string, string | number | boolean>;
}

export type ShpInboxFilter = "queued" | "processing" | "failed" | "all";

export const SHP_QUEUE_STATE_LABELS: Record<string, string> = {
  queued: "W kolejce",
  processing: "Przetwarzanie",
  dispatched: "Wysłano",
  failed: "Błąd",
  label_created: "Etykieta",
};

export const SHP_QUEUE_STATE_COLORS: Record<string, string> = {
  queued: "gray",
  processing: "blue",
  dispatched: "green",
  failed: "red",
  label_created: "green",
};
