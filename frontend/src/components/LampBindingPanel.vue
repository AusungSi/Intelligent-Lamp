<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'

import { useLampBinding } from '@/composables/useLampBinding'

const {
  loading,
  busy,
  error,
  mijia,
  devices,
  lamp,
  commands,
  qrStatus,
  qrImageUrl,
  beginQrLogin,
  bind,
  unbind,
  control,
  changeMode,
} = useLampBinding()

const currentState = computed(() => lamp.value?.state)
const currentBinding = computed(() => lamp.value?.binding)
const currentMode = computed(() => currentState.value?.mode)
const localBrightness = ref(50)
const localColorTemperature = ref(4000)
const brightnessEditing = ref(false)
const colorTemperatureEditing = ref(false)

const SLIDER_CONTROL_INTERVAL_MS = 250
const SLIDER_EDITING_RELEASE_MS = 600
let brightnessTimer: ReturnType<typeof setTimeout> | null = null
let colorTemperatureTimer: ReturnType<typeof setTimeout> | null = null
let brightnessEditingTimer: ReturnType<typeof setTimeout> | null = null
let colorTemperatureEditingTimer: ReturnType<typeof setTimeout> | null = null
let lastBrightnessSentAt = 0
let lastColorTemperatureSentAt = 0
let lastBrightnessValue: number | null = null
let lastColorTemperatureValue: number | null = null

watch(
  () => currentState.value?.brightness,
  (brightness) => {
    if (brightness != null && !brightnessEditing.value) {
      localBrightness.value = brightness
    }
  },
  { immediate: true },
)

watch(
  () => currentState.value?.color_temperature,
  (colorTemperature) => {
    if (colorTemperature != null && !colorTemperatureEditing.value) {
      localColorTemperature.value = colorTemperature
    }
  },
  { immediate: true },
)

function isModeSelected(mode: string) {
  return currentMode.value === mode
}

function onBrightnessChange(event: Event) {
  releaseBrightnessEditingSoon()
  sendBrightness(Number((event.target as HTMLInputElement).value))
}

function onColorTemperatureChange(event: Event) {
  releaseColorTemperatureEditingSoon()
  sendColorTemperature(Number((event.target as HTMLInputElement).value))
}

function onBrightnessInput(event: Event) {
  scheduleBrightness(Number((event.target as HTMLInputElement).value))
}

function onColorTemperatureInput(event: Event) {
  scheduleColorTemperature(Number((event.target as HTMLInputElement).value))
}

function scheduleBrightness(value: number) {
  brightnessEditing.value = true
  localBrightness.value = value
  const delay = Math.max(0, SLIDER_CONTROL_INTERVAL_MS - (Date.now() - lastBrightnessSentAt))
  if (delay === 0) {
    sendBrightness(value)
    return
  }
  if (brightnessTimer) {
    clearTimeout(brightnessTimer)
  }
  brightnessTimer = setTimeout(() => sendBrightness(value), delay)
}

function scheduleColorTemperature(value: number) {
  colorTemperatureEditing.value = true
  localColorTemperature.value = value
  const delay = Math.max(0, SLIDER_CONTROL_INTERVAL_MS - (Date.now() - lastColorTemperatureSentAt))
  if (delay === 0) {
    sendColorTemperature(value)
    return
  }
  if (colorTemperatureTimer) {
    clearTimeout(colorTemperatureTimer)
  }
  colorTemperatureTimer = setTimeout(() => sendColorTemperature(value), delay)
}

function sendBrightness(value: number) {
  if (brightnessTimer) {
    clearTimeout(brightnessTimer)
    brightnessTimer = null
  }
  if (lastBrightnessValue === value) {
    return
  }
  localBrightness.value = value
  lastBrightnessValue = value
  lastBrightnessSentAt = Date.now()
  void control({ brightness: value })
}

function sendColorTemperature(value: number) {
  if (colorTemperatureTimer) {
    clearTimeout(colorTemperatureTimer)
    colorTemperatureTimer = null
  }
  if (lastColorTemperatureValue === value) {
    return
  }
  localColorTemperature.value = value
  lastColorTemperatureValue = value
  lastColorTemperatureSentAt = Date.now()
  void control({ color_temperature: value })
}

function releaseBrightnessEditingSoon() {
  if (brightnessEditingTimer) {
    clearTimeout(brightnessEditingTimer)
  }
  brightnessEditingTimer = setTimeout(() => {
    brightnessEditing.value = false
    if (currentState.value?.brightness != null) {
      localBrightness.value = currentState.value.brightness
    }
  }, SLIDER_EDITING_RELEASE_MS)
}

function releaseColorTemperatureEditingSoon() {
  if (colorTemperatureEditingTimer) {
    clearTimeout(colorTemperatureEditingTimer)
  }
  colorTemperatureEditingTimer = setTimeout(() => {
    colorTemperatureEditing.value = false
    if (currentState.value?.color_temperature != null) {
      localColorTemperature.value = currentState.value.color_temperature
    }
  }, SLIDER_EDITING_RELEASE_MS)
}

onUnmounted(() => {
  for (const timer of [
    brightnessTimer,
    colorTemperatureTimer,
    brightnessEditingTimer,
    colorTemperatureEditingTimer,
  ]) {
    if (timer) {
      clearTimeout(timer)
    }
  }
})
</script>

<template>
  <div class="panel-stack">
    <section class="content-panel lamp-binding">
      <div class="section-title">
        <div>
          <p class="eyebrow">Lamp Binding</p>
          <h2>台灯绑定与控制</h2>
          <p class="section-desc">
            扫码登录米家账号后选择台灯绑定，绑定后可在前端直接控制亮度和色温，后端自动策略会在默认模式下接管。
          </p>
        </div>
        <span class="tag" :class="mijia?.logged_in ? 'tag--active' : 'tag--warning'">
          {{ mijia?.logged_in ? '已登录' : '未登录' }}
        </span>
      </div>

      <section v-if="loading" class="loading-card">正在加载台灯状态...</section>
      <section v-else-if="error" class="loading-card loading-card--error">{{ error }}</section>

      <template v-else>
        <div class="lamp-binding__top">
          <div class="lamp-binding__status">
            <strong>米家状态</strong>
            <span>{{ mijia?.available ? '可用' : '待登录或未验证' }}</span>
          </div>
          <div class="lamp-binding__actions">
            <button type="button" :disabled="busy" @click="beginQrLogin">扫码登录</button>
            <button type="button" :disabled="busy" @click="unbind">解除绑定</button>
          </div>
        </div>

        <div v-if="qrImageUrl" class="lamp-binding__qr">
          <img :src="qrImageUrl" alt="米家扫码登录二维码" />
          <div>
            <strong>扫码登录</strong>
            <p>状态：{{ qrStatus }}</p>
          </div>
        </div>

        <div class="lamp-binding__grid">
          <section class="lamp-binding__block">
            <h3>可绑定设备</h3>
            <div class="lamp-binding__device-list">
              <button
                v-for="device in devices"
                :key="device.did"
                type="button"
                class="lamp-binding__device"
                :class="{ 'lamp-binding__device--active': currentBinding?.did === device.did }"
                :disabled="busy || !device.bindable"
                @click="bind(device)"
              >
                <strong>{{ device.name }}</strong>
                <span>{{ device.model }}</span>
                <span>{{ device.room_name ?? '未分配房间' }}</span>
              </button>
            </div>
          </section>

          <section class="lamp-binding__block">
            <h3>当前绑定</h3>
            <template v-if="currentBinding && currentState">
              <p>{{ currentBinding.name }} / {{ currentBinding.model }}</p>
              <p>亮度：{{ localBrightness }}</p>
              <p>色温：{{ localColorTemperature }}</p>
              <p>模式：{{ currentState.mode }}</p>
              <div class="lamp-binding__slider-row">
                <label>
                  亮度
                  <input
                    type="range"
                    min="1"
                    max="100"
                    :value="localBrightness"
                    @input="onBrightnessInput"
                    @change="onBrightnessChange"
                  />
                </label>
                <label>
                  色温
                  <input
                    type="range"
                    min="2700"
                    max="6500"
                    step="100"
                    :value="localColorTemperature"
                    @input="onColorTemperatureInput"
                    @change="onColorTemperatureChange"
                  />
                </label>
              </div>
              <div class="lamp-binding__actions">
                <button type="button" :disabled="busy" @click="control({ power: true })">开灯</button>
                <button type="button" :disabled="busy" @click="control({ power: false })">关灯</button>
                <button
                  type="button"
                  class="lamp-binding__mode-button"
                  :class="{ 'lamp-binding__mode-button--active': isModeSelected('auto') }"
                  :disabled="busy"
                  @click="changeMode('auto')"
                >
                  自动
                </button>
                <button
                  type="button"
                  class="lamp-binding__mode-button"
                  :class="{ 'lamp-binding__mode-button--active': isModeSelected('manual_override') }"
                  :disabled="busy"
                  @click="changeMode('manual_override')"
                >
                  手动覆盖
                </button>
              </div>
            </template>
            <p v-else>尚未绑定台灯。</p>
          </section>
        </div>

        <section class="lamp-binding__block">
          <h3>最近命令</h3>
          <div class="lamp-binding__log">
            <article v-for="item in commands" :key="item.id" class="lamp-binding__log-item">
              <strong>{{ item.command_type }}</strong>
              <span>{{ item.requested_by }} / {{ item.status }}</span>
              <p>{{ item.reason ?? item.error_message ?? '无' }}</p>
            </article>
          </div>
        </section>
      </template>
    </section>
  </div>
</template>
