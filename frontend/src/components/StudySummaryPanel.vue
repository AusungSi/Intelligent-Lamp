<script setup lang="ts">
import { useStudySummary } from '@/composables/useStudySummary'

const {
  loading,
  error,
  currentSession,
  latestSummary,
  todaySummary,
  formatDuration,
} = useStudySummary()

function formatClock(timestamp?: number | null): string {
  if (!timestamp) {
    return '--:--'
  }

  const date = new Date(timestamp * 1000)
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}
</script>

<template>
  <div class="panel-stack">
    <section v-if="loading" class="loading-card">正在生成学习摘要...</section>
    <section v-if="error" class="loading-card loading-card--error">{{ error }}</section>

    <template v-if="!loading && !error">
      <section class="summary-grid">
        <article class="summary-card summary-card--highlight">
          <p class="eyebrow">Current Session</p>
          <h2>当前学习会话</h2>
          <template v-if="currentSession">
            <div class="summary-card__stats">
              <div>
                <span>开始时间</span>
                <strong>{{ formatClock(currentSession.started_at) }}</strong>
              </div>
              <div>
                <span>已学习</span>
                <strong>{{ formatDuration(currentSession.duration_seconds) }}</strong>
              </div>
              <div>
                <span>异常提醒</span>
                <strong>{{ currentSession.warning_count ?? 0 }} 次</strong>
              </div>
              <div>
                <span>离桌次数</span>
                <strong>{{ currentSession.leave_count ?? 0 }} 次</strong>
              </div>
            </div>
            <p class="summary-card__note">会话进行中，系统将持续监测坐姿与环境状态。</p>
          </template>
          <p v-else class="summary-card__empty">当前没有进行中的学习会话。</p>
        </article>

        <article class="summary-card">
          <p class="eyebrow">Latest Report</p>
          <h2>最近一次学习摘要</h2>
          <p v-if="latestSummary?.summary_text" class="summary-card__text">
            {{ latestSummary.summary_text }}
          </p>
          <p v-else class="summary-card__empty">暂无已完成的学习摘要。</p>
        </article>
      </section>

      <section v-if="todaySummary" class="content-panel">
        <div class="section-title">
          <div>
            <p class="eyebrow">Today</p>
            <h2>今日学习汇总</h2>
          </div>
        </div>

        <div class="today-stats">
          <div>
            <span>累计学习</span>
            <strong>{{ formatDuration(todaySummary.total_duration_seconds) }}</strong>
          </div>
          <div>
            <span>异常提醒</span>
            <strong>{{ todaySummary.total_warning_count }} 次</strong>
          </div>
          <div>
            <span>离桌次数</span>
            <strong>{{ todaySummary.total_leave_count }} 次</strong>
          </div>
        </div>

        <div class="session-list">
          <article
            v-for="session in todaySummary.sessions"
            :key="session.id"
            class="session-item"
          >
            <div class="session-item__head">
              <strong>
                {{ formatClock(session.started_at) }}
                -
                {{ session.status === 'active' ? '进行中' : formatClock(session.ended_at) }}
              </strong>
              <span :class="session.status === 'active' ? 'tag tag--active' : 'tag'">
                {{ session.status === 'active' ? '进行中' : '已结束' }}
              </span>
            </div>
            <p>
              时长 {{ formatDuration(session.duration_seconds) }} · 异常
              {{ session.warning_count ?? 0 }} 次 · 离桌 {{ session.leave_count ?? 0 }} 次
            </p>
          </article>
        </div>
      </section>
    </template>
  </div>
</template>
