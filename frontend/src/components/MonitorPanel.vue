<script setup lang="ts">
import { computed } from 'vue'

import SensorCard from '@/components/SensorCard.vue'
import { useSensorDashboard } from '@/composables/useSensorDashboard'
import { formatEventTime, getEventTypeLabel } from '@/api/statusMapper'

const { dashboard, loading, error } = useSensorDashboard()

const statusText = computed(() => (dashboard.value?.lamp.online ? '设备在线' : '设备离线'))
const updatedAtText = computed(() => dashboard.value?.lamp.updatedAt ?? '--')
</script>

<template>
  <div class="panel-stack">
    <section v-if="loading && !dashboard" class="loading-card">正在读取实时监测数据...</section>

    <section v-if="error" class="loading-card loading-card--error">
      数据刷新失败：{{ error }}
    </section>

    <template v-if="dashboard">
      <section class="overview-banner" :class="`overview-banner--${dashboard.overview.studyState}`">
        <div>
          <p class="eyebrow">Study State</p>
          <h2>{{ dashboard.overview.headline }}</h2>
          <p>{{ dashboard.overview.detail }}</p>
        </div>
        <div class="overview-banner__meta">
          <div>
            <span>学习时长</span>
            <strong>{{ dashboard.overview.studyDurationText }}</strong>
          </div>
          <div>
            <span>在位状态</span>
            <strong>{{ dashboard.overview.presenceState === 'present' ? '已入座' : '已离桌' }}</strong>
          </div>
        </div>
      </section>

      <section v-if="dashboard.overview.latestEvent" class="alert-strip">
        <span class="alert-strip__badge">最新事件</span>
        <strong>{{ getEventTypeLabel(dashboard.overview.latestEvent.event_type) }}</strong>
        <span>{{ dashboard.overview.latestEvent.message }}</span>
        <time>{{ formatEventTime(dashboard.overview.latestEvent.timestamp) }}</time>
      </section>

      <section class="dashboard-grid">
        <aside class="device-panel">
          <div class="device-panel__header">
            <div>
              <p class="eyebrow">Device</p>
              <h2>{{ dashboard.lamp.name }}</h2>
              <span>{{ dashboard.lamp.room }}</span>
            </div>
            <div class="lamp-orb">
              <div class="lamp-orb__glow"></div>
            </div>
          </div>

          <div class="device-panel__metrics">
            <div>
              <span>连接状态</span>
              <strong>{{ statusText }}</strong>
            </div>
            <div>
              <span>当前模式</span>
              <strong>{{ dashboard.lamp.mode }}</strong>
            </div>
          </div>

          <p class="device-panel__footer">最后同步：{{ updatedAtText }}</p>
        </aside>

        <section class="content-panel">
          <div class="section-title">
            <div>
              <p class="eyebrow">Realtime</p>
              <h2>传感器实时概览</h2>
            </div>
            <button type="button" disabled>接口轮询 · 2s</button>
          </div>

          <div class="sensor-grid">
            <SensorCard
              v-for="reading in dashboard.readings"
              :key="reading.key"
              :reading="reading"
            />
          </div>
        </section>
      </section>
    </template>
  </div>
</template>
