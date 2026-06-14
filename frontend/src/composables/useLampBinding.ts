import { onMounted, onUnmounted, ref } from 'vue'

import {
  bindLamp,
  controlLamp,
  fetchLampCommands,
  fetchLampState,
  fetchMijiaDevices,
  fetchMijiaStatus,
  fetchQrLoginStatus,
  getQrLoginImageUrl,
  setLampMode,
  startQrLogin,
  unbindLamp,
} from '@/api/lampService'
import type { LampCommand, LampStatePayload, MijiaDevice, MijiaStatus } from '@/types/lamp'

export function useLampBinding() {
  const loading = ref(true)
  const busy = ref(false)
  const error = ref<string | null>(null)
  const mijia = ref<MijiaStatus | null>(null)
  const devices = ref<MijiaDevice[]>([])
  const lamp = ref<LampStatePayload | null>(null)
  const commands = ref<LampCommand[]>([])
  const qrSessionId = ref<string | null>(null)
  const qrStatus = ref<string | null>(null)
  const qrImageUrl = ref<string | null>(null)

  let qrTimer: ReturnType<typeof setInterval> | null = null

  async function refresh() {
    loading.value = true
    try {
      const [status, state, recentCommands] = await Promise.all([
        fetchMijiaStatus(),
        fetchLampState(),
        fetchLampCommands(8),
      ])
      mijia.value = status
      lamp.value = state
      commands.value = recentCommands
      if (status.logged_in) {
        devices.value = await fetchMijiaDevices()
      }
      error.value = null
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : '台灯状态加载失败'
    } finally {
      loading.value = false
    }
  }

  async function beginQrLogin() {
    busy.value = true
    try {
      const session = await startQrLogin()
      qrSessionId.value = session.session_id
      qrStatus.value = session.status
      qrImageUrl.value = getQrLoginImageUrl(session.session_id)
      startPollingQr()
      error.value = null
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : '二维码登录启动失败'
    } finally {
      busy.value = false
    }
  }

  function startPollingQr() {
    if (qrTimer) {
      clearInterval(qrTimer)
    }
    qrTimer = setInterval(async () => {
      if (!qrSessionId.value) {
        return
      }
      const session = await fetchQrLoginStatus(qrSessionId.value)
      qrStatus.value = session.status
      if (['confirmed', 'expired', 'failed'].includes(session.status)) {
        if (qrTimer) {
          clearInterval(qrTimer)
          qrTimer = null
        }
        if (session.status === 'confirmed') {
          await refresh()
        } else if (session.error) {
          error.value = session.error
        }
      }
    }, 2000)
  }

  async function bind(device: MijiaDevice) {
    busy.value = true
    try {
      await bindLamp({
        did: device.did,
        name: device.name,
        model: device.model,
        room_name: device.room_name ?? undefined,
      })
      await refresh()
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : '台灯绑定失败'
    } finally {
      busy.value = false
    }
  }

  async function unbind() {
    busy.value = true
    try {
      await unbindLamp()
      await refresh()
    } finally {
      busy.value = false
    }
  }

  async function control(payload: {
    power?: boolean
    brightness?: number
    color_temperature?: number
  }) {
    busy.value = true
    try {
      lamp.value = await controlLamp({ ...payload, override_minutes: 30 })
      commands.value = await fetchLampCommands(8)
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : '台灯控制失败'
    } finally {
      busy.value = false
    }
  }

  async function changeMode(mode: 'auto' | 'manual_override' | 'manual' | 'off') {
    busy.value = true
    try {
      await setLampMode(mode)
      lamp.value = await fetchLampState()
    } finally {
      busy.value = false
    }
  }

  onMounted(() => {
    void refresh()
  })

  onUnmounted(() => {
    if (qrTimer) {
      clearInterval(qrTimer)
    }
  })

  return {
    loading,
    busy,
    error,
    mijia,
    devices,
    lamp,
    commands,
    qrStatus,
    qrImageUrl,
    refresh,
    beginQrLogin,
    bind,
    unbind,
    control,
    changeMode,
  }
}
