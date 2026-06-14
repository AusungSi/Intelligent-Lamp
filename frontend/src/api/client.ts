import type {
  CurrentStatusResponse,
  EventsResponse,
  HistoryResponse,
  LatestSummaryResponse,
  SessionResponse,
  TodaySummaryResponse,
} from '@/types/api'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`请求失败 (${response.status})`)
  }

  const payload = (await response.json()) as T & { ok?: boolean; message?: string }
  if (payload.ok === false) {
    throw new Error(payload.message ?? '接口返回异常')
  }

  return payload
}

export async function fetchCurrentStatus(): Promise<CurrentStatusResponse> {
  return parseJson(await fetch(`${API_BASE}/api/status/current`))
}

export async function fetchEvents(page = 1, pageSize = 50): Promise<EventsResponse> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })
  return parseJson(await fetch(`${API_BASE}/api/status/events?${params.toString()}`))
}

export async function fetchHistory(limit = 120): Promise<HistoryResponse> {
  return parseJson(await fetch(`${API_BASE}/api/status/history?limit=${limit}`))
}

export async function fetchCurrentSession(): Promise<SessionResponse> {
  return parseJson(await fetch(`${API_BASE}/api/status/session/current`))
}

export async function fetchLatestSummary(): Promise<LatestSummaryResponse> {
  return parseJson(await fetch(`${API_BASE}/api/summaries/latest`))
}

export async function fetchTodaySummary(): Promise<TodaySummaryResponse> {
  return parseJson(await fetch(`${API_BASE}/api/summaries/today`))
}
