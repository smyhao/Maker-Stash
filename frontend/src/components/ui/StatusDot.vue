<script setup lang="ts">
import type { Status } from '@/types'

defineProps<{ status: Status }>()

const labels: Record<Status, string> = {
  normal: '正常',
  low: '较低',
  empty: '用完',
  broken: '损坏',
  missing: '找不到',
  idle: '闲置',
  archived: '归档',
}
</script>

<template>
  <span class="inline-flex items-center gap-2 text-[14px]">
    <span
      class="h-2 w-2 rounded-full"
      :class="status === 'normal' ? 'bg-teal' : status === 'low' ? 'bg-amber' : 'bg-slate-400'"
    ></span>
    {{ labels[status] || status }}
  </span>
</template>
