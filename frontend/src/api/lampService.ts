import type {
  LampBinding,
  LampCommand,
  LampPolicy,
  LampStatePayload,
  MijiaDevice,
  MijiaStatus,
  QrLoginSession,
  QrLoginStart,
} from '@/types/lamp'

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

export async function fetchMijiaStatus(): Promise<MijiaStatus> {
  return parseJson(await fetch(`${API_BASE}/api/lamp/mijia/status`))
}

export async function startQrLogin(): Promise<QrLoginStart> {
  return parseJson(await fetch(`${API_BASE}/api/lamp/mijia/login/qr`, { method: 'POST' }))
}

export async function fetchQrLoginStatus(sessionId: string): Promise<QrLoginSession> {
  const response = await parseJson<{ session: QrLoginSession }>(
    await fetch(`${API_BASE}/api/lamp/mijia/login/qr/${sessionId}/status`),
  )
  return response.session
}

export function getQrLoginImageUrl(sessionId: string): string {
  return `${API_BASE}/api/lamp/mijia/login/qr/${sessionId}/image`
}

export async function fetchMijiaDevices(): Promise<MijiaDevice[]> {
  const response = await parseJson<{ items: MijiaDevice[] }>(
    await fetch(`${API_BASE}/api/lamp/mijia/devices`),
  )
  return response.items
}

export async function fetchCurrentBinding(): Promise<LampBinding | null> {
  const response = await parseJson<{ binding: LampBinding | null }>(
    await fetch(`${API_BASE}/api/lamp/binding/current`),
  )
  return response.binding
}

export async function bindLamp(payload: {
  did: string
  name?: string
  model?: string
  room_name?: string
}): Promise<LampBinding> {
  const response = await parseJson<{ binding: LampBinding }>(
    await fetch(`${API_BASE}/api/lamp/binding`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  )
  return response.binding
}

export async function unbindLamp(): Promise<boolean> {
  const response = await parseJson<{ unbound: boolean }>(
    await fetch(`${API_BASE}/api/lamp/binding/current`, { method: 'DELETE' }),
  )
  return response.unbound
}

export async function fetchLampState(refresh = false): Promise<LampStatePayload> {
  const suffix = refresh ? '?refresh=1' : ''
  return parseJson(await fetch(`${API_BASE}/api/lamp/state${suffix}`))
}

export async function controlLamp(payload: {
  power?: boolean
  brightness?: number
  color_temperature?: number
  override_minutes?: number
}): Promise<LampStatePayload> {
  return parseJson(
    await fetch(`${API_BASE}/api/lamp/control`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  )
}

export async function setLampMode(mode: 'auto' | 'manual_override' | 'manual' | 'off') {
  return parseJson(
    await fetch(`${API_BASE}/api/lamp/mode`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode }),
    }),
  )
}

export async function fetchLampCommands(limit = 20): Promise<LampCommand[]> {
  const response = await parseJson<{ items: LampCommand[] }>(
    await fetch(`${API_BASE}/api/lamp/commands?limit=${limit}`),
  )
  return response.items
}

export async function fetchLampPolicy(): Promise<LampPolicy> {
  const response = await parseJson<{ policy: LampPolicy }>(
    await fetch(`${API_BASE}/api/lamp/policy`),
  )
  return response.policy
}

export async function updateLampPolicy(payload: Partial<LampPolicy>): Promise<LampPolicy> {
  const response = await parseJson<{ policy: LampPolicy }>(
    await fetch(`${API_BASE}/api/lamp/policy`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  )
  return response.policy
}
