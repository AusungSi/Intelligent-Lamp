export type SensorKey = 'illumination' | 'humidity' | 'temperature' | 'distance'

export interface SensorReading {
  key: SensorKey
  label: string
  value: number
  unit: string
  status: 'low' | 'normal' | 'high'
  trend: string
  description: string
}

export interface LampState {
  name: string
  room: string
  online: boolean
  mode: string
  updatedAt: string
}

import type { EventRecord } from '@/types/api'

export interface StatusOverview {
  studyState: string
  presenceState: string
  studyDurationText: string
  headline: string
  detail: string
  latestEvent: EventRecord | null
}

export interface SensorDashboardPayload {
  lamp: LampState
  overview: StatusOverview
  readings: SensorReading[]
}
