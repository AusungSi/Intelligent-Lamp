<script setup lang="ts">
import { ref } from 'vue'

import AppNav from '@/components/AppNav.vue'
import EventTimeline from '@/components/EventTimeline.vue'
import HistoryChartPanel from '@/components/HistoryChartPanel.vue'
import MonitorPanel from '@/components/MonitorPanel.vue'
import StudySummaryPanel from '@/components/StudySummaryPanel.vue'
import type { AppTab } from '@/types/navigation'

const activeTab = ref<AppTab>('monitor')
</script>

<template>
  <main class="app-shell">
    <section class="hero-card">
      <div>
        <p class="eyebrow">StudyPilot Parent Console</p>
        <h1>StudyPilot 智能学习台灯家长端</h1>
        <p class="hero-card__desc">
          入座监测、学习识别、异常提醒、离桌判定与数据复盘一体化管理平台。
        </p>
      </div>
    </section>

    <AppNav :active="activeTab" @change="activeTab = $event" />

    <MonitorPanel v-show="activeTab === 'monitor'" />
    <StudySummaryPanel v-show="activeTab === 'summary'" />
    <EventTimeline v-show="activeTab === 'events'" />
    <HistoryChartPanel v-show="activeTab === 'history'" />
  </main>
</template>
