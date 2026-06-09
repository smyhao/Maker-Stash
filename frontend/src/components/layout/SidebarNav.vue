<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Boxes, Heart, Home, ListTodo, MapPinned, PackagePlus, Settings, Wrench } from 'lucide-vue-next'

import { EXTENSIONS_CHANGED_EVENT, fetchExtensions } from '@/api/extensions'
import { useInventoryStore } from '@/stores/inventory'
import type { ExtensionManifest } from '@/types'

const store = useInventoryStore()
const extensions = ref<ExtensionManifest[]>([])
const restockCount = computed(() => store.stats?.restock_count ?? 0)
const entries = [
  { route: 'home', label: '工作台', icon: Home },
  { route: 'items', label: '库存', icon: Boxes },
  { route: 'quick-entry', label: '连续录入', icon: PackagePlus },
  { route: 'locations', label: '位置', icon: MapPinned },
  { route: 'management', label: '管理', icon: Settings },
]

const toolExtensions = computed(() => extensions.value.flatMap((extension) => (
  extension.enabled
    ? extension.contributions
      .filter((contribution) => contribution.place === 'tools.menu' && contribution.action.startsWith('open-'))
      .map((contribution) => ({ extension, contribution }))
    : []
)))

async function loadExtensions() {
  try {
    const data = await fetchExtensions()
    extensions.value = data.extensions
  } catch {
    extensions.value = []
  }
}

onMounted(() => {
  loadExtensions()
  window.addEventListener(EXTENSIONS_CHANGED_EVENT, loadExtensions)
})
onBeforeUnmount(() => window.removeEventListener(EXTENSIONS_CHANGED_EVENT, loadExtensions))
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
    <template v-if="toolExtensions.length">
      <div class="mt-6 mb-3 px-3 text-[12px] font-medium uppercase tracking-[0.14em] text-muted">插件扩展</div>
      <RouterLink
        v-for="item in toolExtensions"
        :key="`${item.extension.id}:${item.contribution.action}`"
        v-slot="{ isActive }"
        :to="{ name: 'extension-tool', params: { extensionId: item.extension.id } }"
        class="mt-1"
      >
        <span class="flex h-12 items-center gap-3 rounded-xl px-3 text-[14px] font-medium transition" :class="isActive ? 'bg-green/12 text-green' : 'text-ink/75 hover:bg-white'">
          <Wrench :size="19" />{{ item.contribution.label }}
        </span>
      </RouterLink>
    </template>
  </nav>
</template>
