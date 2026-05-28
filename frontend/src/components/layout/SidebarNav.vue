<script setup lang="ts">
import { computed } from 'vue'
import { Boxes, Heart, Home, ListTodo, MapPinned, Settings } from 'lucide-vue-next'

import { useInventoryStore } from '@/stores/inventory'

const store = useInventoryStore()
const restockCount = computed(() => store.stats?.restock_count ?? 0)
const entries = [
  { route: 'home', label: '工作台', icon: Home },
  { route: 'items', label: '库存', icon: Boxes },
  { route: 'locations', label: '位置', icon: MapPinned },
  { route: 'management', label: '管理', icon: Settings },
]
</script>

<template>
  <nav class="flex flex-1 flex-col px-3 py-6">
    <div class="mb-3 px-3 text-[12px] font-medium uppercase tracking-[0.14em] text-muted">主要任务</div>
    <RouterLink
      v-for="entry in entries"
      :key="entry.route"
      v-slot="{ isActive }"
      :to="{ name: entry.route }"
      class="mb-1 block"
    >
      <span class="flex h-12 items-center gap-3 rounded-xl px-3 text-[14px] font-medium transition" :class="isActive ? 'bg-green/12 text-green' : 'text-ink/75 hover:bg-white'">
        <component :is="entry.icon" :size="19" />
        {{ entry.label }}
      </span>
    </RouterLink>
    <div class="mt-6 mb-3 px-3 text-[12px] font-medium uppercase tracking-[0.14em] text-muted">快捷入口</div>
    <RouterLink v-slot="{ isActive }" :to="{ name: 'restock' }">
      <span class="flex h-12 items-center justify-between rounded-xl px-3 text-[14px] font-medium transition" :class="isActive ? 'bg-clay/10 text-clay' : 'text-ink/75 hover:bg-white'">
        <span class="inline-flex items-center gap-3"><ListTodo :size="19" />补货</span>
        <span v-if="restockCount" class="rounded-full bg-clay/12 px-2 py-0.5 text-[12px] text-clay">{{ restockCount }}</span>
      </span>
    </RouterLink>
    <RouterLink v-slot="{ isActive }" :to="{ name: 'favorites' }" class="mt-1">
      <span class="flex h-12 items-center gap-3 rounded-xl px-3 text-[14px] font-medium transition" :class="isActive ? 'bg-green/12 text-green' : 'text-ink/75 hover:bg-white'">
        <Heart :size="19" />常用物品
      </span>
    </RouterLink>
  </nav>
</template>
