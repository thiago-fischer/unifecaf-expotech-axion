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
