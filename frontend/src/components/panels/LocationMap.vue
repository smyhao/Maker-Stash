<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowDownToLine, Boxes, ChevronRight, Container, Grid2X2, MapPinned, Paperclip, Pencil, Plus, Printer, ScrollText, Trash2, X } from 'lucide-vue-next'

import { convertLocationToContainer, fetchContainerBoard, fetchLocationItems, swapContainerSlots } from '@/api/catalog'
import { downloadAttachmentFile, fetchItem, fetchItemAttachments, fetchItemAttributes, fetchItems, moveItem } from '@/api/items'
import ContainerFormDialog from '@/components/dialogs/ContainerFormDialog.vue'
import ItemThumb from '@/components/ui/ItemThumb.vue'
import StatusDot from '@/components/ui/StatusDot.vue'
import { useInventoryStore } from '@/stores/inventory'
import type { Attachment, ContainerBoard, ContainerBoardSlot, ContainerCreatePayload, ContainerLayoutPayload, Item, ItemAttribute, LocationNode, SlotAssignment } from '@/types'

const store = useInventoryStore()
const router = useRouter()
const emit = defineEmits<{
  create: [parent: (LocationNode & { depth?: number }) | null]
  createInSlot: [locationCode: string, locationLabel: string]
  edit: [location: LocationNode & { depth?: number }]
  delete: [location: LocationNode & { depth?: number }]
}>()

const board = ref<ContainerBoard | null>(null)
const boardLoading = ref(false)
const message = ref<{ type: 'success' | 'error'; text: string } | null>(null)
const containerDialog = ref<'create' | 'convert' | 'edit' | null>(null)
const dialogLocation = ref<LocationNode | null>(null)
const busy = ref(false)
const arranging = ref(false)
const sourceSlot = ref<ContainerBoardSlot | null>(null)
const targetSlot = ref<ContainerBoardSlot | null>(null)
const selectedSlot = ref<ContainerBoardSlot | null>(null)
const slotDetailItem = ref<Item | null>(null)
const slotAttributes = ref<ItemAttribute[]>([])
const slotAttachments = ref<Attachment[]>([])
const slotDetailLoading = ref(false)
const slotDetailError = ref<string | null>(null)
const directItems = ref<import('@/types').Item[]>([])
const isMobile = ref(false)
const pickerOpen = ref(false)
const pickerQuery = ref('')
const pickerItems = ref<Item[]>([])
const pickerLoading = ref(false)
const pickerSlot = ref<ContainerBoardSlot | null>(null)
const pdfPreviewAttachment = ref<Attachment | null>(null)
const pdfPreviewUrl = ref<string | null>(null)
let media: MediaQueryList | null = null
let slotDetailRequest = 0
let pickerRequest = 0
let messageTimer: number | null = null

const PRESET_COLORS: Record<string, string> = {
  sage: '#5F7F67',
  clay: '#C56A45',
  sand: '#C9AD7A',
  ink: '#29313A',
}

const activeLocation = computed(() => store.flatLocations.find((location) => location.full_code === store.activeLocationCode) || null)
const visibleLocations = computed(() => store.flatLocations.filter((location) => !location.is_slot))
const isContainer = computed(() => Boolean(activeLocation.value?.layout_type))
const occupancy = computed(() => board.value?.slots.filter((slot) => slot.item).length || 0)
const gridColumns = computed(() => board.value?.container.layout_columns || 1)
const ordinaryItems = computed(() => (isContainer.value ? [] : directItems.value))
const actionSlot = computed(() => targetSlot.value || selectedSlot.value || sourceSlot.value)
const slotCategory = computed(() => (slotDetailItem.value?.category_id ? store.categoryById.get(slotDetailItem.value.category_id)?.name : '未分类'))
const slotLocation = computed(() => slotDetailItem.value?.location_display || slotDetailItem.value?.location_text || actionSlot.value?.location.full_code || '未记录')
const slotDocumentAttachments = computed(() => slotAttachments.value.filter((attachment) => !isCoverAttachment(attachment)))

function updateMobile(event?: MediaQueryListEvent) {
  isMobile.value = event ? event.matches : Boolean(media?.matches)
}

onMounted(() => {
  media = window.matchMedia('(max-width: 1023px)')
  updateMobile()
  media.addEventListener('change', updateMobile)
})

onBeforeUnmount(() => {
  media?.removeEventListener('change', updateMobile)
  clearMessageTimer()
  closePdfPreview()
})

function clearMessageTimer() {
  if (messageTimer) {
    window.clearTimeout(messageTimer)
    messageTimer = null
  }
}

watch(
  () => store.locations,
  () => {
    const current = activeLocation.value
    const initial = visibleLocations.value.find((location) => location.layout_type) || visibleLocations.value[0]
    if (current || initial) void selectLocation(current || initial)
  },
  { immediate: true },
)

watch(message, (value) => {
  clearMessageTimer()
  if (!value) return
  messageTimer = window.setTimeout(() => {
    message.value = null
    messageTimer = null
  }, 2000)
})

async function loadBoard(location: LocationNode) {
  boardLoading.value = true
  try {
    board.value = await fetchContainerBoard(location.id)
  } catch (error) {
    message.value = { type: 'error', text: error instanceof Error ? error.message : '格位加载失败' }
    board.value = null
  } finally {
    boardLoading.value = false
  }
}

async function selectLocation(location: LocationNode & { depth?: number }) {
  store.setLocation(location.full_code)
  sourceSlot.value = null
  targetSlot.value = null
  selectedSlot.value = null
  clearSlotDetail()
  arranging.value = false
  if (location.layout_type) {
    directItems.value = []
    await loadBoard(location)
  } else {
    board.value = null
    try {
      const data = await fetchLocationItems(location.id)
      directItems.value = data.items
      await store.loadItems()
    } catch (error) {
      directItems.value = []
      message.value = { type: 'error', text: error instanceof Error ? error.message : '位置内容加载失败' }
    }
  }
}

function containerLabel(location: LocationNode) {
  if (!location.layout_type) return location.type || '普通位置'
  if (location.layout_type === 'row') return `单排 · ${location.layout_columns} 格`
  return `${location.layout_rows} x ${location.layout_columns} · 收纳盒`
}

function resolveColor(value?: string | null) {
  if (!value) return PRESET_COLORS.sage
  if (PRESET_COLORS[value]) return PRESET_COLORS[value]
  return /^#[0-9A-Fa-f]{6}$/.test(value) ? value.toUpperCase() : PRESET_COLORS.sage
}

function withAlpha(hex: string, alpha: number) {
  const normalized = resolveColor(hex).slice(1)
  const red = parseInt(normalized.slice(0, 2), 16)
  const green = parseInt(normalized.slice(2, 4), 16)
  const blue = parseInt(normalized.slice(4, 6), 16)
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`
}

function locationColorStyle(location: LocationNode) {
  if (!location.layout_type) return {}
  const color = resolveColor(location.appearance_color)
  return {
    borderLeft: `4px solid ${color}`,
    backgroundColor: withAlpha(color, store.activeLocationCode === location.full_code ? 0.12 : 0.05),
  }
}

function boardStyle(location: LocationNode) {
  const color = resolveColor(location.appearance_color)
  return {
    backgroundColor: withAlpha(color, 0.08),
    borderColor: withAlpha(color, 0.28),
    gridTemplateColumns: `repeat(${gridColumns.value}, minmax(0, 1fr))`,
  }
}

function openContainer(mode: 'create' | 'convert' | 'edit', location: LocationNode | null) {
  dialogLocation.value = location
  containerDialog.value = mode
}

function printLocationLabels(location: LocationNode, scope: 'container' | 'slots' | 'all' = 'container') {
  const route = router.resolve({ name: 'location-label-print', query: { id: String(location.id), scope } })
  window.open(route.href, '_blank')
}

async function createContainer(payload: ContainerCreatePayload) {
  busy.value = true
  try {
    await store.saveContainer(payload)
    containerDialog.value = null
    const created = store.flatLocations.find((location) => location.full_code === `${payload.parent_code ? `${payload.parent_code}.` : ''}${payload.code}`)
    if (created) await selectLocation(created)
    message.value = { type: 'success', text: '收纳盒及格位已创建' }
  } catch (error) {
    message.value = { type: 'error', text: error instanceof Error ? error.message : '创建收纳盒失败' }
  } finally {
    busy.value = false
  }
}

async function convertContainer(id: number, payload: ContainerLayoutPayload & { assignments: SlotAssignment[] }) {
  busy.value = true
  try {
    await convertLocationToContainer(id, payload)
    await store.bootstrap()
    const location = store.flatLocations.find((entry) => entry.id === id)
    if (location) await selectLocation(location)
    containerDialog.value = null
    message.value = { type: 'success', text: '位置已配置为可视化收纳盒' }
  } catch (error) {
    message.value = { type: 'error', text: error instanceof Error ? error.message : '配置收纳盒失败' }
  } finally {
    busy.value = false
  }
}

async function updateLayout(id: number, payload: ContainerLayoutPayload) {
  busy.value = true
  try {
    await store.resizeContainer(id, payload)
    const location = store.flatLocations.find((entry) => entry.id === id)
    if (location) await loadBoard(location)
    containerDialog.value = null
    message.value = { type: 'success', text: '收纳盒布局已保存' }
  } catch (error) {
    message.value = { type: 'error', text: error instanceof Error ? error.message : '布局保存失败' }
  } finally {
    busy.value = false
  }
}

function chooseSlot(slot: ContainerBoardSlot) {
  selectedSlot.value = slot
  if (isMobile.value || !arranging.value) return
  if (!sourceSlot.value) {
    if (slot.item) sourceSlot.value = slot
    return
  }
  if (slot.location.id !== sourceSlot.value.location.id) targetSlot.value = slot
}

function clearSlotDetail() {
  slotDetailRequest += 1
  slotDetailItem.value = null
  slotAttributes.value = []
  slotAttachments.value = []
  slotDetailLoading.value = false
  slotDetailError.value = null
}

async function loadSlotDetail(slot: ContainerBoardSlot | null) {
  if (!slot?.item || arranging.value) {
    clearSlotDetail()
    return
  }
  const requestId = ++slotDetailRequest
  slotDetailItem.value = slot.item
  slotAttributes.value = []
  slotAttachments.value = []
  slotDetailError.value = null
  slotDetailLoading.value = true
  try {
    const [item, attributes, attachments] = await Promise.all([
      fetchItem(slot.item.code),
      fetchItemAttributes(slot.item.code),
      fetchItemAttachments(slot.item.code),
    ])
    if (requestId !== slotDetailRequest) return
    slotDetailItem.value = item
    slotAttributes.value = attributes.attributes
    slotAttachments.value = attachments.attachments.filter((attachment) => !attachment.is_deleted)
  } catch (error) {
    if (requestId !== slotDetailRequest) return
    slotDetailError.value = error instanceof Error ? error.message : '物品详情加载失败'
  } finally {
    if (requestId === slotDetailRequest) slotDetailLoading.value = false
  }
}

watch(
  () => [selectedSlot.value?.item?.code || null, arranging.value] as const,
  () => {
    void loadSlotDetail(selectedSlot.value)
  },
)

function formatBytes(bytes: number | null) {
  if (!bytes && bytes !== 0) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function isCoverAttachment(attachment: Attachment) {
  return attachment.is_cover || attachment.id === slotDetailItem.value?.cover_attachment_id
}

async function downloadAttachment(attachment: Attachment) {
  const blob = await downloadAttachmentFile(attachment.id)
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = attachment.original_name
  link.click()
  URL.revokeObjectURL(url)
}

function canPreviewAttachment(attachment: Attachment) {
  return attachment.mime_type === 'application/pdf' || attachment.original_name.toLowerCase().endsWith('.pdf')
}

async function previewAttachment(attachment: Attachment) {
  try {
    const blob = await downloadAttachmentFile(attachment.id)
    const previewBlob = blob.type === 'application/pdf' ? blob : new Blob([blob], { type: 'application/pdf' })
    const url = URL.createObjectURL(previewBlob)
    closePdfPreview()
    pdfPreviewAttachment.value = attachment
    pdfPreviewUrl.value = url
  } catch {
    window.alert('附件预览失败，请下载后查看。')
  }
}

function closePdfPreview() {
  if (pdfPreviewUrl.value) URL.revokeObjectURL(pdfPreviewUrl.value)
  pdfPreviewUrl.value = null
  pdfPreviewAttachment.value = null
}

function startArrange(slot?: ContainerBoardSlot) {
  if (arranging.value && !slot) {
    arranging.value = false
    sourceSlot.value = null
    targetSlot.value = null
    selectedSlot.value = null
    return
  }
  arranging.value = true
  sourceSlot.value = slot?.item ? slot : null
  targetSlot.value = null
  selectedSlot.value = slot || null
}

async function confirmArrange() {
  if (!board.value || !sourceSlot.value?.item || !targetSlot.value) return
  busy.value = true
  try {
    if (targetSlot.value.item) {
      await swapContainerSlots(board.value.container.id, sourceSlot.value.item.code, targetSlot.value.location.slot_key || '')
      message.value = { type: 'success', text: `已交换 ${sourceSlot.value.location.slot_key} 与 ${targetSlot.value.location.slot_key}` }
    } else {
      await moveItem(sourceSlot.value.item.code, targetSlot.value.location.full_code, null, `整理至 ${targetSlot.value.location.slot_key}`)
      message.value = { type: 'success', text: `已移动到 ${targetSlot.value.location.slot_key}` }
    }
    await loadBoard(board.value.container)
    await store.refreshStats()
    sourceSlot.value = null
    targetSlot.value = null
    selectedSlot.value = null
  } catch (error) {
    message.value = { type: 'error', text: error instanceof Error ? error.message : '整理操作失败' }
  } finally {
    busy.value = false
  }
}

async function removeSelectedFromSlot() {
  if (!board.value || !selectedSlot.value?.item || isMobile.value || arranging.value) return
  const item = selectedSlot.value.item
  const slotKey = selectedSlot.value.location.slot_key
  busy.value = true
  try {
    await moveItem(item.code, null, null, `移出格位 ${slotKey}`)
    await loadBoard(board.value.container)
    await store.refreshStats()
    selectedSlot.value = null
    message.value = { type: 'success', text: `${item.name} 已移出格位` }
  } catch (error) {
    message.value = { type: 'error', text: error instanceof Error ? error.message : '移出格位失败' }
  } finally {
    busy.value = false
  }
}

async function placeSelectedItem(slot: ContainerBoardSlot) {
  if (!store.selectedItem || slot.item || isMobile.value) return
  busy.value = true
  try {
    await moveItem(store.selectedItem.code, slot.location.full_code, null, `放入格位 ${slot.location.slot_key}`)
    if (board.value) await loadBoard(board.value.container)
    selectedSlot.value = null
    message.value = { type: 'success', text: `${store.selectedItem.name} 已放入 ${slot.location.slot_key}` }
  } catch (error) {
    message.value = { type: 'error', text: error instanceof Error ? error.message : '放置物品失败' }
  } finally {
    busy.value = false
  }
}

async function openItemPicker(slot: ContainerBoardSlot) {
  if (slot.item || isMobile.value) return
  pickerSlot.value = slot
  pickerOpen.value = true
  pickerQuery.value = ''
  await loadPickerItems()
}

async function loadPickerItems() {
  const requestId = ++pickerRequest
  pickerLoading.value = true
  try {
    const data = await fetchItems({
      q: pickerQuery.value.trim() || undefined,
      page: 1,
      page_size: 20,
    })
    if (requestId !== pickerRequest) return
    pickerItems.value = data.items.filter((item) => !item.is_archived && item.location_id !== pickerSlot.value?.location.id)
  } catch {
    if (requestId !== pickerRequest) return
    pickerItems.value = []
  } finally {
    if (requestId === pickerRequest) pickerLoading.value = false
  }
}

async function placePickedItem(item: Item) {
  if (!pickerSlot.value || pickerSlot.value.item || isMobile.value) return
  busy.value = true
  try {
    await moveItem(item.code, pickerSlot.value.location.full_code, null, `放入格位 ${pickerSlot.value.location.slot_key}`)
    if (board.value) await loadBoard(board.value.container)
    selectedSlot.value = null
    pickerOpen.value = false
    pickerSlot.value = null
    message.value = { type: 'success', text: `${item.name} 已放入格位` }
  } catch (error) {
    message.value = { type: 'error', text: error instanceof Error ? error.message : '放置物品失败' }
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="min-w-0 overflow-x-hidden p-4 2xl:p-6">
    <div class="mb-5 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-[25px] font-semibold tracking-tight">位置</h2>
        <p class="mt-1 text-[14px] text-muted">按实物格位定位与整理物品</p>
      </div>
      <div class="hidden gap-2 lg:flex">
        <button class="h-10 rounded-xl border border-line bg-white px-4 text-[14px]" @click="emit('create', null)">新增位置</button>
        <button class="inline-flex h-10 items-center gap-2 rounded-xl bg-green px-4 text-[14px] font-medium text-white" @click="openContainer('create', activeLocation)">
          <Plus :size="16" /> 新建收纳盒
        </button>
      </div>
    </div>

    <div v-if="isMobile" class="mb-4 rounded-xl border border-line bg-white px-4 py-3 text-[13px] text-muted">
      查看实物格位，整理请使用桌面端。
    </div>
    <div v-if="message" class="mb-4 rounded-xl border px-4 py-3 text-[13px]" :class="message.type === 'error' ? 'border-red-200 bg-red-50 text-red-700' : 'border-green/20 bg-green/10 text-green'">
      {{ message.text }}
    </div>

    <div class="grid min-w-0 gap-4 xl:grid-cols-[255px_minmax(400px,1fr)_300px]">
      <aside class="rounded-2xl border border-line bg-white p-3">
        <div class="mb-3 px-2 text-[13px] font-medium text-muted">收纳位置</div>
        <button
          v-for="location in visibleLocations"
          :key="location.id"
          class="mb-1 w-full rounded-xl px-3 py-3 text-left"
          :class="store.activeLocationCode === location.full_code ? 'bg-green/10 text-green' : 'hover:bg-wash'"
          :style="{ ...locationColorStyle(location), paddingLeft: `${12 + (location.depth || 0) * 14}px` }"
          @click="selectLocation(location)"
        >
          <span class="flex items-start gap-2">
            <Grid2X2 v-if="location.layout_type === 'grid'" :size="17" class="mt-0.5 shrink-0" />
            <Container v-else-if="location.layout_type === 'row'" :size="17" class="mt-0.5 shrink-0" />
            <Boxes v-else :size="17" class="mt-0.5 shrink-0" />
            <span class="min-w-0">
              <span class="block truncate text-[14px] font-medium">{{ location.name }}</span>
              <span class="mt-0.5 block truncate text-[12px] text-muted">
                {{ containerLabel(location) }}<template v-if="location.layout_type"> · 查看格位</template>
              </span>
            </span>
          </span>
        </button>
      </aside>

      <main class="min-w-0 overflow-hidden rounded-2xl border border-line bg-white p-4 lg:p-5">
        <template v-if="board">
          <div class="mb-5 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 class="text-[21px] font-semibold">{{ board.container.name }}</h3>
              <p class="mt-1 text-[13px] text-muted">{{ board.container.full_code }} · {{ containerLabel(board.container) }} · {{ occupancy }} / {{ board.slots.length }} 已占用</p>
            </div>
            <div class="hidden gap-2 lg:flex">
              <button class="inline-flex h-9 items-center gap-2 rounded-xl border border-line px-3 text-[13px]" @click="printLocationLabels(board.container)">
                <Printer :size="15" />容器标签
              </button>
              <button class="inline-flex h-9 items-center gap-2 rounded-xl border border-line px-3 text-[13px]" @click="printLocationLabels(board.container, 'all')">
                <Printer :size="15" />全部格位
              </button>
              <button class="h-9 rounded-xl border px-3 text-[13px]" :class="arranging ? 'border-green bg-green/10 text-green' : 'border-line'" @click="startArrange()">
                {{ arranging ? '整理中' : '整理模式' }}
              </button>
              <button class="h-9 rounded-xl border border-line px-3 text-[13px]" @click="openContainer('edit', board.container)">编辑布局</button>
              <button class="grid h-9 w-9 place-items-center rounded-xl border border-red-200 text-red-600" title="删除收纳盒" @click="emit('delete', board.container)">
                <Trash2 :size="15" />
              </button>
            </div>
          </div>
          <div v-if="boardLoading" class="py-16 text-center text-[14px] text-muted">正在加载格位...</div>
          <div v-else class="grid max-w-full min-w-0 gap-2 overflow-hidden rounded-2xl border p-3 lg:gap-3 lg:p-4" :style="boardStyle(board.container)">
            <button
              v-for="slot in board.slots"
              :key="slot.location.id"
              class="slot-cell min-h-[92px] overflow-hidden rounded-xl border p-2 text-left transition lg:min-h-[108px] lg:p-3"
              :class="[
                sourceSlot?.location.id === slot.location.id ? 'border-green bg-green/10 ring-2 ring-green/20' :
                targetSlot?.location.id === slot.location.id ? 'border-dashed border-green bg-green/5' :
                slot.item?.need_restock || slot.item?.status === 'low' ? 'border-clay/30 bg-clay/5' :
                slot.item ? 'border-line bg-white hover:border-green/40' : 'border-dashed border-line bg-white/70 hover:border-green/40',
              ]"
              @click="chooseSlot(slot)"
            >
              <span class="block text-[12px] font-semibold" :class="slot.item?.need_restock ? 'text-clay' : 'text-muted'">{{ slot.location.slot_key }}</span>
              <template v-if="slot.item">
                <span class="mt-2 grid min-w-0 gap-1">
                  <span v-if="slot.item.cover_attachment_id" class="grid h-8 w-full place-items-center overflow-hidden rounded-[6px] bg-white/70 lg:h-9">
                    <ItemThumb :item="slot.item" :show-fallback="false" compact />
                  </span>
                  <span class="slot-item-name text-[12px] font-medium leading-4 text-ink lg:text-[13px]">{{ slot.item.name }}</span>
                  <span class="block truncate text-[11px] leading-4 text-muted lg:text-[12px]">{{ slot.item.quantity ?? '-' }} {{ slot.item.unit || '' }}</span>
                </span>
              </template>
              <span v-else class="mt-3 block truncate text-[12px] text-muted">{{ targetSlot?.location.id === slot.location.id ? '放入' : '空' }}</span>
            </button>
          </div>
        </template>

        <template v-else-if="activeLocation">
          <div class="mb-4 flex items-start justify-between gap-3">
            <div>
              <h3 class="text-[21px] font-semibold">{{ activeLocation.name }}</h3>
              <p class="mt-1 text-[13px] text-muted">{{ activeLocation.full_code }} · {{ activeLocation.type || '普通位置' }}</p>
            </div>
            <div class="hidden gap-2 lg:flex">
              <button class="inline-flex h-9 items-center gap-2 rounded-xl border border-line px-3 text-[13px]" @click="printLocationLabels(activeLocation)">
                <Printer :size="15" />打印标签
              </button>
              <button class="h-9 rounded-xl border border-line px-3 text-[13px]" @click="openContainer('convert', activeLocation)">配置为收纳盒</button>
              <button class="grid h-9 w-9 place-items-center rounded-xl border border-line text-green" @click="emit('edit', activeLocation)"><Pencil :size="15" /></button>
              <button class="grid h-9 w-9 place-items-center rounded-xl border border-red-200 text-red-600" @click="emit('delete', activeLocation)"><Trash2 :size="15" /></button>
            </div>
          </div>
          <div class="rounded-xl border border-line p-4 text-[14px]">
            <div class="mb-4 grid grid-cols-[88px_1fr] gap-y-3">
              <span class="text-muted">完整编号</span><span>{{ activeLocation.full_code }}</span>
              <span class="text-muted">物品数</span><span>{{ ordinaryItems.length }}</span>
              <span class="text-muted">描述</span><span>{{ activeLocation.description || '暂无描述' }}</span>
            </div>
            <h4 class="mb-2 border-t border-line pt-4 font-semibold">当前位置物品</h4>
            <button v-for="item in ordinaryItems" :key="item.code" class="flex w-full items-center gap-3 rounded-xl px-2 py-3 text-left hover:bg-wash" @click="store.selectItem(item.code)">
              <ItemThumb :item="item" />
              <span class="min-w-0 flex-1">
                <span class="block truncate text-[14px] font-medium">{{ item.name }}</span>
                <span class="text-[12px] text-muted">{{ item.code }} · {{ item.quantity ?? '-' }} {{ item.unit || '' }}</span>
              </span>
              <StatusDot :status="item.status" />
            </button>
            <div v-if="!ordinaryItems.length" class="py-10 text-center text-muted">该位置下暂无物品</div>
          </div>
        </template>

        <div v-else class="grid min-h-[350px] place-items-center text-center text-[14px] text-muted">
          <div><MapPinned class="mx-auto mb-3" :size="28" />选择收纳位置查看详情</div>
        </div>
      </main>

      <aside class="min-w-0 overflow-hidden rounded-2xl border border-line bg-white p-4">
        <template v-if="board">
          <h3 class="text-[17px] font-semibold">{{ isMobile ? '格位定位' : arranging ? '正在整理' : '格位详情' }}</h3>
          <p class="mt-2 text-[13px] leading-5 text-muted">
            {{ isMobile ? '此页面仅用于定位，不支持移动物品。' : arranging ? '选择物品后，再点击目标格位。' : '进入整理模式可直接调整格位。' }}
          </p>
          <div v-if="actionSlot" class="mt-5 rounded-xl border border-line bg-wash p-3">
            <div class="text-[12px] text-muted">{{ isMobile ? `${board.container.name} · ${actionSlot.location.slot_key}` : actionSlot.location.slot_key }}</div>
            <div v-if="actionSlot.item" class="mt-2 flex items-center gap-3">
              <ItemThumb v-if="actionSlot.item.cover_attachment_id" :item="actionSlot.item" :show-fallback="false" compact />
              <div class="min-w-0">
                <div class="truncate text-[14px] font-medium">{{ actionSlot.item.name }}</div>
                <div class="mt-1 text-[13px] text-muted">{{ actionSlot.item.code }} · {{ actionSlot.item.quantity ?? '-' }} {{ actionSlot.item.unit || '' }}</div>
              </div>
            </div>
            <div v-else class="mt-2 text-[14px] text-muted">空格位</div>
            <button class="mt-3 h-9 w-full rounded-xl border border-line text-[13px] text-green" @click="printLocationLabels(actionSlot.location)">打印此格标签</button>
            <button
              v-if="!isMobile && !arranging && selectedSlot?.item && selectedSlot.location.id === actionSlot.location.id"
              :disabled="busy"
              class="mt-3 h-9 w-full rounded-xl border border-red-200 text-[13px] text-red-600 disabled:opacity-50"
              @click="removeSelectedFromSlot"
            >
              移出格位
            </button>
          </div>
          <template v-if="!arranging && selectedSlot?.item">
            <div v-if="slotDetailLoading" class="mt-4 rounded-xl border border-line px-3 py-4 text-[13px] text-muted">正在加载物品详情...</div>
            <div v-if="slotDetailError" class="mt-4 rounded-xl border border-red-200 bg-red-50 px-3 py-3 text-[13px] text-red-700">{{ slotDetailError }}</div>
            <template v-if="slotDetailItem">
              <div class="mt-4 rounded-xl border border-line p-3">
                <h4 class="mb-3 text-[14px] font-semibold">基础信息</h4>
                <dl class="grid grid-cols-[70px_1fr] gap-y-2 text-[13px]">
                  <dt class="text-muted">类型</dt><dd>{{ slotCategory }}</dd>
                  <dt class="text-muted">编号</dt><dd>{{ slotDetailItem.code }}</dd>
                  <dt class="text-muted">数量</dt><dd><b>{{ slotDetailItem.quantity ?? '—' }}</b> {{ slotDetailItem.unit || '' }}</dd>
                  <dt class="text-muted">位置</dt><dd>{{ slotLocation }}</dd>
                  <dt class="text-muted">状态</dt><dd><StatusDot :status="slotDetailItem.status" /></dd>
                  <dt class="text-muted">备注</dt><dd class="text-muted">{{ slotDetailItem.description || '暂无备注' }}</dd>
                </dl>
              </div>

              <div class="mt-4 rounded-xl border border-line p-3">
                <h4 class="mb-3 text-[14px] font-semibold">属性</h4>
                <div class="space-y-2">
                  <div v-for="attr in slotAttributes" :key="attr.id" class="flex justify-between gap-3 text-[13px]">
                    <span class="text-muted">{{ attr.name }}</span>
                    <span class="text-right">{{ attr.value || '—' }}{{ attr.unit ? ` ${attr.unit}` : '' }}</span>
                  </div>
                  <div v-if="!slotAttributes.length" class="text-[13px] text-muted">暂无属性</div>
                </div>
              </div>

              <div class="mt-4 rounded-xl border border-line p-3">
                <h4 class="mb-3 inline-flex items-center gap-2 text-[14px] font-semibold"><Paperclip :size="15" />附件</h4>
                <div class="mb-2 text-[12px] text-muted">用于存放手册、数据表、说明文档等资料；封面图片不会显示在这里。</div>
                <div class="overflow-hidden rounded-lg border border-line">
                  <div v-for="attachment in slotDocumentAttachments" :key="attachment.id" class="flex items-center justify-between gap-3 border-b border-line px-3 py-2 last:border-b-0">
                    <div class="min-w-0">
                      <div class="truncate text-[13px] font-medium">{{ attachment.original_name }}</div>
                      <div class="text-[12px] text-muted">{{ attachment.mime_type || '未知类型' }}<template v-if="formatBytes(attachment.size_bytes)"> · {{ formatBytes(attachment.size_bytes) }}</template></div>
                    </div>
                    <div class="flex shrink-0 gap-2">
                      <button v-if="canPreviewAttachment(attachment)" class="grid h-8 w-8 place-items-center rounded-lg border border-line text-ink/70" title="预览" @click="previewAttachment(attachment)">
                        <ScrollText :size="15" />
                      </button>
                      <button class="grid h-8 w-8 place-items-center rounded-lg border border-line text-green" title="下载" @click="downloadAttachment(attachment)">
                        <ArrowDownToLine :size="15" />
                      </button>
                    </div>
                  </div>
                  <div v-if="!slotDocumentAttachments.length" class="px-3 py-4 text-[13px] text-muted">暂无附件</div>
                </div>
              </div>
            </template>
          </template>
          <template v-if="!isMobile && arranging">
            <div v-if="sourceSlot?.item && targetSlot" class="mt-4 rounded-xl border border-green/25 bg-green/5 p-3 text-[13px]">
              <div class="flex items-center gap-2 font-medium">
                {{ sourceSlot.location.slot_key }} <ChevronRight :size="14" /> {{ targetSlot.location.slot_key }}
              </div>
              <p class="mt-2 text-muted">{{ targetSlot.item ? `将与「${targetSlot.item.name}」交换格位。` : '目标为空格，将直接移动。' }}</p>
              <button :disabled="busy" class="mt-3 h-10 w-full rounded-xl bg-green text-[14px] font-medium text-white disabled:opacity-50" @click="confirmArrange">
                {{ targetSlot.item ? '确认交换格位' : '确认移动到此格' }}
              </button>
            </div>
            <p v-else class="mt-4 rounded-xl bg-wash px-3 py-3 text-[13px] text-muted">先选择一个有物品的格位作为来源。</p>
          </template>
          <template v-if="!isMobile && !arranging && selectedSlot && !selectedSlot.item && store.selectedItem">
            <button :disabled="busy" class="mt-4 h-10 w-full rounded-xl bg-green text-[14px] font-medium text-white" @click="placeSelectedItem(selectedSlot)">
              将已选物品放入 {{ selectedSlot.location.slot_key }}
            </button>
          </template>
          <button
            v-if="!isMobile && !arranging && selectedSlot && !selectedSlot.item"
            class="mt-3 h-10 w-full rounded-xl bg-green text-[14px] font-medium text-white"
            @click="openItemPicker(selectedSlot)"
          >
            选择已有物品放入此格
          </button>
          <button
            v-if="!isMobile && !arranging && selectedSlot && !selectedSlot.item"
            class="mt-3 h-10 w-full rounded-xl border border-line text-[14px] text-green"
            @click="emit('createInSlot', selectedSlot.location.full_code, `${board.container.name} · ${selectedSlot.location.slot_key}`)"
          >
            新建物品并放入此格
          </button>
        </template>
        <div v-else class="text-[14px] text-muted">选择一个收纳盒后，可在这里查看格位和整理动作。</div>
      </aside>
    </div>

    <ContainerFormDialog
      :open="containerDialog !== null"
      :mode="containerDialog || 'create'"
      :location="dialogLocation"
      :items="containerDialog === 'convert' ? ordinaryItems : []"
      :busy="busy"
      @close="containerDialog = null"
      @create="createContainer"
      @convert="convertContainer"
      @edit="updateLayout"
    />

    <div v-if="pdfPreviewUrl && pdfPreviewAttachment" class="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4" @click.self="closePdfPreview">
      <section class="flex h-[86vh] w-full max-w-5xl flex-col overflow-hidden rounded-[8px] border border-line bg-white shadow-soft">
        <header class="flex h-12 shrink-0 items-center justify-between border-b border-line px-4">
          <h3 class="truncate text-[15px] font-semibold">{{ pdfPreviewAttachment.original_name }}</h3>
          <button class="grid h-8 w-8 place-items-center rounded-[6px] text-muted hover:bg-slate-50" title="关闭" @click="closePdfPreview">
            <X :size="18" />
          </button>
        </header>
        <iframe :src="pdfPreviewUrl" class="min-h-0 flex-1 bg-white" title="PDF 预览"></iframe>
      </section>
    </div>

    <div v-if="pickerOpen && pickerSlot" class="fixed inset-0 z-50 grid place-items-center bg-ink/30 p-4" @click.self="pickerOpen = false">
      <div class="w-full max-w-[560px] overflow-hidden rounded-2xl border border-line bg-white shadow-soft">
        <header class="flex items-start justify-between border-b border-line px-5 py-4">
          <div>
            <h3 class="text-[18px] font-semibold">选择物品放入 {{ pickerSlot.location.slot_key }}</h3>
            <p class="mt-1 text-[13px] text-muted">会将整条物品记录移动到该格位。</p>
          </div>
          <button class="grid h-9 w-9 place-items-center rounded-lg text-muted hover:bg-wash" @click="pickerOpen = false">×</button>
        </header>
        <div class="p-5">
          <input
            v-model="pickerQuery"
            class="h-11 w-full rounded-xl border border-line px-3 text-[14px] outline-none focus:border-green"
            placeholder="搜索名称、编号、规格、位置、标签..."
            @input="loadPickerItems"
          />
          <div class="mt-4 max-h-[360px] overflow-y-auto rounded-xl border border-line">
            <div v-if="pickerLoading" class="px-4 py-6 text-center text-[14px] text-muted">正在搜索...</div>
            <button
              v-for="item in pickerItems"
              :key="item.code"
              :disabled="busy"
              class="flex w-full items-center gap-3 border-b border-line px-4 py-3 text-left last:border-b-0 hover:bg-wash disabled:opacity-50"
              @click="placePickedItem(item)"
            >
              <ItemThumb :item="item" compact />
              <span class="min-w-0 flex-1">
                <span class="block truncate text-[14px] font-medium">{{ item.name }}</span>
                <span class="mt-0.5 block truncate text-[12px] text-muted">{{ item.code }} · {{ item.location_display || item.location_text || '未记录位置' }}</span>
              </span>
              <span class="shrink-0 text-[13px] font-medium">{{ item.quantity ?? '—' }} {{ item.unit || '' }}</span>
            </button>
            <div v-if="!pickerLoading && !pickerItems.length" class="px-4 py-6 text-center text-[14px] text-muted">暂无匹配物品</div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.slot-cell :deep(img) {
  max-height: 100%;
  max-width: 100%;
  object-fit: contain;
}

.slot-item-name {
  display: -webkit-box;
  min-height: 32px;
  overflow: hidden;
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
</style>
