<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Box, Cable, ChevronDown, ChevronRight, Cuboid, Hammer, Package, Shapes, Wrench } from 'lucide-vue-next'

import { useInventoryStore } from '@/stores/inventory'
import type { Category } from '@/types'

const store = useInventoryStore()
const expanded = ref(new Set<number>())
const initialized = ref(false)
const iconBySlug: Record<string, unknown> = {
  components: Cuboid,
  filament: Shapes,
  tools: Wrench,
  materials: Package,
  cables: Cable,
  others: Hammer,
}

const visibleCategories = computed(() => {
  const result: Array<Category & { depth: number }> = []
  const walk = (nodes: Category[], depth = 0) => {
    nodes.forEach((node) => {
      result.push({ ...node, depth })
      if (node.children?.length && expanded.value.has(node.id)) walk(node.children, depth + 1)
    })
  }
  walk(store.categories)
  return result
})

watch(
  () => store.categories,
  (categories) => {
    if (initialized.value || !categories.length) return
    const collectParents = (nodes: Category[]) => {
      nodes.forEach((category) => {
        if (category.children?.length) {
          expanded.value.add(category.id)
          collectParents(category.children)
        }
      })
    }
    collectParents(categories)
    initialized.value = true
  },
  { immediate: true },
)

function iconFor(category: Category) {
  return iconBySlug[category.slug] || Box
}

function choose(slug: string | null) {
  store.setCategory(slug)
  void store.loadItems()
}

function toggle(category: Category) {
  const next = new Set(expanded.value)
  if (next.has(category.id)) next.delete(category.id)
  else next.add(category.id)
  expanded.value = next
}
</script>

<template>
  <aside class="hidden w-[215px] shrink-0 border-r border-line bg-wash/60 p-3 xl:block">
    <div class="mb-3 px-2 text-[12px] font-medium uppercase tracking-[0.14em] text-muted">分类</div>
    <button class="mb-1 flex h-11 w-full items-center justify-between rounded-xl px-2 text-[13px]" :class="store.activeCategory === null ? 'bg-green/12 text-green' : 'hover:bg-white'" @click="choose(null)">
      <span class="inline-flex items-center gap-2"><Box :size="16" />全部</span>
      <span class="text-muted">{{ store.stats?.item_count ?? store.total }}</span>
    </button>
    <div
      v-for="category in visibleCategories"
      :key="category.id"
      class="mb-1 flex h-11 w-full items-center rounded-xl text-[13px]"
      :class="store.activeCategory === category.slug ? 'bg-green/12 text-green' : 'hover:bg-white'"
      :style="{ paddingLeft: `${8 + category.depth * 14}px` }"
    >
      <button class="flex min-w-0 flex-1 items-center gap-2 text-left" @click="choose(category.slug)">
        <component :is="iconFor(category)" :size="16" class="shrink-0" />
        <span class="truncate">{{ category.name }}</span>
      </button>
      <span class="mr-1 text-muted">{{ store.categoryCounts.get(category.id) || 0 }}</span>
      <button
        v-if="category.children?.length"
        class="mr-1 grid h-7 w-7 shrink-0 place-items-center rounded-md text-muted hover:bg-green/10 hover:text-green"
        :title="expanded.has(category.id) ? '收起子分类' : '展开子分类'"
        @click.stop="toggle(category)"
      >
        <ChevronDown v-if="expanded.has(category.id)" :size="15" />
        <ChevronRight v-else :size="15" />
      </button>
      <span v-else class="w-8 shrink-0"></span>
    </div>
  </aside>
</template>
