<script setup lang="ts">
import { Box, Cable, Cuboid, Hammer, Package, Shapes, Wrench } from 'lucide-vue-next'

import { useInventoryStore } from '@/stores/inventory'
import type { Category } from '@/types'

const store = useInventoryStore()

const iconBySlug: Record<string, unknown> = {
  components: Cuboid,
  filament: Shapes,
  tools: Wrench,
  materials: Package,
  cables: Cable,
  others: Hammer,
}

function iconFor(category: Category) {
  return iconBySlug[category.slug] || Box
}

function countFor(category: Category) {
  return store.categoryCounts.get(category.id) || 0
}
</script>

<template>
  <nav class="flex h-[calc(100%-300px)] min-h-[420px] flex-col px-3 py-5">
    <div class="mb-4 px-3 text-[13px] text-muted">物品类型</div>
    <button
      class="mb-2 flex h-[54px] items-center justify-between rounded-[8px] px-3 text-[15px] transition"
      :class="store.activeCategory === null ? 'bg-blue/10 text-blue' : 'text-ink hover:bg-slate-50'"
      @click="store.setCategory(null); store.loadItems()"
    >
      <span class="flex items-center gap-3">
        <Box :size="22" stroke-width="1.8" />
        <b class="font-semibold">全部</b>
      </span>
      <span class="text-[14px]" :class="store.activeCategory === null ? 'text-blue' : 'text-muted'">
        {{ store.stats?.item_count ?? store.total }}
      </span>
    </button>
    <button
      v-for="category in store.flatCategories"
      :key="category.id"
      class="mb-2 flex h-[54px] items-center justify-between rounded-[8px] px-3 text-[15px] transition"
      :class="store.activeCategory === category.slug ? 'bg-blue/10 text-blue' : 'text-ink hover:bg-slate-50'"
      :style="{ paddingLeft: `${12 + category.depth * 16}px` }"
      @click="store.setCategory(category.slug); store.loadItems()"
    >
      <span class="flex items-center gap-3">
        <component :is="iconFor(category)" :size="22" stroke-width="1.8" />
        <b class="font-semibold">{{ category.name }}</b>
      </span>
      <span class="text-[14px]" :class="store.activeCategory === category.slug ? 'text-blue' : 'text-muted'">
        {{ countFor(category) }}
      </span>
    </button>
  </nav>
</template>
