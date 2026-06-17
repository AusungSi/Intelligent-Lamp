<script setup lang="ts">
import { useEvents } from '@/composables/useEvents'
import {
  eventLevelLabel,
  formatEventTime,
  getEventMessage,
  getEventTypeLabel,
  isBehaviorEvent,
} from '@/api/statusMapper'

const { loading, error, events, page, total, totalPages, goToPage } = useEvents()
</script>

<template>
  <div class="panel-stack">
    <section class="content-panel">
      <div class="section-title">
        <div>
          <p class="eyebrow">Timeline</p>
          <h2>学习过程事件记录</h2>
          <p class="section-desc">
            行为类异常自动关联现场快照；环境类异常仅展示数据与文字提示，全程不采集视频。
          </p>
        </div>
        <span class="tag">共 {{ total }} 条</span>
      </div>

      <section v-if="loading" class="loading-card">正在加载事件记录...</section>
      <section v-else-if="error" class="loading-card loading-card--error">{{ error }}</section>

      <div v-else class="event-list">
        <article
          v-for="event in events"
          :key="event.id ?? event.timestamp"
          class="event-item"
          :class="{
            'event-item--warning': event.level === 'warning',
            'event-item--has-snapshot': !!event.snapshot_url,
          }"
        >
          <div class="event-item__timeline">
            <span></span>
          </div>

          <div class="event-item__body">
            <div class="event-item__head">
              <div>
                <strong>{{ getEventTypeLabel(event.event_type) }}</strong>
                <time>{{ formatEventTime(event.timestamp) }}</time>
              </div>
              <span
                class="tag"
                :class="event.level === 'warning' ? 'tag--warning' : 'tag--info'"
              >
                {{ eventLevelLabel(event.level) }}
              </span>
            </div>

            <p>{{ getEventMessage(event) }}</p>

            <div class="event-item__meta">
              <span v-if="event.presence_state">在位：{{ event.presence_state === 'present' ? '在座' : '离桌' }}</span>
              <span v-if="event.distance_level">距离：{{ event.distance_level }}</span>
              <span v-if="event.study_state">状态：{{ event.study_state }}</span>
            </div>

            <figure v-if="isBehaviorEvent(event) && event.snapshot_url" class="event-snapshot">
              <img :src="event.snapshot_url" :alt="`${getEventTypeLabel(event.event_type)}现场快照`" />
              <figcaption>异常触发时刻现场快照（单帧采集，非连续录像）</figcaption>
            </figure>
          </div>
        </article>
      </div>

      <div v-if="totalPages > 1" class="pagination">
        <button type="button" :disabled="page <= 1" @click="goToPage(page - 1)">上一页</button>
        <span>{{ page }} / {{ totalPages }}</span>
        <button type="button" :disabled="page >= totalPages" @click="goToPage(page + 1)">
          下一页
        </button>
      </div>
    </section>
  </div>
</template>
