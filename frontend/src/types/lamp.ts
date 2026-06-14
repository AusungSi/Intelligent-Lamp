export interface MijiaAccount {
  id: number
  user_id?: string | null
  login_status?: string
  last_verified_at?: number | null
}

export interface MijiaStatus {
  logged_in: boolean
  available: boolean
  account: MijiaAccount | null
  message?: string | null
}

export interface QrLoginStart {
  session_id: string
  status: string
  expires_in: number
  qr_image_url: string
}

export interface QrLoginSession {
  status: 'pending' | 'scanned' | 'confirmed' | 'expired' | 'failed'
  created_at: number
  expires_at: number
  account: MijiaAccount | null
  error?: string | null
}

export interface MijiaDevice {
  did: string
  name: string
  model: string
  room_name?: string | null
  online?: boolean | null
  bindable: boolean
  home_id?: string | null
}

export interface LampBinding {
  id: number
  account_id: number
  did: string
  name?: string | null
  model?: string | null
  room_name?: string | null
  is_active: boolean
  capability?: Record<string, unknown>
}

export interface LampState {
  power?: boolean | null
  brightness?: number | null
  color_temperature?: number | null
  mode: 'auto' | 'manual_override' | 'manual' | 'off'
  online?: boolean | null
  source?: string | null
  manual_override_until?: number
  updated_at?: string | null
}

export interface LampStatePayload {
  bound: boolean
  binding: LampBinding | null
  state: LampState | null
  message?: string
}

export interface LampPolicy {
  id: number
  name: string
  enabled: boolean
  config: Record<string, number | boolean | string>
  updated_at?: string
}

export interface LampCommand {
  id: number
  binding_id?: number | null
  command_type: string
  requested_by: string
  payload: Record<string, unknown>
  status: string
  reason?: string | null
  error_message?: string | null
  created_at?: string
  executed_at?: number | null
}
