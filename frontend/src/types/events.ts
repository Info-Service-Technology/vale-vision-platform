export interface VisionEvent {
  id: number;
  tenant_id?: number | null;
  camera_id?: number | null;
  container_id?: number | null;
  data_ref?: string | null;
  hora_ref?: string | null;
  file_path?: string | null;
  s3_bucket?: string | null;
  s3_key_raw?: string | null;
  s3_key_debug?: string | null;
  status?: string | null;
  fill_percent?: number | null;
  materiais_detectados?: string | null;
  contaminantes_detectados?: string | null;
  alerta_contaminacao?: number | boolean | null;
  tipo_contaminacao?: string | null;
  cacamba_esperada?: string | null;
  material_esperado?: string | null;
  image_received_at?: string | null;
  processing_status?: string | null;
  resolved_at?: string | null;
}

export interface EventsResponse {
  items: VisionEvent[];
  total: number;
  page: number;
  page_size: number;
}

export interface MetricsResponse {
  total_events: number;
  ok_events: number;
  active_contaminations: number;
  avg_fill_percent: number;
  over_threshold: number;
  system_online: boolean;
  last_frame_at?: string | null;
}
