import * as client from '@/api/client'
import type {
  CurrentStatusPayload,
  EventRecord,
  StudySession,
  TelemetryRecord,
  TodaySummaryPayload,
} from '@/types/api'

export async function loadCurrentStatus(): Promise<CurrentStatusPayload> {
  const response = await client.fetchCurrentStatus()
  return {
    telemetry: response.telemetry,
    heartbeat: response.heartbeat,
    latest_event: response.latest_event,
  }
}

export async function loadEvents(page = 1, pageSize = 8): Promise<{
  items: EventRecord[]
  total: number
  page: number
  page_size: number
}> {
  const response = await client.fetchEvents(page, pageSize)
  return {
    items: response.items,
    total: response.total ?? response.items.length,
    page: response.page ?? page,
    page_size: response.page_size ?? pageSize,
  }
}

export async function loadHistory(limit = 120): Promise<TelemetryRecord[]> {
  const response = await client.fetchHistory(limit)
  return response.items
}

export async function loadCurrentSession(): Promise<StudySession | null> {
  const response = await client.fetchCurrentSession()
  return response.session
}

export async function loadLatestSummary(): Promise<StudySession | null> {
  const response = await client.fetchLatestSummary()
  return response.summary
}

export async function loadTodaySummary(): Promise<TodaySummaryPayload> {
  const response = await client.fetchTodaySummary()
  return {
    sessions: response.sessions,
    total_duration_seconds: response.total_duration_seconds,
    total_warning_count: response.total_warning_count,
    total_leave_count: response.total_leave_count,
  }
}
