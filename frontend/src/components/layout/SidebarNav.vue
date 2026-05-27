<script setup lang="ts">
import { computed, ref } from 'vue'
import { Box, Cable, ChevronDown, ChevronRight, Cuboid, Hammer, Package, Shapes, Wrench } from 'lucide-vue-next'

import { useInventoryStore } from '@/stores/inventory'
import type { Category } from '@/types'

const store = useInventoryStore()
const collapsedCategoryIds = ref<Set<number>>(new Set())

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

function countFor(category: Category): number {
  return (store.categoryCounts.get(category.id) || 0)
    + (category.children || []).reduce<number>((total, child) => total + countFor(child), 0)
}

function hasChildren(category: Category) {
  return Boolean(category.children?.some((child) => child.slug))
}

function isCollapsed(category: Category) {
  return collapsedCategoryIds.value.has(category.id)
}

function toggleCategory(category: Category) {
  const next = new Set(collapsedCategoryIds.value)
  if (next.has(category.id)) {
    next.delete(category.id)
  } else {
    next.add(category.id)
  }
  collapsedCategoryIds.value = next
}

const visibleCategories = computed(() => {
  const result: Array<Category & { depth: number }> = []

  function walk(categories: Category[], depth = 0) {
    categories.forEach((category) => {
      if (!category.slug) return
      result.push({ ...category, depth })
      if (!isCollapsed(category)) {
        walk(category.children || [], depth + 1)
      }
    })
  }

  walk(store.categories)
  return result
})
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
      <div
        v-for="category in visibleCategories"
        :key="category.id"
        class="mb-2 flex h-[54px] items-center justify-between rounded-[8px] px-3 text-[15px] transition"
        :class="store.activeCategory === category.slug ? 'bg-blue/10 text-blue' : 'text-ink hover:bg-slate-50'"
        :style="{ paddingLeft: `${8 + category.depth * 18}px` }"
        role="button"
        tabindex="0"
        @click="store.setCategory(category.slug); store.loadItems()"
        @keydown.enter.prevent="store.setCategory(category.slug); store.loadItems()"
        @keydown.space.prevent="store.setCategory(category.slug); store.loadItems()"
      >
        <span class="flex min-w-0 items-center gap-2">
          <span class="grid h-6 w-6 shrink-0 place-items-center" @click.stop @keydown.stop>
            <button
              v-if="hasChildren(category)"
              type="button"
              class="grid h-6 w-6 place-items-center rounded-[6px] hover:bg-white/70"
              :aria-label="isCollapsed(category) ? `展开${category.name}` : `收起${category.name}`"
              @click="toggleCategory(category)"
            >
              <component :is="isCollapsed(category) ? ChevronRight : ChevronDown" :size="16" stroke-width="2.2" />
            </button>
          </span>
          <component :is="iconFor(category)" :size="22" stroke-width="1.8" />
          <b class="truncate font-semibold">{{ category.name }}</b>
        </span>
        <span class="shrink-0 text-[14px]" :class="store.activeCategory === category.slug ? 'text-blue' : 'text-muted'">
          {{ countFor(category) }}
        </span>
      </div>
  </nav>
</template>
