<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  Box,
  Grid2X2,
  Home,
  ListFilter,
  ListTodo,
  MapPinned,
  Plus,
  ScanLine,
  Settings,
  SlidersHorizontal,
  Wifi,
} from 'lucide-vue-next'

import DetailPanel from '@/components/panels/DetailPanel.vue'
import AttributesDialog from '@/components/dialogs/AttributesDialog.vue'
import DeleteItemDialog from '@/components/dialogs/DeleteItemDialog.vue'
import InventoryTable from '@/components/panels/InventoryTable.vue'
import ItemFormDialog from '@/components/dialogs/ItemFormDialog.vue'
import LocationFormDialog from '@/components/dialogs/LocationFormDialog.vue'
import LocationMap from '@/components/panels/LocationMap.vue'
import MoveItemDialog from '@/components/dialogs/MoveItemDialog.vue'
import QuantityDialog from '@/components/dialogs/QuantityDialog.vue'
import SettingsDialog from '@/components/dialogs/SettingsDialog.vue'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import TagsDialog from '@/components/dialogs/TagsDialog.vue'
import ItemThumb from '@/components/ui/ItemThumb.vue'
import StatusDot from '@/components/ui/StatusDot.vue'
import { useInventoryStore } from '@/stores/inventory'
import type { ItemFormPayload, LocationFormPayload, LocationNode } from '@/types'

const store = useInventoryStore()
const itemDialog = ref<'create' | 'edit' | null>(null)
const quantityDialog = ref<'add' | 'use' | null>(null)
const deleteDialogOpen = ref(false)
const settingsOpen = ref(false)
const tagsOpen = ref(false)
const attributesOpen = ref(false)
const locationDialog = ref<{ mode: 'create' | 'edit'; location: (LocationNode & { depth?: number }) | null } | null>(null)
const moveDialogOpen = ref(false)
const busy = ref(false)

const statusText = computed(() => {
  if (store.loading) return '正在同步数据'
  if (store.error) return '使用演示数据'
  return '数据同步于 10:24'
})

async function saveItem(payload: ItemFormPayload) {
  busy.value = true
  try {
    await store.saveItem(payload, itemDialog.value === 'edit' ? store.selectedItem?.code : undefined)
    itemDialog.value = null
  } finally {
    busy.value = false
  }
}

async function submitQuantity(amount: number, note: string) {
  busy.value = true
  try {
    if (quantityDialog.value === 'add') {
      await store.addQuantity(amount, note)
    } else {
      await store.useQuantity(amount, note)
    }
    quantityDialog.value = null
  } finally {
    busy.value = false
  }
}

async function deleteSelected(deleteAttachments: boolean) {
  busy.value = true
  try {
    await store.archiveSelected(deleteAttachments)
    deleteDialogOpen.value = false
  } finally {
    busy.value = false
  }
}

async function reloadWithFilters() {
  await store.loadItems()
}

async function toggleFavoriteFilter() {
  store.setFavoriteOnly(!store.favoriteOnly)
  await reloadWithFilters()
}

async function toggleRestockFilter() {
  store.setRestockOnly(!store.restockOnly)
  await reloadWithFilters()
}

async function toggleLowFilter() {
  store.setLowOnly(!store.lowOnly)
  await reloadWithFilters()
}

async function clearFilters() {
  store.clearFilters()
  await reloadWithFilters()
}

async function runBusy(action: () => Promise<void>) {
  busy.value = true
  try {
    await action()
  } catch (error) {
    window.alert(error instanceof Error ? error.message : '操作失败')
    throw error
  } finally {
    busy.value = false
  }
}

async function saveLocation(payload: LocationFormPayload) {
  await runBusy(async () => {
    await store.saveLocation(payload, locationDialog.value?.mode === 'edit' ? locationDialog.value.location?.id : undefined)
    locationDialog.value = null
  })
}

async function deleteLocation(location: LocationNode & { depth?: number }) {
  const confirmed = window.confirm(`删除位置「${location.name}」？如果位置下有子位置或物品，后端会拒绝删除。`)
  if (!confirmed) return
  await runBusy(() => store.deleteLocation(location.id))
}

async function moveSelected(locationCode: string | null, locationText: string | null) {
  await runBusy(async () => {
    await store.moveSelectedToLocation(locationCode, locationText)
    moveDialogOpen.value = false
  })
}
</script>

<template>
  <div class="min-h-screen bg-wash text-ink">
    <div class="flex min-h-screen flex-col lg:hidden">
      <header class="border-b border-line bg-white px-4 py-4">
        <div class="mb-4 flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="grid h-10 w-10 place-items-center rounded-[8px] border-2 border-ink">
              <Box :size="25" stroke-width="1.8" />
            </div>
            <div>
              <div class="text-[22px] font-semibold leading-6">工坊物栈</div>
              <div class="text-[13px] text-muted">Maker Stash</div>
            </div>
          </div>
          <button class="grid h-10 w-10 place-items-center rounded-[8px] border border-line" @click="settingsOpen = true">
            <Settings :size="20" />
          </button>
        </div>
        <div class="relative">
          <ListFilter class="absolute left-3 top-1/2 -translate-y-1/2 text-muted" :size="20" />
          <input
            :value="store.query"
            class="h-12 w-full rounded-[8px] border border-line bg-white pl-10 pr-3 text-[15px] outline-none focus:border-blue"
            placeholder="搜索物品、位置、标签..."
            @input="store.setQuery(($event.target as HTMLInputElement).value)"
            @keydown.enter="store.loadItems()"
          />
        </div>
      </header>
      <main class="thin-scrollbar flex-1 overflow-y-auto px-4 py-4">
        <div class="mb-4 flex gap-2 overflow-x-auto pb-1">
          <button
            class="shrink-0 rounded-[8px] border px-3 py-2 text-[14px] font-medium"
            :class="store.activeCategory === null ? 'border-blue bg-blue/10 text-blue' : 'border-line bg-white'"
            @click="store.setCategory(null); store.loadItems()"
          >
            全部
          </button>
          <button
            v-for="category in store.categories"
            :key="category.slug || 'all-mobile'"
            v-show="category.slug"
            class="shrink-0 rounded-[8px] border px-3 py-2 text-[14px] font-medium"
            :class="store.activeCategory === (category.slug || null) ? 'border-blue bg-blue/10 text-blue' : 'border-line bg-white'"
            @click="store.setCategory(category.slug || null); store.loadItems()"
          >
            {{ category.name }}
          </button>
        </div>
        <button
          v-for="item in store.items"
          :key="item.code"
          class="mb-3 w-full rounded-[8px] border border-line bg-white p-4 text-left shadow-sm"
          @click="store.selectItem(item.code)"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="flex min-w-0 items-center gap-3">
              <ItemThumb :item="item" />
              <div class="min-w-0">
                <div class="truncate text-[17px] font-semibold">{{ item.name }}</div>
                <div class="mt-1 text-[12px] text-muted">SKU: {{ item.code }}</div>
              </div>
            </div>
            <StatusDot :status="item.status" />
          </div>
          <div class="mt-3 flex items-center justify-between text-[14px]">
            <span class="text-muted">{{ item.location_text || '未记录位置' }}</span>
            <b>{{ item.quantity ?? '—' }} {{ item.unit }}</b>
          </div>
        </button>
        <div v-if="!store.items.length" class="rounded-[8px] border border-dashed border-line bg-white px-4 py-8 text-center text-[14px] text-muted">
          暂无匹配物品
        </div>
      </main>
      <nav class="grid h-16 grid-cols-5 border-t border-line bg-white text-[12px] text-muted">
        <button class="grid place-items-center text-blue"><Home :size="21" />物品</button>
        <button class="grid place-items-center" @click="store.setLocation(null); store.loadItems()"><MapPinned :size="21" />位置</button>
        <button class="grid place-items-center" @click="itemDialog = 'create'"><Plus :size="21" />新增</button>
        <button class="grid place-items-center" :class="store.restockOnly ? 'text-amber' : ''" @click="toggleRestockFilter"><ListTodo :size="21" />补货</button>
        <button class="grid place-items-center" @click="settingsOpen = true"><Settings :size="21" />设置</button>
      </nav>
    </div>

    <div class="hidden h-screen min-h-[680px] grid-cols-[clamp(190px,17vw,250px)_minmax(0,1fr)_clamp(280px,24vw,360px)] grid-rows-[80px_1fr] overflow-hidden lg:grid">
      <aside class="row-span-2 border-r border-line bg-panel">
        <div class="flex h-[80px] items-center gap-3 border-b border-line px-3 xl:px-4 2xl:px-6">
          <div class="grid h-10 w-10 shrink-0 place-items-center rounded-[8px] border-2 border-ink 2xl:h-11 2xl:w-11">
            <Box :size="26" stroke-width="1.8" />
          </div>
          <div class="min-w-0">
            <div class="truncate text-[22px] font-semibold leading-7 tracking-normal 2xl:text-[25px]">工坊物栈</div>
            <div class="mt-1 text-[14px] text-muted">Maker Stash</div>
          </div>
        </div>
        <SidebarNav />
        <div class="mx-4 mt-auto rounded-[8px] border border-line bg-white p-4 shadow-sm">
          <div class="mb-4 flex items-center justify-between">
            <span class="text-[15px] font-semibold">库存概览</span>
            <span class="grid h-5 w-5 place-items-center rounded-full border border-line text-[12px] text-muted">i</span>
          </div>
          <div class="space-y-3 text-[14px]">
            <div class="flex justify-between"><span class="text-muted">物品总数</span><b>{{ store.stats?.item_count ?? store.total }}</b></div>
            <div class="flex justify-between"><span class="text-muted">常用物品</span><b>{{ store.stats?.favorite_count ?? 0 }}</b></div>
            <div class="flex justify-between"><span class="text-muted">补货标记</span><b class="text-amber">{{ store.stats?.restock_count ?? 0 }}</b></div>
            <div class="flex justify-between"><span class="text-muted">附件数量</span><b class="text-teal">{{ store.stats?.attachment_count ?? 0 }}</b></div>
            <div class="flex justify-between"><span class="text-muted">未分类</span><b>{{ store.stats?.uncategorized_count ?? 0 }}</b></div>
            <div class="flex justify-between"><span class="text-muted">未定位</span><b>{{ store.stats?.unlocated_count ?? 0 }}</b></div>
          </div>
        </div>
        <div class="mx-4 mt-3 flex items-center justify-between rounded-[8px] border border-line bg-white px-4 py-3 text-[13px] text-muted">
          <span class="inline-flex items-center gap-2"><span class="h-2 w-2 rounded-full bg-teal"></span>{{ statusText }}</span>
          <span class="text-[18px]">↻</span>
        </div>
      </aside>

      <header class="col-span-2 flex min-w-0 items-center gap-2 border-b border-line bg-panel px-3 xl:gap-3 xl:px-4 2xl:gap-5 2xl:px-5">
        <div class="relative flex-1">
          <ListFilter class="absolute left-4 top-1/2 -translate-y-1/2 text-muted" :size="22" />
          <input
            :value="store.query"
            class="h-[54px] w-full rounded-[8px] border border-line bg-white pl-12 pr-4 text-[15px] outline-none transition focus:border-blue focus:ring-4 focus:ring-blue/10"
            placeholder="搜索物品、规格、位置、标签...  （⌘K）"
            @input="store.setQuery(($event.target as HTMLInputElement).value)"
            @keydown.enter="store.loadItems()"
          />
        </div>
        <button class="inline-flex h-[46px] shrink-0 items-center gap-2 rounded-[8px] border border-line bg-white px-3 text-[14px] font-medium hover:border-blue hover:text-blue 2xl:h-[54px] 2xl:px-5 2xl:text-[15px]" @click="itemDialog = 'create'">
          <Plus :size="21" /> 快速添加
        </button>
        <button class="hidden h-[46px] shrink-0 cursor-not-allowed items-center gap-2 rounded-[8px] border border-line bg-white px-3 text-[14px] font-medium text-slate-400 2xl:inline-flex 2xl:h-[54px] 2xl:px-5 2xl:text-[15px]" disabled title="扫码功能待接入硬件/摄像头权限">
          <ScanLine :size="21" /> 扫描
        </button>
        <button class="hidden h-[46px] shrink-0 cursor-not-allowed items-center gap-2 rounded-[8px] border border-line bg-white px-3 text-[14px] font-medium text-slate-400 2xl:inline-flex 2xl:h-[54px] 2xl:px-5 2xl:text-[15px]" disabled title="NFC 功能待接入浏览器/设备能力">
          <Wifi :size="21" /> NFC
        </button>
        <button class="inline-flex h-[46px] shrink-0 items-center gap-2 rounded-[8px] border border-line bg-white px-3 text-[14px] font-medium hover:border-blue hover:text-blue 2xl:h-[54px] 2xl:px-5 2xl:text-[15px]" @click="settingsOpen = true">
          <Settings :size="21" /> 设置
        </button>
      </header>

      <main class="flex min-h-0 min-w-0 flex-col overflow-hidden bg-panel">
        <div class="shrink-0 flex min-h-[56px] flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-2 2xl:px-5">
          <div class="flex h-full items-center gap-8 text-[16px] font-medium">
            <button class="relative h-full text-blue after:absolute after:bottom-0 after:left-0 after:h-[2px] after:w-full after:bg-blue">库存</button>
            <button class="h-full text-ink/80">位置</button>
            <button class="h-full text-ink/80">工作台</button>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <button class="inline-flex h-9 items-center gap-2 rounded-[6px] border border-blue/30 bg-blue/10 px-3 text-[14px] font-medium text-blue"><ListTodo :size="18" />列表</button>
            <button class="inline-flex h-9 cursor-not-allowed items-center gap-2 rounded-[6px] border border-line bg-white px-3 text-[14px] text-slate-400" disabled><Grid2X2 :size="17" />网格</button>
            <button class="h-9 rounded-[6px] border px-3 text-[13px]" :class="store.favoriteOnly ? 'border-blue bg-blue/10 text-blue' : 'border-line bg-white text-ink/80'" @click="toggleFavoriteFilter">常用</button>
            <button class="h-9 rounded-[6px] border px-3 text-[13px]" :class="store.restockOnly ? 'border-amber/40 bg-amber/10 text-amber' : 'border-line bg-white text-ink/80'" @click="toggleRestockFilter">补货</button>
            <button class="h-9 rounded-[6px] border px-3 text-[13px]" :class="store.lowOnly ? 'border-amber/40 bg-amber/10 text-amber' : 'border-line bg-white text-ink/80'" @click="toggleLowFilter">低库存</button>
            <button class="grid h-9 w-9 place-items-center rounded-[6px] border border-line bg-white text-ink/80" title="清除筛选" @click="clearFilters"><SlidersHorizontal :size="18" /></button>
          </div>
        </div>
        <div class="thin-scrollbar min-h-0 flex-1 overflow-y-auto">
          <InventoryTable />
          <LocationMap
            @create="(location) => locationDialog = { mode: 'create', location }"
            @edit="(location) => locationDialog = { mode: 'edit', location }"
            @delete="deleteLocation"
          />
        </div>
      </main>

      <aside class="min-h-0 min-w-0 overflow-hidden border-l border-line bg-panel">
        <DetailPanel
          @add-quantity="quantityDialog = 'add'"
          @use-quantity="quantityDialog = 'use'"
          @edit="itemDialog = 'edit'"
          @delete="deleteDialogOpen = true"
          @favorite="runBusy(() => store.toggleSelectedFavorite())"
          @restock="runBusy(() => store.toggleSelectedRestock())"
          @edit-tags="tagsOpen = true"
          @edit-attributes="attributesOpen = true"
          @move="moveDialogOpen = true"
          @upload-attachment="(file) => runBusy(() => store.uploadSelectedAttachment(file))"
          @delete-attachment="(id) => runBusy(() => store.deleteSelectedAttachment(id))"
        />
      </aside>
    </div>

    <div class="fixed bottom-5 right-[calc(clamp(280px,24vw,360px)+20px)] hidden gap-3 2xl:flex">
      <button class="grid h-11 w-11 place-items-center rounded-[8px] border border-line bg-white text-muted shadow-sm">−</button>
      <button class="grid h-11 w-11 place-items-center rounded-[8px] border border-line bg-white text-muted shadow-sm">＋</button>
      <button class="inline-flex h-11 items-center gap-2 rounded-[8px] border border-line bg-white px-4 text-[14px] font-medium text-ink shadow-sm">
        <MapPinned :size="17" /> 重置视图
      </button>
    </div>

    <ItemFormDialog
      :open="itemDialog !== null"
      :mode="itemDialog || 'create'"
      :item="itemDialog === 'edit' ? store.selectedItem : null"
      :busy="busy"
      @close="itemDialog = null"
      @submit="saveItem"
    />
    <QuantityDialog
      :open="quantityDialog !== null"
      :mode="quantityDialog || 'add'"
      :unit="store.selectedItem?.unit || null"
      :busy="busy"
      @close="quantityDialog = null"
      @submit="submitQuantity"
    />
    <DeleteItemDialog
      :open="deleteDialogOpen"
      :item="store.selectedItem"
      :attachment-count="store.selectedAttachments.length"
      :busy="busy"
      @close="deleteDialogOpen = false"
      @confirm="deleteSelected"
    />
    <SettingsDialog
      :open="settingsOpen"
      @close="settingsOpen = false"
      @saved="store.bootstrap()"
    />
    <TagsDialog
      :open="tagsOpen"
      :tags="store.selectedTags"
      :busy="busy"
      @close="tagsOpen = false"
      @add="(tags) => runBusy(() => store.addSelectedTags(tags))"
      @remove="(tag) => runBusy(() => store.removeSelectedTag(tag))"
    />
    <AttributesDialog
      :open="attributesOpen"
      :attributes="store.selectedAttributes"
      :busy="busy"
      @close="attributesOpen = false"
      @create="(payload) => runBusy(() => store.createSelectedAttribute(payload))"
      @update="(id, payload) => runBusy(() => store.updateSelectedAttribute(id, payload))"
      @remove="(id) => runBusy(() => store.deleteSelectedAttribute(id))"
    />
    <LocationFormDialog
      :open="locationDialog !== null"
      :mode="locationDialog?.mode || 'create'"
      :location="locationDialog?.location || null"
      :busy="busy"
      @close="locationDialog = null"
      @submit="saveLocation"
    />
    <MoveItemDialog
      :open="moveDialogOpen"
      :busy="busy"
      @close="moveDialogOpen = false"
      @submit="moveSelected"
    />
  </div>
</template>
