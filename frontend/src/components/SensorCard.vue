<script setup lang="ts">
import type { SensorReading } from '@/types/sensor'

defineProps<{
  reading: SensorReading
}>()

const iconMap: Record<SensorReading['key'], string> = {
  illumination: '☀',
  humidity: '◌',
  temperature: '℃',
  distance: '↔',
}
</script>

<template>
  <article class="sensor-card" :class="`sensor-card--${reading.status}`">
    <div class="sensor-card__top">
      <span class="sensor-card__icon">{{ iconMap[reading.key] }}</span>
      <span class="sensor-card__trend">{{ reading.trend }}</span>
    </div>

    <div class="sensor-card__body">
      <p class="sensor-card__label">{{ reading.label }}</p>
      <strong class="sensor-card__value">
        {{ reading.value }}
        <span>{{ reading.unit }}</span>
      </strong>
      <p class="sensor-card__description">{{ reading.description }}</p>
    </div>
  </article>
</template>
