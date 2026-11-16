export interface Machine {
  id: number;
  name: string;
}
export interface Step {
  sequence: number;
  machine_id: number;
  processing_time_seconds: number;
}
export interface Product {
  id: number;
  name: string;
  steps: Step[];
}
export interface OrderItem {
  product_id: number;
  quantity: number;
}
export interface Order {
  id: number;
  items: OrderItem[];
}
export interface Operation {
  operation_id: string;
  unit_id: string;
  product_id: number;
  step_sequence: number;
  machine_id: number;
  start_seconds: number;
  end_seconds: number;
  duration_seconds: number;
}
// Campos consumidos pela interface; o contrato completo está no OpenAPI da API.
export interface Plan {
  schema_version: 1;
  order_id: number;
  quality: 'optimal' | 'feasible';
  optimality_proven: boolean;
  selected_source: 'genetic_algorithm' | 'cp_sat';
  execution_ready: false;
  metrics: { makespan_seconds: number; unit_count: number; operation_count: number };
  proof: { method: 'cp_sat' | 'analytical_bound' | 'none' };
  input_snapshot: {
    items: { product_id: number; product_name: string }[];
    machines: { machine_id: number; machine_name: string }[];
  };
  operations: Operation[];
}

export type NetworkHealth = 'online' | 'degraded' | 'offline' | 'disabled' | 'unknown';
export interface NetworkOverview {
  capture_session_id: string | null;
  last_event_at: string | null;
  last_batch_age_ms: number | null;
  services: Record<string, { state: NetworkHealth; detail: string | null }>;
  connections: {
    source: string;
    destination: string;
    visibility: 'observed' | 'configured' | 'unavailable';
  }[];
  security: {
    controller_token_configured: boolean;
    capture_token_configured: boolean;
    local_http_without_tls: boolean;
    ports_restricted_to_host: boolean;
    raw_capture_storage_disabled: boolean;
    accepted_batches: number;
    blocked_batches: number;
  };
  grafana_public_url: string;
  grafana_dashboard_uid: string;
}
export interface NetworkEvent {
  capture_session_id: string;
  sequence: number;
  observed_at: string;
  source_service: string;
  destination_service: string;
  source_port: number;
  destination_port: number;
  protocol: 'HTTP' | 'PostgreSQL' | 'TCP';
  tcp_stream: number;
  frame_length: number;
  http_method: string | null;
  http_path: string | null;
  status_code: number | null;
  latency_ms: number | null;
  retransmission: boolean;
  reset: boolean;
}
export interface NetworkEventsResponse {
  capture_session_id: string | null;
  events: NetworkEvent[];
  next_sequence: number;
  history_lost: boolean;
  session_changed: boolean;
  last_batch_age_ms: number | null;
}
