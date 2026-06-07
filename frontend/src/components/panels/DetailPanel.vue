<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ArrowDownToLine, Heart, MapPinned, PackageCheck, Paperclip, Pencil, ScrollText, SlidersHorizontal, Trash2, Upload, X } from 'lucide-vue-next'

import ExtensionActionSlot from '@/components/extensions/ExtensionActionSlot.vue'
import StatusDot from '@/components/ui/StatusDot.vue'
import { downloadAttachmentFile } from '@/api/items'
import { useInventoryStore } from '@/stores/inventory'
import type { Attachment } from '@/types'

const store = useInventoryStore()
const props = withDefaults(defineProps<{ allowMove?: boolean }>(), {
  allowMove: true,
})
const emit = defineEmits<{
  addQuantity: []
  useQuantity: []
  adjustQuantity: []
  edit: []
  delete: []
  favorite: []
  restock: []
  editTags: []
  editAttributes: []
  move: []
  uploadImage: [file: File]
  uploadAttachment: [file: File]
  deleteAttachment: [id: number]
}>()

const MAX_UPLOAD_BYTES = 50 * 1024 * 1024
const IMAGE_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp', 'image/gif'])
const RECENT_NOTE_LIMIT = 3
const item = computed(() => store.selectedItem)
const category = computed(() => (item.value?.category_id ? store.categoryById.get(item.value.category_id)?.name : '未分类'))
const location = computed(() => (item.value?.location_id ? store.locationById.get(item.value.location_id)?.full_code : item.value?.location_text))
const showAllNotes = ref(false)
const visibleNotes = computed(() => (showAllNotes.value ? store.selectedNotes : store.selectedNotes.slice(0, RECENT_NOTE_LIMIT)))
const hasMoreNotes = computed(() => store.selectedNotes.length > RECENT_NOTE_LIMIT)
const coverAttachment = computed(() => {
  if (!item.value) return null
  return store.selectedAttachments.find((attachment) => attachment.id === item.value?.cover_attachment_id)
    || store.selectedAttachments.find((attachment) => attachment.is_cover)
    || store.selectedAttachments.find((attachment) => attachment.attachment_type === 'image')
    || null
})
const documentAttachments = computed(() => store.selectedAttachments.filter((attachment) => !isCoverAttachment(attachment)))
const coverUrl = ref<string | null>(null)
const coverHovered = ref(false)
const pdfPreviewAttachment = ref<Attachment | null>(null)
const pdfPreviewUrl = ref<string | null>(null)

function isCoverAttachment(attachment: Attachment) {
  return attachment.is_cover || attachment.id === item.value?.cover_attachment_id
}

function clearCoverUrl() {
  if (coverUrl.value) URL.revokeObjectURL(coverUrl.value)
  coverUrl.value = null
}

function closePdfPreview() {
  if (pdfPreviewUrl.value) URL.revokeObjectURL(pdfPreviewUrl.value)
  pdfPreviewUrl.value = null
  pdfPreviewAttachment.value = null
}

watch(
  () => coverAttachment.value?.id,
  async (attachmentId) => {
    clearCoverUrl()
    if (!attachmentId) return
    try {
      const blob = await downloadAttachmentFile(attachmentId)
      coverUrl.value = URL.createObjectURL(blob)
    } catch {
      coverUrl.value = null
    }
  },
  { immediate: true },
)

watch(
  () => item.value?.code,
  () => {
    showAllNotes.value = false
  },
)

onBeforeUnmount(() => {
  clearCoverUrl()
  closePdfPreview()
})
onMounted(() => window.addEventListener('paste', onWindowPaste))
onBeforeUnmount(() => window.removeEventListener('paste', onWindowPaste))

function onAttachmentChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file && validateFile(file)) emit('uploadAttachment', file)
  input.value = ''
}

function onImageChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file && validateFile(file, true)) emit('uploadImage', file)
  input.value = ''
}

function onWindowPaste(event: ClipboardEvent) {
  if (!item.value || !coverHovered.value || isEditablePasteTarget(event.target)) return

  const file = getPastedImageFile(event.clipboardData)
  if (!file) return

  event.preventDefault()
  if (coverAttachment.value && !window.confirm('当前物品已有封面，是否替换为粘贴的图片？')) return
  if (validateFile(file, true)) emit('uploadImage', file)
}

function isEditablePasteTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return false
  return target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)
}

function getPastedImageFile(data: DataTransfer | null) {
  if (!data) return null

  for (const item of Array.from(data.items)) {
    if (item.kind !== 'file' || !item.type.startsWith('image/')) continue
    const file = item.getAsFile()
    if (!file) return null
    if (file.name) return file

    const extension = item.type.split('/')[1] || 'png'
    return new File([file], `pasted-cover.${extension}`, { type: file.type, lastModified: file.lastModified })
  }

  return null
}

function validateFile(file: File, imageOnly = false) {
  if (file.size > MAX_UPLOAD_BYTES) {
    window.alert('文件超过 50MB，请压缩或拆分后再上传。')
    return false
  }
  if (imageOnly && !IMAGE_TYPES.has(file.type)) {
    window.alert('封面图片只支持 JPEG、PNG、WebP 或 GIF。')
    return false
  }
  return true
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
</script>

<template>
  <section v-if="item" class="flex h-full min-h-0 flex-col">
    <div class="flex h-[56px] shrink-0 items-center justify-between border-b border-line px-5">
      <h2 class="truncate text-[20px] font-semibold">{{ item.name }}</h2>
      <button class="grid h-9 w-9 place-items-center rounded-[6px] text-muted hover:bg-slate-50">
        <X :size="22" />
      </button>
    </div>

      <div class="thin-scrollbar min-h-0 flex-1 overflow-y-auto px-4 py-3 2xl:px-5 2xl:py-4">
      <div
        class="relative grid min-h-[144px] place-items-center overflow-hidden rounded-[8px] border border-line bg-gradient-to-br from-white to-slate-100 p-3 2xl:min-h-[176px]"
        @mouseenter="coverHovered = true"
        @mouseleave="coverHovered = false"
      >
        <img v-if="coverUrl" :src="coverUrl" :alt="item.name" class="max-h-[128px] max-w-full object-contain 2xl:max-h-[160px]" />
        <div v-else class="h-[70px] w-[120px] rounded-full bg-[radial-gradient(circle_at_center,#16191f_0,#16191f_40%,#2a2f36_42%,#0c0d10_64%,transparent_65%)] shadow-soft 2xl:h-[88px] 2xl:w-[150px]"></div>
        <div v-if="!coverAttachment && coverHovered" class="absolute inset-x-3 bottom-3 rounded-[6px] border border-dashed border-blue/40 bg-white/90 px-3 py-2 text-center text-[12px] text-blue shadow-sm">粘贴图片上传封面</div>
        <div class="absolute right-2 top-2 flex gap-2">
          <button v-if="coverAttachment" class="inline-flex h-8 cursor-pointer items-center gap-1 rounded-[6px] border border-red-200 bg-white/95 px-3 text-[12px] font-medium text-red-600 shadow-sm hover:bg-red-50" title="删除封面" @click="emit('deleteAttachment', coverAttachment.id)">
            <Trash2 :size="14" />删除
          </button>
          <label class="inline-flex h-8 cursor-pointer items-center gap-1 rounded-[6px] border border-line bg-white/95 px-3 text-[12px] font-medium text-ink/80 shadow-sm hover:border-blue hover:text-blue">
            <Upload :size="14" />封面
            <input type="file" accept="image/jpeg,image/png,image/webp,image/gif" class="hidden" @change="onImageChange" />
          </label>
        </div>
      </div>

      <dl class="mt-3 grid grid-cols-[78px_1fr] gap-y-2 text-[14px] 2xl:mt-4 2xl:grid-cols-[92px_1fr] 2xl:gap-y-3">
        <dt class="text-muted">类型</dt><dd>{{ category }}</dd>
        <dt class="text-muted">编号</dt><dd>{{ item.code }}</dd>
        <dt class="text-muted">数量</dt><dd><b>{{ item.quantity ?? '—' }}</b> {{ item.unit }}</dd>
        <dt class="text-muted">位置</dt><dd>{{ item.location_display || item.location_text || location || '未记录' }}</dd>
        <dt class="text-muted">状态</dt><dd><StatusDot :status="item.status" /></dd>
        <dt class="text-muted">标签</dt>
        <dd class="flex flex-wrap gap-2">
          <span v-for="tag in store.selectedTags" :key="tag.id" class="rounded-[5px] border border-blue/20 bg-blue/10 px-2 py-1 text-[12px] text-blue">{{ tag.name }}</span>
          <span v-if="!store.selectedTags.length" class="text-muted">暂无</span>
          <button class="rounded-[5px] border border-blue/30 px-2 py-1 text-[12px] text-blue" @click="emit('editTags')">编辑</button>
        </dd>
        <dt class="text-muted">备注</dt><dd class="text-muted">{{ item.description || '添加备注...' }}</dd>
      </dl>

      <div class="mt-4 border-t border-line pt-3 2xl:mt-5 2xl:pt-4">
        <div class="mb-3 flex items-center justify-between">
          <h3 class="text-[15px] font-semibold">属性</h3>
          <button class="text-[13px] text-blue" @click="emit('editAttributes')">编辑</button>
        </div>
        <div class="space-y-2">
          <div v-for="attr in store.selectedAttributes" :key="attr.id" class="flex justify-between text-[14px]">
            <span class="text-muted">{{ attr.name }}</span>
            <span>{{ attr.value }}{{ attr.unit ? ` ${attr.unit}` : '' }}</span>
          </div>
          <div v-if="!store.selectedAttributes.length" class="text-[14px] text-muted">暂无属性</div>
        </div>
      </div>

      <div class="mt-4 border-t border-line pt-3 2xl:mt-5 2xl:pt-4">
        <h3 class="mb-2 text-[15px] font-semibold 2xl:mb-3">库存操作</h3>
        <div class="grid grid-cols-2 gap-3">
          <button class="inline-flex h-11 items-center justify-center gap-2 rounded-[8px] border border-blue bg-blue/5 text-[15px] font-medium text-blue" @click="emit('addQuantity')">
            <ArrowDownToLine :size="19" /> 入库
          </button>
          <button class="inline-flex h-11 items-center justify-center gap-2 rounded-[8px] border border-orange-300 bg-orange-50 text-[15px] font-medium text-orange-600" @click="emit('useQuantity')">
            <ArrowUpFromLine :size="19" /> 出库
          </button>
          <button class="inline-flex h-10 items-center justify-center gap-2 rounded-[8px] border border-line text-[14px] font-medium text-ink/80" @click="emit('adjustQuantity')">
            <SlidersHorizontal :size="17" /> 调整
          </button>
          <button class="inline-flex h-10 items-center justify-center gap-2 rounded-[8px] border border-line text-[14px] font-medium" :class="item.is_favorite ? 'bg-blue/10 text-blue' : 'text-ink/80'" @click="emit('favorite')">
            <Heart :size="17" /> {{ item.is_favorite ? '取消常用' : '常用' }}
          </button>
          <button class="inline-flex h-10 items-center justify-center gap-2 rounded-[8px] border border-line text-[14px] font-medium text-ink/80" @click="emit('edit')">
            <Pencil :size="17" /> 编辑
          </button>
          <button v-if="props.allowMove" class="col-span-2 inline-flex h-10 items-center justify-center gap-2 rounded-[8px] border border-line text-[14px] font-medium text-ink/80" @click="emit('move')">
            <MapPinned :size="17" /> 移动位置
          </button>
          <button class="col-span-2 inline-flex h-10 items-center justify-center gap-2 rounded-[8px] border border-amber/30 text-[14px] font-medium" :class="item.need_restock ? 'bg-amber/10 text-amber' : 'text-ink/80'" @click="emit('restock')">
            <PackageCheck :size="17" /> {{ item.need_restock ? '取消补货标记' : '标记补货' }}
          </button>
          <button class="col-span-2 inline-flex h-10 items-center justify-center gap-2 rounded-[8px] border border-red-200 bg-red-50 text-[14px] font-medium text-red-600" @click="emit('delete')">
            <Trash2 :size="17" /> 删除物品
          </button>
        </div>
      </div>

      <ExtensionActionSlot place="item.detail.actions" :context="{ item_id: item.id, item_code: item.code }" />

      <div class="mt-4 border-t border-line pt-3 2xl:mt-5 2xl:pt-4">
        <div class="mb-3 flex items-center justify-between">
          <h3 class="inline-flex items-center gap-2 text-[15px] font-semibold"><Paperclip :size="17" />附件</h3>
          <label class="inline-flex h-8 cursor-pointer items-center gap-1 rounded-[6px] border border-line px-3 text-[13px] text-ink/80 hover:border-blue hover:text-blue">
            <Upload :size="15" /> 上传
            <input type="file" class="hidden" @change="onAttachmentChange" />
          </label>
        </div>
        <div class="mb-2 text-[12px] text-muted">用于存放手册、数据表、说明文档等资料；封面图片不会显示在这里。</div>
        <div class="overflow-hidden rounded-[8px] border border-line">
          <div v-for="attachment in documentAttachments" :key="attachment.id" class="flex items-center justify-between gap-3 border-b border-line px-4 py-3 last:border-b-0">
            <div class="min-w-0">
              <div class="truncate text-[14px] font-medium">{{ attachment.original_name }}</div>
              <div class="text-[12px] text-muted">{{ attachment.mime_type || '未知类型' }}</div>
            </div>
            <div class="flex shrink-0 gap-2">
              <button v-if="canPreviewAttachment(attachment)" class="grid h-8 w-8 place-items-center rounded-[6px] border border-line text-ink/70" title="预览" @click="previewAttachment(attachment)">
                <ScrollText :size="15" />
              </button>
              <button class="grid h-8 w-8 place-items-center rounded-[6px] border border-line text-blue" title="下载" @click="downloadAttachment(attachment)">
                <ArrowDownToLine :size="15" />
              </button>
              <button class="grid h-8 w-8 place-items-center rounded-[6px] border border-red-200 text-red-600" title="删除" @click="emit('deleteAttachment', attachment.id)">
                <Trash2 :size="15" />
              </button>
            </div>
          </div>
          <div v-if="!documentAttachments.length" class="px-4 py-6 text-[14px] text-muted">暂无附件</div>
        </div>
      </div>

      <div class="mt-4 border-t border-line pt-3 2xl:mt-5 2xl:pt-4">
        <div class="mb-3 flex items-center justify-between">
          <h3 class="text-[15px] font-semibold">库存记录</h3>
          <button v-if="hasMoreNotes" class="text-[13px] text-blue" @click="showAllNotes = !showAllNotes">
            {{ showAllNotes ? '收起' : `查看全部 ${store.selectedNotes.length} 条` }}
          </button>
        </div>
        <div class="overflow-hidden rounded-[8px] border border-line">
          <div v-for="note in visibleNotes" :key="note.id" class="border-b border-line px-4 py-3 last:border-b-0">
            <div class="text-[14px]">{{ note.content }}</div>
            <div class="mt-1 text-[12px] text-muted">{{ note.created_at }} · {{ note.source }}</div>
          </div>
          <div v-if="!store.selectedNotes.length" class="px-4 py-6 text-[14px] text-muted">暂无记录</div>
        </div>
      </div>
    </div>

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
  </section>
</template>
