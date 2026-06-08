<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Grid2X2, ListFilter, ListTodo, Plus, QrCode, SlidersHorizontal, X } from 'lucide-vue-next'

import AttributesDialog from '@/components/dialogs/AttributesDialog.vue'
import DeleteItemDialog from '@/components/dialogs/DeleteItemDialog.vue'
import ItemFormDialog from '@/components/dialogs/ItemFormDialog.vue'
import LocationFormDialog from '@/components/dialogs/LocationFormDialog.vue'
import MoveItemDialog from '@/components/dialogs/MoveItemDialog.vue'
import QuantityDialog from '@/components/dialogs/QuantityDialog.vue'
import TagsDialog from '@/components/dialogs/TagsDialog.vue'
import CategoryFilter from '@/components/layout/CategoryFilter.vue'
import ExtensionHostView from '@/views/ExtensionHostView.vue'
import MobileBottomNav from '@/components/layout/MobileBottomNav.vue'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ExtensionSettingsPanel from '@/components/extensions/ExtensionSettingsPanel.vue'
import BackupManager from '@/components/panels/BackupManager.vue'
import CategoryManager from '@/components/panels/CategoryManager.vue'
import DetailPanel from '@/components/panels/DetailPanel.vue'
import HomeDashboard from '@/components/panels/HomeDashboard.vue'
import InventoryGrid from '@/components/panels/InventoryGrid.vue'
import InventoryTable from '@/components/panels/InventoryTable.vue'
import LocationMap from '@/components/panels/LocationMap.vue'
import LocationLabelManager from '@/components/panels/LocationLabelManager.vue'
import ManagementHub from '@/components/panels/ManagementHub.vue'
import QuickEntryPanel from '@/components/panels/QuickEntryPanel.vue'
import SettingsPanel from '@/components/panels/SettingsPanel.vue'
import BrandMark from '@/components/ui/BrandMark.vue'
import ItemThumb from '@/components/ui/ItemThumb.vue'
import StatusDot from '@/components/ui/StatusDot.vue'
import { fetchItems } from '@/api/items'
import { useInventoryStore } from '@/stores/inventory'
import type { Item, ItemFormPayload, LocationFormPayload, LocationNode } from '@/types'

type ScreenMode = 'home' | 'inventory' | 'quickEntry' | 'locations' | 'locationLabels' | 'management' | 'categories' | 'backups' | 'settings' | 'extensionSettings' | 'extension'

const store = useInventoryStore()
const route = useRoute()
const router = useRouter()
const itemDialog = ref<'create' | 'edit' | null>(null)
const quantityDialog = ref<'add' | 'use' | 'adjust' | null>(null)
const deleteDialogOpen = ref(false)
const tagsOpen = ref(false)
const attributesOpen = ref(false)
const locationDialog = ref<{ mode: 'create' | 'edit'; location: (LocationNode & { depth?: number }) | null } | null>(null)
const moveDialogOpen = ref(false)
const itemTargetLocation = ref<{ code: string; label: string } | null>(null)
const mobileDetailOpen = ref(false)
const busy = ref(false)
const notice = ref<{ type: 'error' | 'success'; message: string } | null>(null)
const inventoryView = ref<'list' | 'grid'>('list')
const searchFocused = ref(false)
const searchSuggestions = ref<Item[]>([])
const searchLoading = ref(false)
let searchTimer: number | null = null
let searchRequest = 0

const screenMode = computed<ScreenMode>(() => {
  switch (String(route.name || 'home')) {
    case 'home': return 'home'
    case 'quick-entry': return 'quickEntry'
    case 'locations': return 'locations'
    case 'location-labels': return 'locationLabels'
    case 'management': return 'management'
    case 'categories': return 'categories'
    case 'backups': return 'backups'
    case 'settings': return 'settings'
    case 'extension-settings': return 'extensionSettings'
    case 'extension-tool': return 'extension'
    default: return 'inventory'
  }
})
const showInventoryFilters = computed(() => screenMode.value === 'inventory')
const showDetailPanel = computed(() => screenMode.value === 'inventory')
const statusText = computed(() => {
  if (store.loading) return '正在同步数据'
  if (store.error) return '使用演示数据'
  return '数据已同步'
})

watch(
  () => route.name,
  (name) => {
    const routeName = String(name || 'home')
    if (routeName !== 'locations' && store.activeLocationCode) store.setLocation(null)
    store.setFavoriteOnly(routeName === 'favorites')
    store.setRestockOnly(routeName === 'restock')
    store.setLowOnly(false)
    mobileDetailOpen.value = false
    if ((store.items.length || store.categories.length) && routeName !== 'settings') void store.loadItems()
  },
  { immediate: true },
)

function showNotice(type: 'error' | 'success', message: string) {
  notice.value = { type, message }
}

async function runBusy(action: () => Promise<void>) {
  busy.value = true
  try {
    notice.value = null
    await action()
  } catch (error) {
    showNotice('error', error instanceof Error ? error.message : '操作失败')
  } finally {
    busy.value = false
  }
}

async function saveItem(payload: ItemFormPayload) {
  await runBusy(async () => {
    await store.saveItem(payload, itemDialog.value === 'edit' ? store.selectedItem?.code : undefined)
    itemDialog.value = null
    itemTargetLocation.value = null
  })
}

async function submitQuantity(amount: number, note: string) {
  await runBusy(async () => {
    if (quantityDialog.value === 'add') await store.addQuantity(amount, note)
    else if (quantityDialog.value === 'adjust') await store.adjustQuantity(amount, note)
    else await store.useQuantity(amount, note)
    quantityDialog.value = null
  })
}

async function deleteSelected(deleteAttachments: boolean) {
  await runBusy(async () => {
    await store.archiveSelected(deleteAttachments)
    deleteDialogOpen.value = false
  })
}

async function saveLocation(payload: LocationFormPayload) {
  await runBusy(async () => {
    await store.saveLocation(payload, locationDialog.value?.mode === 'edit' ? locationDialog.value.location?.id : undefined)
    locationDialog.value = null
  })
}

async function deleteLocation(location: LocationNode & { depth?: number }) {
  if (!window.confirm(`删除位置「${location.name}」？如果位置下有子位置或物品，后端会拒绝删除。`)) return
  await runBusy(() => store.deleteLocation(location.id))
}

async function moveSelected(locationCode: string | null, locationText: string | null) {
  await runBusy(async () => {
    await store.moveSelectedToLocation(locationCode, locationText)
    moveDialogOpen.value = false
  })
}

async function selectMobileItem(code: string) {
  await store.selectItem(code)
  mobileDetailOpen.value = true
}

function categoryName(item: Item) {
  return item.category_id ? store.categoryById.get(item.category_id)?.name || '未分类' : '未分类'
}

function clearSearchTimer() {
  if (searchTimer) {
    window.clearTimeout(searchTimer)
    searchTimer = null
  }
}

function handleSearchInput(value: string) {
  store.setQuery(value)
  clearSearchTimer()
  const query = value.trim()
  if (!query) {
    searchSuggestions.value = []
    searchLoading.value = false
    return
  }
  searchLoading.value = true
  searchTimer = window.setTimeout(() => {
    void loadSearchSuggestions(query)
  }, 180)
}

async function loadSearchSuggestions(query: string) {
  const requestId = ++searchRequest
  try {
    const data = await fetchItems({ q: query, page: 1, page_size: 6 })
    if (requestId !== searchRequest) return
    searchSuggestions.value = data.items
  } catch {
    if (requestId !== searchRequest) return
    searchSuggestions.value = []
  } finally {
    if (requestId === searchRequest) searchLoading.value = false
  }
}

async function submitSearch() {
  clearSearchTimer()
  searchFocused.value = false
  searchSuggestions.value = []
  await store.loadItems()
  if (screenMode.value !== 'inventory') await router.push({ name: 'items' })
}

async function chooseSearchSuggestion(item: Item) {
  clearSearchTimer()
  searchFocused.value = false
  searchSuggestions.value = []
  store.setCategory(null)
  store.setLocation(null)
  store.setFavoriteOnly(false)
  store.setRestockOnly(false)
  store.setLowOnly(false)
  store.setQuery(item.code)
  await router.push({ name: 'items' })
  await store.loadItems()
  await store.selectItem(item.code)
  mobileDetailOpen.value = true
}

function hideSearchSuggestionsSoon() {
  window.setTimeout(() => {
    searchFocused.value = false
  }, 120)
}

function openCreateItem() {
  itemTargetLocation.value = null
  itemDialog.value = 'create'
}

function openScan() {
  void router.push({ name: 'location-scan' })
}

function openCreateItemInSlot(code: string, label: string) {
  itemTargetLocation.value = { code, label }
  itemDialog.value = 'create'
}

async function reloadWithFilters() {
  await store.loadItems()
}
</script>

<template>
  <div class="min-h-screen bg-wash text-ink">
    <div class="flex h-screen min-h-0 flex-col overflow-hidden lg:hidden">
      <header class="border-b border-line bg-panel px-4 py-4">
        <div class="mb-4 flex items-center justify-between">
          <div class="flex items-center gap-3">
            <BrandMark />
            <div><div class="text-[21px] font-semibold leading-6">工坊物栈</div><div class="text-[12px] text-muted">Maker Stash</div></div>
          </div>
          <div class="flex gap-2">
            <button class="grid h-11 w-11 place-items-center rounded-xl border border-line bg-white text-green" title="扫码查看位置" @click="openScan"><QrCode :size="20" /></button>
            <button class="grid h-11 w-11 place-items-center rounded-xl bg-green text-white" title="新增物品" @click="openCreateItem"><Plus :size="20" /></button>
          </div>
        </div>
        <div class="relative">
          <ListFilter class="absolute left-3 top-1/2 -translate-y-1/2 text-muted" :size="19" />
          <input :value="store.query" class="h-12 w-full rounded-xl border border-line bg-white pl-10 pr-3 text-[14px] outline-none focus:border-green" placeholder="搜索物品、位置、标签..." @focus="searchFocused = true" @blur="hideSearchSuggestionsSoon" @input="handleSearchInput(($event.target as HTMLInputElement).value)" @keydown.enter="submitSearch" />
          <div v-if="searchFocused && (store.query || searchLoading || searchSuggestions.length)" class="absolute left-0 right-0 top-[54px] z-40 overflow-hidden rounded-2xl border border-line bg-white shadow-soft">
            <div v-if="searchLoading" class="px-4 py-3 text-[13px] text-muted">正在搜索...</div>
            <button
              v-for="item in searchSuggestions"
              :key="item.code"
              class="flex w-full items-center gap-3 px-3 py-3 text-left hover:bg-wash"
              @mousedown.prevent="chooseSearchSuggestion(item)"
            >
              <ItemThumb :item="item" compact />
              <span class="min-w-0 flex-1">
                <span class="block truncate text-[14px] font-medium">{{ item.name }}</span>
                <span class="mt-0.5 block truncate text-[12px] text-muted">{{ item.code }} · {{ categoryName(item) }} · {{ item.location_display || item.location_text || '未记录位置' }}</span>
              </span>
              <span class="shrink-0 text-[13px] font-medium">{{ item.quantity ?? '—' }} {{ item.unit || '' }}</span>
            </button>
            <div v-if="!searchLoading && store.query && !searchSuggestions.length" class="px-4 py-3 text-[13px] text-muted">暂无匹配物品</div>
          </div>
        </div>
      </header>
      <main class="min-h-0 flex-1" :class="screenMode === 'extension' ? 'h-full overflow-hidden pb-16' : 'thin-scrollbar overflow-y-auto pb-20'">
        <div v-if="notice" class="mx-4 mt-4 rounded-xl border px-3 py-2 text-[13px]" :class="notice.type === 'error' ? 'border-red-200 bg-red-50 text-red-700' : 'border-green/20 bg-green/10 text-green'">{{ notice.message }}</div>
        <LocationMap v-if="screenMode === 'locations'" @create="(location) => locationDialog = { mode: 'create', location }" @create-in-slot="openCreateItemInSlot" @edit="(location) => locationDialog = { mode: 'edit', location }" @delete="deleteLocation" />
        <LocationLabelManager v-else-if="screenMode === 'locationLabels'" />
        <HomeDashboard v-else-if="screenMode === 'home'" />
        <QuickEntryPanel v-else-if="screenMode === 'quickEntry'" />
        <ManagementHub v-else-if="screenMode === 'management'" />
        <CategoryManager v-else-if="screenMode === 'categories'" />
        <BackupManager v-else-if="screenMode === 'backups'" />
        <SettingsPanel v-else-if="screenMode === 'settings'" @saved="store.bootstrap()" />
        <ExtensionSettingsPanel v-else-if="screenMode === 'extensionSettings'" />
        <ExtensionHostView v-else-if="screenMode === 'extension'" />
        <section v-else class="p-4">
          <h2 class="mb-4 text-[24px] font-semibold">库存</h2>
          <div class="mb-4 flex gap-2 overflow-x-auto pb-1">
            <button class="shrink-0 rounded-xl border px-3 py-2 text-[13px]" :class="store.activeCategory === null ? 'border-green bg-green/10 text-green' : 'border-line bg-white'" @click="store.setCategory(null); store.loadItems()">全部</button>
            <button v-for="category in store.flatCategories" :key="category.id" class="shrink-0 rounded-xl border px-3 py-2 text-[13px]" :class="store.activeCategory === category.slug ? 'border-green bg-green/10 text-green' : 'border-line bg-white'" @click="store.setCategory(category.slug); store.loadItems()">{{ category.name }}</button>
          </div>
          <button v-for="item in store.items" :key="item.code" class="mb-3 w-full rounded-2xl border border-line bg-white p-4 text-left shadow-sm" @click="selectMobileItem(item.code)">
            <div class="flex items-start justify-between gap-3">
              <div class="flex min-w-0 items-center gap-3">
                <ItemThumb :item="item" />
                <div class="min-w-0"><div class="truncate text-[16px] font-semibold">{{ item.name }}</div><div class="mt-1 text-[12px] text-muted">{{ item.code }}</div></div>
              </div>
              <StatusDot :status="item.status" />
            </div>
            <div class="mt-3 flex justify-between text-[13px]"><span class="truncate text-muted">{{ item.location_display || item.location_text || '未记录位置' }}</span><b>{{ item.quantity ?? '—' }} {{ item.unit }}</b></div>
          </button>
        </section>
      </main>
      <MobileBottomNav />
    </div>

    <div class="hidden h-screen min-h-[680px] grid-cols-[214px_minmax(0,1fr)_clamp(300px,24vw,360px)] grid-rows-[76px_1fr] overflow-hidden lg:grid">
      <aside class="row-span-2 flex flex-col border-r border-line bg-nav">
        <div class="flex h-[76px] items-center gap-3 border-b border-line px-5">
          <BrandMark />
          <div class="min-w-0"><div class="truncate text-[20px] font-semibold">工坊物栈</div><div class="text-[12px] text-muted">Maker Stash</div></div>
        </div>
        <SidebarNav />
        <div class="m-4 rounded-xl border border-line bg-white/70 px-3 py-3 text-[12px] text-muted">
          <span class="inline-flex items-center gap-2"><span class="h-2 w-2 rounded-full bg-green"></span>{{ statusText }}</span>
        </div>
      </aside>

      <header class="col-span-2 flex min-w-0 items-center justify-center border-b border-line bg-panel px-5">
        <div class="flex w-full max-w-[860px] items-center gap-3">
          <div class="relative min-w-0 flex-1">
            <ListFilter class="absolute left-4 top-1/2 -translate-y-1/2 text-muted" :size="20" />
            <input :value="store.query" class="h-[50px] w-full rounded-xl border border-line bg-white pl-12 pr-4 text-[14px] outline-none transition focus:border-green focus:ring-4 focus:ring-green/10" placeholder="搜索物品、规格、位置、标签..." @focus="searchFocused = true" @blur="hideSearchSuggestionsSoon" @input="handleSearchInput(($event.target as HTMLInputElement).value)" @keydown.enter="submitSearch" />
            <div v-if="searchFocused && (store.query || searchLoading || searchSuggestions.length)" class="absolute left-0 right-0 top-[58px] z-40 overflow-hidden rounded-2xl border border-line bg-white shadow-soft">
              <div v-if="searchLoading" class="px-4 py-3 text-[13px] text-muted">正在搜索...</div>
              <button
                v-for="item in searchSuggestions"
                :key="item.code"
                class="flex w-full items-center gap-3 px-3 py-3 text-left hover:bg-wash"
                @mousedown.prevent="chooseSearchSuggestion(item)"
              >
                <ItemThumb :item="item" compact />
                <span class="min-w-0 flex-1">
                  <span class="block truncate text-[14px] font-medium">{{ item.name }}</span>
                  <span class="mt-0.5 block truncate text-[12px] text-muted">{{ item.code }} · {{ categoryName(item) }} · {{ item.location_display || item.location_text || '未记录位置' }}</span>
                </span>
                <span class="shrink-0 text-[13px] font-medium">{{ item.quantity ?? '—' }} {{ item.unit || '' }}</span>
              </button>
              <div v-if="!searchLoading && store.query && !searchSuggestions.length" class="px-4 py-3 text-[13px] text-muted">暂无匹配物品</div>
            </div>
          </div>
          <button class="grid h-[48px] w-[48px] shrink-0 place-items-center rounded-xl border border-line bg-white text-green" title="扫码查看位置" @click="openScan"><QrCode :size="18" /></button>
          <button class="inline-flex h-[48px] shrink-0 items-center gap-2 rounded-xl bg-green px-5 text-[14px] font-medium text-white" @click="openCreateItem"><Plus :size="18" /> 新增物品</button>
        </div>
      </header>

      <main class="flex min-h-0 min-w-0 flex-col overflow-hidden bg-panel" :class="showDetailPanel ? '' : 'col-span-2'">
        <div v-if="notice" class="shrink-0 border-b px-5 py-3 text-[13px]" :class="notice.type === 'error' ? 'border-red-200 bg-red-50 text-red-700' : 'border-green/20 bg-green/10 text-green'">{{ notice.message }}</div>
        <div v-if="showInventoryFilters" class="flex shrink-0 items-center justify-between border-b border-line px-5 py-4">
          <h2 class="text-[24px] font-semibold">库存</h2>
          <div class="flex gap-2">
            <button class="inline-flex h-9 items-center gap-2 rounded-xl border px-3 text-[13px]" :class="inventoryView === 'list' ? 'border-green bg-green/10 text-green' : 'border-line'" @click="inventoryView = 'list'"><ListTodo :size="16" />列表</button>
            <button class="inline-flex h-9 items-center gap-2 rounded-xl border px-3 text-[13px]" :class="inventoryView === 'grid' ? 'border-green bg-green/10 text-green' : 'border-line'" @click="inventoryView = 'grid'"><Grid2X2 :size="16" />网格</button>
            <button class="h-9 rounded-xl border px-3 text-[13px]" :class="store.favoriteOnly ? 'border-green bg-green/10 text-green' : 'border-line'" @click="store.setFavoriteOnly(!store.favoriteOnly); reloadWithFilters()">常用</button>
            <button class="h-9 rounded-xl border px-3 text-[13px]" :class="store.restockOnly ? 'border-clay bg-clay/10 text-clay' : 'border-line'" @click="store.setRestockOnly(!store.restockOnly); reloadWithFilters()">补货</button>
            <button class="h-9 rounded-xl border px-3 text-[13px]" :class="store.lowOnly ? 'border-clay bg-clay/10 text-clay' : 'border-line'" @click="store.setLowOnly(!store.lowOnly); reloadWithFilters()">低库存</button>
            <button class="grid h-9 w-9 place-items-center rounded-xl border border-line" title="清除筛选" @click="store.clearFilters(); reloadWithFilters()"><SlidersHorizontal :size="16" /></button>
          </div>
        </div>
        <div v-if="screenMode === 'inventory'" class="flex min-h-0 flex-1">
          <CategoryFilter />
          <div class="thin-scrollbar min-w-0 flex-1 overflow-y-auto">
            <InventoryTable v-if="inventoryView === 'list'" />
            <InventoryGrid v-else />
          </div>
        </div>
        <div v-else class="min-h-0 flex-1" :class="screenMode === 'extension' ? 'h-full overflow-hidden' : 'thin-scrollbar overflow-y-auto'">
          <LocationMap v-if="screenMode === 'locations'" @create="(location) => locationDialog = { mode: 'create', location }" @create-in-slot="openCreateItemInSlot" @edit="(location) => locationDialog = { mode: 'edit', location }" @delete="deleteLocation" />
          <LocationLabelManager v-else-if="screenMode === 'locationLabels'" />
          <HomeDashboard v-else-if="screenMode === 'home'" />
          <QuickEntryPanel v-else-if="screenMode === 'quickEntry'" />
          <ManagementHub v-else-if="screenMode === 'management'" />
          <CategoryManager v-else-if="screenMode === 'categories'" />
          <BackupManager v-else-if="screenMode === 'backups'" />
          <SettingsPanel v-else-if="screenMode === 'settings'" @saved="store.bootstrap()" />
          <ExtensionSettingsPanel v-else-if="screenMode === 'extensionSettings'" />
          <ExtensionHostView v-else-if="screenMode === 'extension'" />
        </div>
      </main>

      <aside v-if="showDetailPanel" class="min-h-0 min-w-0 overflow-hidden border-l border-line bg-white">
        <DetailPanel :allow-move="false" @add-quantity="quantityDialog = 'add'" @use-quantity="quantityDialog = 'use'" @adjust-quantity="quantityDialog = 'adjust'" @edit="itemDialog = 'edit'" @delete="deleteDialogOpen = true" @favorite="runBusy(() => store.toggleSelectedFavorite())" @restock="runBusy(() => store.toggleSelectedRestock())" @edit-tags="tagsOpen = true" @edit-attributes="attributesOpen = true" @upload-image="(file) => runBusy(() => store.uploadSelectedImage(file))" @upload-attachment="(file) => runBusy(() => store.uploadSelectedAttachment(file))" @delete-attachment="(id) => runBusy(() => store.deleteSelectedAttachment(id))" />
      </aside>
    </div>

    <div v-if="mobileDetailOpen && screenMode === 'inventory'" class="fixed inset-0 z-30 bg-ink/25 lg:hidden" @click.self="mobileDetailOpen = false">
      <section class="absolute inset-x-0 bottom-16 flex h-[78dvh] max-h-[calc(100dvh-5rem)] min-h-0 flex-col overflow-hidden rounded-t-3xl bg-white shadow-soft">
        <button class="absolute right-4 top-3 z-10 grid h-9 w-9 place-items-center rounded-full bg-wash" @click="mobileDetailOpen = false"><X :size="17" /></button>
        <DetailPanel @add-quantity="quantityDialog = 'add'" @use-quantity="quantityDialog = 'use'" @adjust-quantity="quantityDialog = 'adjust'" @edit="itemDialog = 'edit'" @delete="deleteDialogOpen = true" @favorite="runBusy(() => store.toggleSelectedFavorite())" @restock="runBusy(() => store.toggleSelectedRestock())" @edit-tags="tagsOpen = true" @edit-attributes="attributesOpen = true" @move="moveDialogOpen = true" @upload-image="(file) => runBusy(() => store.uploadSelectedImage(file))" @upload-attachment="(file) => runBusy(() => store.uploadSelectedAttachment(file))" @delete-attachment="(id) => runBusy(() => store.deleteSelectedAttachment(id))" />
      </section>
    </div>

    <ItemFormDialog :open="itemDialog !== null" :mode="itemDialog || 'create'" :item="itemDialog === 'edit' ? store.selectedItem : null" :location-code="itemTargetLocation?.code || null" :location-label="itemTargetLocation?.label || null" :busy="busy" @close="itemDialog = null; itemTargetLocation = null" @submit="saveItem" />
    <QuantityDialog :open="quantityDialog !== null" :mode="quantityDialog || 'add'" :unit="store.selectedItem?.unit || null" :busy="busy" @close="quantityDialog = null" @submit="submitQuantity" />
    <DeleteItemDialog :open="deleteDialogOpen" :item="store.selectedItem" :attachment-count="store.selectedAttachments.length" :busy="busy" @close="deleteDialogOpen = false" @confirm="deleteSelected" />
    <TagsDialog :open="tagsOpen" :tags="store.selectedTags" :busy="busy" @close="tagsOpen = false" @add="(tags) => runBusy(() => store.addSelectedTags(tags))" @remove="(tag) => runBusy(() => store.removeSelectedTag(tag))" />
    <AttributesDialog :open="attributesOpen" :attributes="store.selectedAttributes" :busy="busy" @close="attributesOpen = false" @create="(payload) => runBusy(() => store.createSelectedAttribute(payload))" @update="(id, payload) => runBusy(() => store.updateSelectedAttribute(id, payload))" @remove="(id) => runBusy(() => store.deleteSelectedAttribute(id))" />
    <LocationFormDialog :open="locationDialog !== null" :mode="locationDialog?.mode || 'create'" :location="locationDialog?.location || null" :busy="busy" @close="locationDialog = null" @submit="saveLocation" />
    <MoveItemDialog :open="moveDialogOpen" :busy="busy" @close="moveDialogOpen = false" @submit="moveSelected" />
  </div>
</template>
