<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { BrowserQRCodeReader } from '@zxing/browser'
import { ArrowDownToLine, ArrowLeft, Camera, Paperclip, QrCode, ScrollText, Search, X } from 'lucide-vue-next'

import { resolveMsloc } from '@/api/catalog'
import { downloadAttachmentFile, fetchItem, fetchItemAttachments, fetchItemAttributes } from '@/api/items'
import ItemThumb from '@/components/ui/ItemThumb.vue'
import StatusDot from '@/components/ui/StatusDot.vue'
import { useInventoryStore } from '@/stores/inventory'
import type { Attachment, ContainerBoard, ContainerBoardSlot, Item, ItemAttribute, LocationNode, MslocResolution } from '@/types'
import { parseMsloc } from '@/utils/msloc'

const route = useRoute()
const router = useRouter()
const store = useInventoryStore()

const videoRef = ref<HTMLVideoElement | null>(null)
const manualText = ref('')
const mode = ref<'camera' | 'manual'>('camera')
const scanning = ref(false)
const scannerMessage = ref('正在准备摄像头...')
const resultMessage = ref<{ type: 'error' | 'success'; text: string } | null>(null)
const location = ref<LocationNode | null>(null)
const board = ref<ContainerBoard | null>(null)
const slot = ref<ContainerBoardSlot | null>(null)
const ordinaryItems = ref<Item[]>([])
const detailItem = ref<Item | null>(null)
const detailAttributes = ref<ItemAttribute[]>([])
const detailAttachments = ref<Attachment[]>([])
const detailLoading = ref(false)
const detailError = ref<string | null>(null)
const previewAttachment = ref<Attachment | null>(null)
const previewUrl = ref<string | null>(null)
const loading = ref(false)
const resultOpen = ref(false)
let controls: { stop: () => void } | null = null
let reader: BrowserQRCodeReader | null = null
let lastScanText = ''
let lastScanAt = 0

const isSlot = computed(() => Boolean(location.value?.is_slot))
const isContainer = computed(() => Boolean(location.value?.layout_type && !location.value?.is_slot))
const containerName = computed(() => board.value?.container.name || location.value?.name || '位置')
const slotTitle = computed(() => slot.value ? `${containerName.value} · ${slot.value.location.slot_key}` : location.value?.name || '')

onMounted(async () => {
  if (!store.locations.length) await store.bootstrap()
  const initialCode = typeof route.query.code === 'string' ? route.query.code : ''
  if (initialCode) {
    manualText.value = initialCode
    await resolveText(initialCode)
  }
  if (!resultOpen.value) await startScanner()
})

onBeforeUnmount(() => {
  stopScanner()
  closeAttachmentPreview()
})

function stopScanner() {
  controls?.stop()
  controls = null
  scanning.value = false
}

async function startScanner() {
  if (mode.value !== 'camera') return
  await nextTick()
  if (!videoRef.value) return
  stopScanner()
  try {
    reader = new BrowserQRCodeReader()
    controls = await reader.decodeFromVideoDevice(undefined, videoRef.value, (result) => {
      const text = result?.getText()
      if (!text) return
      const now = Date.now()
      if (loading.value || (text === lastScanText && now - lastScanAt < 1600)) return
      lastScanText = text
      lastScanAt = now
      stopScanner()
      scannerMessage.value = '扫码已暂停，关闭结果后继续扫描'
      manualText.value = text
      void resolveText(text)
    })
    scanning.value = true
    scannerMessage.value = '将二维码放入取景框'
  } catch (error) {
    scannerMessage.value = error instanceof Error ? error.message : '无法打开摄像头，请使用手动输入。'
    mode.value = 'manual'
  }
}

async function switchMode(nextMode: 'camera' | 'manual') {
  mode.value = nextMode
  if (nextMode === 'manual') {
    stopScanner()
  } else {
    await startScanner()
  }
}

async function resolveText(text: string) {
  const fullCode = parseMsloc(text)
  if (!fullCode) {
    resultMessage.value = { type: 'error', text: '二维码内容必须以 MSLOC: 开头' }
    clearResult()
    return
  }
  loading.value = true
  resultMessage.value = null
  try {
    const resolved = await resolveMsloc(text)
    openResolvedLocation(resolved)
    resultOpen.value = true
    resultMessage.value = { type: 'success', text: `已打开 ${fullCode}` }
    if (mode.value === 'camera') scannerMessage.value = '扫码已暂停，关闭结果后继续扫描'
  } catch (error) {
    clearResult()
    resultMessage.value = { type: 'error', text: error instanceof Error ? error.message : '位置查询失败' }
  } finally {
    loading.value = false
  }
}

function clearResult() {
  resultOpen.value = false
  location.value = null
  board.value = null
  slot.value = null
  ordinaryItems.value = []
  clearItemDetail()
}

function openResolvedLocation(resolved: MslocResolution) {
  clearResult()
  location.value = resolved.location
  if (resolved.kind === 'slot') {
    board.value = { container: resolved.container, slots: [resolved.slot] }
    slot.value = resolved.slot
    return
  }
  if (resolved.kind === 'container') {
    board.value = { container: resolved.container, slots: resolved.slots }
    return
  }
  ordinaryItems.value = resolved.items
}

async function openItemDetail(item: Item) {
  detailLoading.value = true
  detailError.value = null
  detailItem.value = item
  detailAttributes.value = []
  detailAttachments.value = []
  try {
    const [fullItem, attributes, attachments] = await Promise.all([
      fetchItem(item.code),
      fetchItemAttributes(item.code),
      fetchItemAttachments(item.code),
    ])
    detailItem.value = fullItem
    detailAttributes.value = attributes.attributes
    detailAttachments.value = attachments.attachments.filter((attachment) => !attachment.is_deleted && !isCoverAttachment(attachment, fullItem))
  } catch (error) {
    detailError.value = error instanceof Error ? error.message : '物品详情加载失败'
  } finally {
    detailLoading.value = false
  }
}

async function closeResult() {
  resultOpen.value = false
  clearItemDetail()
  closeAttachmentPreview()
  if (mode.value === 'camera') await startScanner()
}

function clearItemDetail() {
  detailItem.value = null
  detailAttributes.value = []
  detailAttachments.value = []
  detailLoading.value = false
  detailError.value = null
}

function isCoverAttachment(attachment: Attachment, item = detailItem.value) {
  return attachment.is_cover || attachment.id === item?.cover_attachment_id
}

function formatBytes(bytes: number | null) {
  if (!bytes && bytes !== 0) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
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
  const name = attachment.original_name.toLowerCase()
  return Boolean(
    attachment.mime_type?.startsWith('image/')
    || attachment.mime_type === 'application/pdf'
    || name.endsWith('.pdf')
  )
}

function isImagePreview(attachment: Attachment) {
  return Boolean(attachment.mime_type?.startsWith('image/'))
}

function slotItemSummary(item: Item) {
  const quantity = item.quantity ?? null
  if (quantity === null || quantity === '') return item.code
  return `${quantity}${item.unit ? ` ${item.unit}` : ''} · ${item.code}`
}

async function openAttachmentPreview(attachment: Attachment) {
  const blob = await downloadAttachmentFile(attachment.id)
  closeAttachmentPreview()
  const previewBlob = attachment.mime_type === 'application/pdf' || attachment.original_name.toLowerCase().endsWith('.pdf')
    ? new Blob([blob], { type: 'application/pdf' })
    : blob
  previewAttachment.value = attachment
  previewUrl.value = URL.createObjectURL(previewBlob)
}

function closeAttachmentPreview() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = null
  previewAttachment.value = null
}

function back() {
  if (window.history.length > 1) router.back()
  else router.push({ name: 'home' })
}
</script>

<template>
  <main class="min-h-screen bg-wash text-ink">
    <header class="sticky top-0 z-10 flex items-center justify-between border-b border-line bg-panel px-4 py-3">
      <button class="grid h-10 w-10 place-items-center rounded-xl border border-line bg-white" title="返回" @click="back">
        <ArrowLeft :size="18" />
      </button>
      <div class="text-center">
        <h1 class="text-[18px] font-semibold">扫码查看位置</h1>
        <p class="text-[12px] text-muted">MSLOC 位置二维码</p>
      </div>
      <button class="grid h-10 w-10 place-items-center rounded-xl border border-line bg-white text-green" title="手动输入" @click="switchMode(mode === 'camera' ? 'manual' : 'camera')">
        <QrCode v-if="mode === 'manual'" :size="18" />
        <Camera v-else :size="18" />
      </button>
    </header>

    <section class="mx-auto grid w-full max-w-5xl gap-4 p-4 lg:grid-cols-[minmax(0,420px)_1fr]">
      <div class="rounded-2xl border border-line bg-white p-4">
        <div v-if="mode === 'camera'" class="overflow-hidden rounded-xl bg-ink">
          <video ref="videoRef" class="aspect-[4/3] w-full object-cover" muted playsinline></video>
        </div>
        <div v-else class="rounded-xl border border-line bg-wash p-3">
          <textarea v-model="manualText" class="min-h-[120px] w-full rounded-xl border border-line bg-white p-3 font-mono text-[13px] outline-none focus:border-green" placeholder="MSLOC:WS.BOX-A.A01"></textarea>
          <button class="mt-3 inline-flex h-10 w-full items-center justify-center gap-2 rounded-xl bg-green text-[14px] font-medium text-white" @click="resolveText(manualText)">
            <Search :size="16" /> 解析并查看
          </button>
        </div>
        <p class="mt-3 text-[13px] text-muted">{{ mode === 'camera' ? scannerMessage : '没有摄像头权限或不方便扫码时，可粘贴二维码内容。' }}</p>
        <button class="mt-3 h-9 w-full rounded-xl border border-line text-[13px] text-green" @click="switchMode(mode === 'camera' ? 'manual' : 'camera')">
          {{ mode === 'camera' ? '切换到手动输入' : '切换到摄像头扫码' }}
        </button>
      </div>

      <section class="min-w-0 rounded-2xl border border-line bg-white p-4">
        <div v-if="resultMessage" class="mb-4 rounded-xl border px-3 py-2 text-[13px]" :class="resultMessage.type === 'error' ? 'border-red-200 bg-red-50 text-red-700' : 'border-green/20 bg-green/10 text-green'">
          {{ resultMessage.text }}
        </div>
        <div v-if="loading" class="py-16 text-center text-[14px] text-muted">正在打开位置...</div>
        <div v-else-if="resultOpen" class="grid min-h-[320px] place-items-center text-center text-[14px] text-muted">
          <div>
            <QrCode class="mx-auto mb-3 text-green" :size="30" />
            扫码结果已打开，关闭结果后继续扫描
          </div>
        </div>

        <template v-else-if="isSlot && slot">
          <h2 class="text-[22px] font-semibold">{{ slotTitle }}</h2>
          <p class="mt-1 break-all font-mono text-[12px] text-muted">{{ slot.location.full_code }}</p>
          <div class="mt-5 rounded-xl border border-line bg-wash p-4">
            <div class="text-[13px] text-muted">当前物品</div>
            <div v-if="slot.item" class="mt-3 flex items-center gap-3">
              <ItemThumb :item="slot.item" />
              <div class="min-w-0 flex-1">
                <div class="truncate text-[16px] font-semibold">{{ slot.item.name }}</div>
                <div class="mt-1 text-[13px] text-muted">{{ slot.item.code }} · {{ slot.item.quantity ?? '-' }} {{ slot.item.unit || '' }}</div>
              </div>
              <StatusDot :status="slot.item.status" />
            </div>
            <div v-else class="mt-3 text-[15px] text-muted">空</div>
            <button v-if="slot.item" class="mt-4 h-10 w-full rounded-xl bg-green text-[14px] font-medium text-white" @click="openItemDetail(slot.item)">查看物品详情</button>
          </div>
        </template>

        <template v-else-if="isContainer && board">
          <h2 class="text-[22px] font-semibold">{{ board.container.name }}</h2>
          <p class="mt-1 break-all font-mono text-[12px] text-muted">{{ board.container.full_code }}</p>
          <div class="mt-5 grid gap-2" :style="{ gridTemplateColumns: `repeat(${board.container.layout_columns || 1}, minmax(0, 1fr))` }">
            <button
              v-for="entry in board.slots"
              :key="entry.location.id"
              :disabled="!entry.item"
              class="min-h-[86px] rounded-xl border p-2 text-left transition disabled:cursor-default"
              :class="entry.item ? 'border-line bg-white hover:border-green/40 active:bg-green/5' : 'border-dashed border-line bg-wash'"
              @click="entry.item && openItemDetail(entry.item)"
            >
              <div class="flex items-center justify-between gap-2">
                <span class="text-[12px] font-semibold text-muted">{{ entry.location.slot_key }}</span>
                <span v-if="entry.item" class="rounded-full bg-green/10 px-1.5 py-0.5 text-[10px] text-green">查看</span>
              </div>
              <template v-if="entry.item">
                <div class="slot-item-name mt-2 text-[12px] font-medium leading-4 text-ink">{{ entry.item.name }}</div>
                <div class="mt-1 truncate text-[11px] leading-4 text-muted">{{ slotItemSummary(entry.item) }}</div>
              </template>
              <div v-else class="mt-3 text-[12px] text-muted">空</div>
            </button>
          </div>
        </template>

        <template v-else-if="location">
          <h2 class="text-[22px] font-semibold">{{ location.name }}</h2>
          <p class="mt-1 break-all font-mono text-[12px] text-muted">{{ location.full_code }}</p>
          <div class="mt-5 rounded-xl border border-line">
            <button v-for="item in ordinaryItems" :key="item.code" class="flex w-full items-center gap-3 border-b border-line px-3 py-3 text-left last:border-b-0" @click="openItemDetail(item)">
              <ItemThumb :item="item" compact />
              <span class="min-w-0 flex-1">
                <span class="block truncate text-[14px] font-medium">{{ item.name }}</span>
                <span class="text-[12px] text-muted">{{ item.code }} · {{ item.quantity ?? '-' }} {{ item.unit || '' }}</span>
              </span>
              <StatusDot :status="item.status" />
            </button>
            <div v-if="!ordinaryItems.length" class="px-3 py-8 text-center text-[14px] text-muted">该位置下暂无物品</div>
          </div>
        </template>

        <div v-else class="grid min-h-[320px] place-items-center text-center text-[14px] text-muted">
          <div>
            <QrCode class="mx-auto mb-3" :size="30" />
            扫描或输入 MSLOC 二维码后查看位置内容
          </div>
        </div>

        <div v-if="detailItem && !resultOpen" class="mt-4 rounded-xl border border-line p-4">
          <h3 class="text-[17px] font-semibold">{{ detailItem.name }}</h3>
          <dl class="mt-3 grid grid-cols-[76px_1fr] gap-y-2 text-[13px]">
            <dt class="text-muted">编号</dt><dd>{{ detailItem.code }}</dd>
            <dt class="text-muted">数量</dt><dd>{{ detailItem.quantity ?? '—' }} {{ detailItem.unit || '' }}</dd>
            <dt class="text-muted">状态</dt><dd><StatusDot :status="detailItem.status" /></dd>
            <dt class="text-muted">备注</dt><dd class="text-muted">{{ detailItem.description || '暂无备注' }}</dd>
          </dl>
        </div>
      </section>
    </section>

    <div v-if="resultOpen" class="fixed inset-0 z-30 flex items-end justify-center bg-ink/35 p-0 sm:items-center sm:p-4" @click.self="closeResult">
      <section class="max-h-[88vh] w-full overflow-hidden rounded-t-3xl border border-line bg-white shadow-soft sm:max-w-[720px] sm:rounded-2xl">
        <header class="flex items-center justify-between border-b border-line px-4 py-3">
          <div>
            <h2 class="text-[17px] font-semibold">扫码结果</h2>
            <p class="mt-0.5 text-[12px] text-muted">扫码已暂停，关闭后继续扫描</p>
          </div>
          <button class="grid h-9 w-9 place-items-center rounded-xl border border-line text-muted" title="关闭" @click="closeResult">
            <X :size="17" />
          </button>
        </header>

        <div class="thin-scrollbar max-h-[calc(88vh-58px)] overflow-y-auto p-4">
          <template v-if="isSlot && slot">
            <h3 class="text-[22px] font-semibold">{{ slotTitle }}</h3>
            <p class="mt-1 break-all font-mono text-[12px] text-muted">{{ slot.location.full_code }}</p>
            <div class="mt-5 rounded-xl border border-line bg-wash p-4">
              <div class="text-[13px] text-muted">当前物品</div>
              <div v-if="slot.item" class="mt-3 flex items-center gap-3">
                <ItemThumb :item="slot.item" />
                <div class="min-w-0 flex-1">
                  <div class="truncate text-[16px] font-semibold">{{ slot.item.name }}</div>
                  <div class="mt-1 text-[13px] text-muted">{{ slot.item.code }} · {{ slot.item.quantity ?? '-' }} {{ slot.item.unit || '' }}</div>
                </div>
                <StatusDot :status="slot.item.status" />
              </div>
              <div v-else class="mt-3 text-[15px] text-muted">空</div>
              <button v-if="slot.item" class="mt-4 h-10 w-full rounded-xl bg-green text-[14px] font-medium text-white" @click="openItemDetail(slot.item)">查看物品详情</button>
            </div>
          </template>

          <template v-else-if="isContainer && board">
            <h3 class="text-[22px] font-semibold">{{ board.container.name }}</h3>
            <p class="mt-1 break-all font-mono text-[12px] text-muted">{{ board.container.full_code }}</p>
            <div class="mt-5 grid gap-2" :style="{ gridTemplateColumns: `repeat(${board.container.layout_columns || 1}, minmax(0, 1fr))` }">
              <button
                v-for="entry in board.slots"
                :key="entry.location.id"
                :disabled="!entry.item"
                class="min-h-[86px] rounded-xl border p-2 text-left transition disabled:cursor-default"
                :class="entry.item ? 'border-line bg-white hover:border-green/40 active:bg-green/5' : 'border-dashed border-line bg-wash'"
                @click="entry.item && openItemDetail(entry.item)"
              >
                <div class="flex items-center justify-between gap-2">
                  <span class="text-[12px] font-semibold text-muted">{{ entry.location.slot_key }}</span>
                  <span v-if="entry.item" class="rounded-full bg-green/10 px-1.5 py-0.5 text-[10px] text-green">查看</span>
                </div>
                <template v-if="entry.item">
                  <div class="slot-item-name mt-2 text-[12px] font-medium leading-4 text-ink">{{ entry.item.name }}</div>
                  <div class="mt-1 truncate text-[11px] leading-4 text-muted">{{ slotItemSummary(entry.item) }}</div>
                </template>
                <div v-else class="mt-3 text-[12px] text-muted">空</div>
              </button>
            </div>
          </template>

          <template v-else-if="location">
            <h3 class="text-[22px] font-semibold">{{ location.name }}</h3>
            <p class="mt-1 break-all font-mono text-[12px] text-muted">{{ location.full_code }}</p>
            <div class="mt-5 rounded-xl border border-line">
              <button v-for="item in ordinaryItems" :key="item.code" class="flex w-full items-center gap-3 border-b border-line px-3 py-3 text-left last:border-b-0" @click="openItemDetail(item)">
                <ItemThumb :item="item" compact />
                <span class="min-w-0 flex-1">
                  <span class="block truncate text-[14px] font-medium">{{ item.name }}</span>
                  <span class="text-[12px] text-muted">{{ item.code }} · {{ item.quantity ?? '-' }} {{ item.unit || '' }}</span>
                </span>
                <StatusDot :status="item.status" />
              </button>
              <div v-if="!ordinaryItems.length" class="px-3 py-8 text-center text-[14px] text-muted">该位置下暂无物品</div>
            </div>
          </template>

          <div v-if="detailLoading" class="mt-4 rounded-xl border border-line px-3 py-4 text-[13px] text-muted">正在加载物品详情...</div>
          <div v-if="detailError" class="mt-4 rounded-xl border border-red-200 bg-red-50 px-3 py-3 text-[13px] text-red-700">{{ detailError }}</div>
          <div v-if="detailItem" class="mt-4 space-y-4">
            <section class="rounded-xl border border-line p-4">
              <h3 class="text-[17px] font-semibold">{{ detailItem.name }}</h3>
              <dl class="mt-3 grid grid-cols-[76px_1fr] gap-y-2 text-[13px]">
                <dt class="text-muted">编号</dt><dd>{{ detailItem.code }}</dd>
                <dt class="text-muted">数量</dt><dd>{{ detailItem.quantity ?? '—' }} {{ detailItem.unit || '' }}</dd>
                <dt class="text-muted">状态</dt><dd><StatusDot :status="detailItem.status" /></dd>
                <dt class="text-muted">备注</dt><dd class="text-muted">{{ detailItem.description || '暂无备注' }}</dd>
              </dl>
            </section>

            <section class="rounded-xl border border-line p-4">
              <h3 class="text-[15px] font-semibold">属性</h3>
              <div class="mt-3 space-y-2">
                <div v-for="attr in detailAttributes" :key="attr.id" class="flex justify-between gap-3 text-[13px]">
                  <span class="text-muted">{{ attr.name }}</span>
                  <span class="text-right">{{ attr.value || '—' }}{{ attr.unit ? ` ${attr.unit}` : '' }}</span>
                </div>
                <div v-if="!detailAttributes.length" class="text-[13px] text-muted">暂无属性</div>
              </div>
            </section>

            <section class="rounded-xl border border-line p-4">
              <h3 class="inline-flex items-center gap-2 text-[15px] font-semibold"><Paperclip :size="15" />附件</h3>
              <div class="mt-3 overflow-hidden rounded-lg border border-line">
                <div v-for="attachment in detailAttachments" :key="attachment.id" class="flex items-center justify-between gap-3 border-b border-line px-3 py-2 last:border-b-0">
                  <div class="min-w-0">
                    <div class="truncate text-[13px] font-medium">{{ attachment.original_name }}</div>
                    <div class="text-[12px] text-muted">{{ attachment.mime_type || '未知类型' }}<template v-if="formatBytes(attachment.size_bytes)"> · {{ formatBytes(attachment.size_bytes) }}</template></div>
                  </div>
                  <div class="flex shrink-0 gap-2">
                    <button v-if="canPreviewAttachment(attachment)" class="grid h-8 w-8 place-items-center rounded-lg border border-line text-ink/70" title="预览" @click="openAttachmentPreview(attachment)">
                      <ScrollText :size="15" />
                    </button>
                    <button class="grid h-8 w-8 place-items-center rounded-lg border border-line text-green" title="下载" @click="downloadAttachment(attachment)">
                      <ArrowDownToLine :size="15" />
                    </button>
                  </div>
                </div>
                <div v-if="!detailAttachments.length" class="px-3 py-4 text-[13px] text-muted">暂无附件</div>
              </div>
            </section>
          </div>
        </div>
      </section>
    </div>

    <div v-if="previewUrl && previewAttachment" class="fixed inset-0 z-40 flex items-center justify-center bg-ink/45 p-4" @click.self="closeAttachmentPreview">
      <section class="flex h-[86vh] w-full max-w-5xl flex-col overflow-hidden rounded-[8px] border border-line bg-white shadow-soft">
        <header class="flex h-12 shrink-0 items-center justify-between border-b border-line px-4">
          <h3 class="truncate text-[15px] font-semibold">{{ previewAttachment.original_name }}</h3>
          <button class="grid h-8 w-8 place-items-center rounded-[6px] text-muted hover:bg-wash" title="关闭" @click="closeAttachmentPreview">
            <X :size="18" />
          </button>
        </header>
        <div class="min-h-0 flex-1 bg-white">
          <img v-if="isImagePreview(previewAttachment)" :src="previewUrl" :alt="previewAttachment.original_name" class="h-full w-full object-contain" />
          <iframe v-else :src="previewUrl" class="h-full w-full bg-white" title="附件预览"></iframe>
        </div>
      </section>
    </div>
  </main>
</template>

<style scoped>
.slot-item-name {
  display: -webkit-box;
  min-height: 32px;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
</style>
