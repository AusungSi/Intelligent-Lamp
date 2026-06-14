import { EVENT_TYPE_LABEL, STUDY_STATE_LABEL } from '@/constants/labels'
import type { CurrentStatusPayload, EventRecord } from '@/types/api'
import type { SensorDashboardPayload, SensorKey, SensorReading, StatusOverview } from '@/types/sensor'

const HEARTBEAT_ONLINE_SECONDS = 30
const DEFAULT_THRESHOLDS = {
  lightLowLux: 150,
  humidityHighPercent: 75,
  temperatureHighC: 30,
}

function formatTimestamp(timestamp?: number | null): string {
  if (!timestamp) {
    return '--'
  }

  const date = new Date(timestamp * 1000)
  const pad = (value: number) => String(value).padStart(2, '0')

  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

function isDeviceOnline(heartbeatTimestamp?: number | null): boolean {
  if (!heartbeatTimestamp) {
    return false
  }

  return Date.now() / 1000 - heartbeatTimestamp <= HEARTBEAT_ONLINE_SECONDS
}

function formatTrend(
  current?: number | null,
  previous?: number,
  stableThreshold = 0.12,
): string {
  if (current == null || previous == null) {
    return '稳定'
  }

  const delta = current - previous
  if (Math.abs(delta) < stableThreshold) {
    return '稳定'
  }

  const sign = delta > 0 ? '+' : ''
  const precision = stableThreshold >= 1 ? 0 : 1
  return `${sign}${delta.toFixed(precision)}`
}

function luxStatus(lux: number | null | undefined): SensorReading['status'] {
  if (lux == null) {
    return 'normal'
  }

  return lux < DEFAULT_THRESHOLDS.lightLowLux ? 'low' : 'normal'
}

function humidityStatus(humidity: number | null | undefined): SensorReading['status'] {
  if (humidity == null) {
    return 'normal'
  }

  return humidity > DEFAULT_THRESHOLDS.humidityHighPercent ? 'high' : 'normal'
}

function temperatureStatus(temperature: number | null | undefined): SensorReading['status'] {
  if (temperature == null) {
    return 'normal'
  }

  return temperature > DEFAULT_THRESHOLDS.temperatureHighC ? 'high' : 'normal'
}

function distanceStatus(distanceLevel?: string | null): SensorReading['status'] {
  if (distanceLevel === 'too_close') {
    return 'high'
  }

  if (distanceLevel === 'far') {
    return 'low'
  }

  return 'normal'
}

function luxDescription(lux: number | null | undefined): string {
  if (lux == null) {
    return '暂无光照数据'
  }

  return lux < DEFAULT_THRESHOLDS.lightLowLux ? '环境偏暗，建议提高亮度' : '光线充足，适合阅读'
}

function humidityDescription(humidity: number | null | undefined): string {
  if (humidity == null) {
    return '暂无湿度数据'
  }

  return humidity > DEFAULT_THRESHOLDS.humidityHighPercent ? '湿度偏高，注意通风' : '湿度舒适，维持当前模式'
}

function temperatureDescription(temperature: number | null | undefined): string {
  if (temperature == null) {
    return '暂无温度数据'
  }

  return temperature > DEFAULT_THRESHOLDS.temperatureHighC ? '温度偏高，注意散热' : '温度适中，无需调整'
}

function distanceDescription(distanceLevel?: string | null): string {
  if (distanceLevel === 'too_close') {
    return '距离过近，请向后调整坐姿'
  }

  if (distanceLevel === 'far') {
    return '未检测到有效用灯距离'
  }

  return '处于推荐用灯距离'
}

function formatDuration(seconds?: number | null): string {
  if (!seconds || seconds <= 0) {
    return '0 分钟'
  }

  const minutes = Math.floor(seconds / 60)
  const remainSeconds = seconds % 60
  if (minutes >= 60) {
    const hours = Math.floor(minutes / 60)
    const remainMinutes = minutes % 60
    return `${hours} 小时 ${remainMinutes} 分`
  }

  return remainSeconds > 0 ? `${minutes} 分 ${remainSeconds} 秒` : `${minutes} 分钟`
}

function eventLevelLabel(level?: string | null): string {
  if (level === 'warning') {
    return '告警'
  }

  return '信息'
}

function buildOverview(payload: CurrentStatusPayload): StatusOverview {
  const { telemetry, latest_event } = payload
  const studyState = telemetry?.study_state ?? 'idle'
  const presence = telemetry?.presence_state ?? 'away'

  let headline = '设备待机中'
  let detail = '暂未检测到学习活动，等待入座后开始陪学监测。'

  if (studyState === 'studying') {
    headline = '正在学习'
    detail = `已持续 ${formatDuration(telemetry?.study_duration)}，环境与坐姿状态正常监测中。`
  } else if (studyState === 'warning') {
    headline = '异常提醒'
    detail = latest_event?.message ?? '检测到需要关注的异常行为或环境变化。'
  } else if (presence === 'present') {
    headline = '已入座'
    detail = '检测到用户在位，等待进入正式学习状态。'
  }

  return {
    studyState,
    presenceState: presence,
    studyDurationText: formatDuration(telemetry?.study_duration),
    headline,
    detail,
    latestEvent: latest_event ?? null,
  }
}

function buildReadings(
  payload: CurrentStatusPayload,
  previousValues?: Partial<Record<SensorKey, number>>,
): SensorReading[] {
  const { telemetry } = payload
  const lux = telemetry?.lux ?? null
  const humidity = telemetry?.humidity ?? null
  const temperature = telemetry?.temperature ?? null
  const distanceCm =
    telemetry?.distance_mm == null ? null : Number((telemetry.distance_mm / 10).toFixed(1))

  return [
    {
      key: 'illumination',
      label: '环境光照',
      value: lux ?? 0,
      unit: 'lx',
      status: luxStatus(lux),
      trend: formatTrend(lux, previousValues?.illumination, 3),
      description: luxDescription(lux),
    },
    {
      key: 'humidity',
      label: '空气湿度',
      value: humidity ?? 0,
      unit: '%',
      status: humidityStatus(humidity),
      trend: formatTrend(humidity, previousValues?.humidity, 1),
      description: humidityDescription(humidity),
    },
    {
      key: 'temperature',
      label: '环境温度',
      value: temperature ?? 0,
      unit: '°C',
      status: temperatureStatus(temperature),
      trend: formatTrend(temperature, previousValues?.temperature, 0.15),
      description: temperatureDescription(temperature),
    },
    {
      key: 'distance',
      label: '人体距离',
      value: distanceCm ?? 0,
      unit: 'cm',
      status: distanceStatus(telemetry?.distance_level),
      trend: formatTrend(distanceCm, previousValues?.distance, 0.8),
      description: distanceDescription(telemetry?.distance_level),
    },
  ]
}

export function mapStatusToDashboard(
  payload: CurrentStatusPayload,
  previousValues?: Partial<Record<SensorKey, number>>,
): SensorDashboardPayload {
  const { telemetry, heartbeat } = payload
  const studyState = telemetry?.study_state ?? heartbeat?.study_state ?? 'idle'
  const updatedAt = formatTimestamp(telemetry?.timestamp ?? heartbeat?.timestamp)

  return {
    lamp: {
      name: 'StudyPilot 学习台灯',
      room: '书房 · 小明',
      online: isDeviceOnline(heartbeat?.timestamp),
      mode: STUDY_STATE_LABEL[studyState] ?? '待机',
      updatedAt,
    },
    overview: buildOverview(payload),
    readings: buildReadings(payload, previousValues),
  }
}

export function formatEventTime(timestamp?: number | null): string {
  return formatTimestamp(timestamp)
}

export function getEventTypeLabel(eventType?: string | null): string {
  return EVENT_TYPE_LABEL[eventType ?? ''] ?? eventType ?? '系统事件'
}

export function isBehaviorEvent(event: EventRecord): boolean {
  return event.event_type === 'presence_away' || event.event_type === 'distance_too_close'
}

export { eventLevelLabel, formatDuration }

export function extractReadingValues(
  dashboard: SensorDashboardPayload,
): Partial<Record<SensorKey, number>> {
  return Object.fromEntries(dashboard.readings.map((reading) => [reading.key, reading.value]))
}
