export interface ApiEnvelope {
  ok: boolean
  message?: string
}

export interface TelemetryRecord {
  device_id?: string
  timestamp?: number
  temperature?: number | null
  humidity?: number | null
  lux?: number | null
  distance_mm?: number | null
  presence_state?: string | null
  distance_level?: string | null
  env_label?: string[] | null
  study_state?: string | null
  study_duration?: number | null
  session_started_at?: number | null
}

export interface HeartbeatRecord {
  device_id?: string
  timestamp?: number
  ip?: string | null
  study_state?: string | null
}

export interface EventRecord {
  id?: number
  device_id?: string
  event_type?: string
  message?: string
  level?: string
  timestamp?: number
  presence_state?: string | null
  distance_level?: string | null
  study_state?: string | null
  extra_json?: Record<string, unknown>
  snapshot_url?: string | null
}

export interface PoseRecord {
  id?: number
  device_id?: string | null
  timestamp?: number
  provider?: string | null
  pose_state?: string | null
  confidence?: number | null
  keypoints?: Array<Record<string, unknown>>
  risk_labels?: string[]
  raw?: Record<string, unknown>
}

export interface CurrentStatusPayload {
  telemetry: TelemetryRecord | null
  heartbeat: HeartbeatRecord | null
  latest_event: EventRecord | null
  pose?: PoseRecord | null
}

export type CurrentStatusResponse = ApiEnvelope & CurrentStatusPayload

export interface StudySession {
  id?: number
  device_id?: string
  started_at?: number
  ended_at?: number | null
  duration_seconds?: number
  warning_count?: number
  leave_count?: number
  summary_text?: string | null
  status?: 'active' | 'completed'
}

export interface TodaySummaryPayload {
  sessions: StudySession[]
  total_duration_seconds: number
  total_warning_count: number
  total_leave_count: number
}

export type TodaySummaryResponse = ApiEnvelope & TodaySummaryPayload

export interface EventsResponse extends ApiEnvelope {
  items: EventRecord[]
  total?: number
  page?: number
  page_size?: number
}

export interface HistoryResponse extends ApiEnvelope {
  items: TelemetryRecord[]
}

export interface SessionResponse extends ApiEnvelope {
  session: StudySession | null
}

export interface LatestSummaryResponse extends ApiEnvelope {
  summary: StudySession | null
}
