<script setup lang="ts">
import { computed } from 'vue'

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

function onBrightnessChange(event: Event) {
  control({ brightness: Number((event.target as HTMLInputElement).value) })
}

function onColorTemperatureChange(event: Event) {
  control({ color_temperature: Number((event.target as HTMLInputElement).value) })
}
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
              <p>亮度：{{ currentState.brightness ?? '--' }}</p>
              <p>色温：{{ currentState.color_temperature ?? '--' }}</p>
              <p>模式：{{ currentState.mode }}</p>
              <div class="lamp-binding__slider-row">
                <label>
                  亮度
                  <input
                    type="range"
                    min="1"
                    max="100"
                    :value="currentState.brightness ?? 50"
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
                    :value="currentState.color_temperature ?? 4000"
                    @change="onColorTemperatureChange"
                  />
                </label>
              </div>
              <div class="lamp-binding__actions">
                <button type="button" :disabled="busy" @click="control({ power: true })">开灯</button>
                <button type="button" :disabled="busy" @click="control({ power: false })">关灯</button>
                <button type="button" :disabled="busy" @click="changeMode('auto')">自动</button>
                <button type="button" :disabled="busy" @click="changeMode('manual_override')">手动覆盖</button>
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
