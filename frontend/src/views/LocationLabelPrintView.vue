<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { fetchContainerBoard, fetchLocation } from '@/api/catalog'
import LocationQrCode from '@/components/ui/LocationQrCode.vue'
import type { ContainerBoard, LocationNode } from '@/types'
import { toMsloc } from '@/utils/msloc'

type PrintLabel = {
  id: number
  kind: 'container' | 'slot'
  title: string
  fullCode: string
}

const route = useRoute()
const loading = ref(true)
const error = ref<string | null>(null)
const labels = ref<PrintLabel[]>([])
const heading = ref('位置标签')

const scope = computed(() => String(route.query.scope || 'all'))

onMounted(() => {
  void loadLabels()
})

function printPage() {
  window.print()
}

async function loadLabels() {
  const id = Number(route.query.id)
  if (!Number.isFinite(id) || id <= 0) {
    error.value = '缺少有效的位置 ID'
    loading.value = false
    return
  }
  try {
    const location = await fetchLocation(id)
    if (location.layout_type && !location.is_slot) {
      await loadContainerLabels(location)
    } else {
      labels.value = [toLabel(location)]
      heading.value = `${location.name} 标签`
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '标签加载失败'
  } finally {
    loading.value = false
  }
}

async function loadContainerLabels(container: LocationNode) {
  heading.value = `${container.name} 标签`
  if (scope.value === 'container') {
    labels.value = [toLabel(container)]
    return
  }
  const board: ContainerBoard = await fetchContainerBoard(container.id)
  const slotLabels = board.slots.map((slot) => toLabel(slot.location))
  labels.value = scope.value === 'slots' ? slotLabels : [toLabel(container), ...slotLabels]
}

function toLabel(location: LocationNode): PrintLabel {
  return {
    id: location.id,
    kind: location.is_slot ? 'slot' : 'container',
    title: location.is_slot ? location.slot_key || location.name : location.name,
    fullCode: location.full_code,
  }
}
</script>

<template>
  <main class="min-h-screen bg-white text-ink">
    <div class="print:hidden flex items-center justify-between border-b border-line px-5 py-4">
      <div>
        <h1 class="text-[22px] font-semibold">{{ heading }}</h1>
        <p class="mt-1 text-[13px] text-muted">A4 浏览器打印视图</p>
      </div>
      <button class="h-10 rounded-xl bg-green px-4 text-[14px] font-medium text-white" @click="printPage">打印</button>
    </div>

    <div v-if="loading" class="p-8 text-[14px] text-muted">正在生成标签...</div>
    <div v-else-if="error" class="p-8 text-[14px] text-red-700">{{ error }}</div>
    <section v-else class="label-sheet">
      <article v-for="label in labels" :key="label.id" class="location-label">
        <div class="label-text">
          <div class="label-title" :class="label.kind === 'slot' ? 'slot-title' : ''">{{ label.title }}</div>
          <div class="label-code">{{ label.fullCode }}</div>
        </div>
        <LocationQrCode :value="toMsloc(label.fullCode)" :size="104" />
      </article>
    </section>
  </main>
</template>

<style scoped>
.label-sheet {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8mm;
  padding: 12mm;
}

.location-label {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  min-height: 38mm;
  break-inside: avoid;
  border: 1px dashed #b8b1a5;
  padding: 5mm;
}

.label-text {
  min-width: 0;
  padding-right: 4mm;
}

.label-title {
  overflow-wrap: anywhere;
  font-size: 15pt;
  font-weight: 700;
  line-height: 1.15;
}

.slot-title {
  font-size: 28pt;
  letter-spacing: 0;
}

.label-code {
  margin-top: 3mm;
  overflow-wrap: anywhere;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 7.8pt;
  line-height: 1.25;
}

@page {
  size: A4;
  margin: 0;
}

@media print {
  .label-sheet {
    gap: 6mm;
    padding: 10mm;
  }

  .location-label {
    min-height: 35mm;
  }
}

@media (max-width: 760px) {
  .label-sheet {
    grid-template-columns: 1fr;
    padding: 16px;
  }
}
</style>
