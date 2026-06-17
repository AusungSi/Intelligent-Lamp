import { onMounted, onUnmounted, ref } from 'vue'

import {
  loadCurrentSession,
  loadLatestSummary,
  loadTodaySummary,
} from '@/api/dataService'
import { formatDuration } from '@/api/statusMapper'
import type { StudySession, TodaySummaryPayload } from '@/types/api'

const SUMMARY_REFRESH_INTERVAL_MS = 3000

export function useStudySummary() {
  const loading = ref(true)
  const error = ref<string | null>(null)
  const currentSession = ref<StudySession | null>(null)
  const latestSummary = ref<StudySession | null>(null)
  const todaySummary = ref<TodaySummaryPayload | null>(null)
  let refreshTimer: ReturnType<typeof setInterval> | null = null
  let refreshing = false

  async function refresh() {
    if (refreshing) {
      return
    }
    refreshing = true
    try {
      const [session, latest, today] = await Promise.all([
        loadCurrentSession(),
        loadLatestSummary(),
        loadTodaySummary(),
      ])
      currentSession.value = session
      latestSummary.value = latest
      todaySummary.value = today
      error.value = null
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : '学习摘要加载失败'
    } finally {
      loading.value = false
      refreshing = false
    }
  }

  function refreshWhenVisible() {
    if (document.visibilityState === 'visible') {
      void refresh()
    }
  }

  onMounted(() => {
    void refresh()
    refreshTimer = setInterval(() => {
      if (document.visibilityState === 'visible') {
        void refresh()
      }
    }, SUMMARY_REFRESH_INTERVAL_MS)
    document.addEventListener('visibilitychange', refreshWhenVisible)
  })

  onUnmounted(() => {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
    document.removeEventListener('visibilitychange', refreshWhenVisible)
  })

  return {
    loading,
    error,
    currentSession,
    latestSummary,
    todaySummary,
    formatDuration,
    refresh,
  }
}
