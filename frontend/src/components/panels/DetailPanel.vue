<script setup lang="ts">
import { computed } from 'vue'
import { ArrowDownToLine, ArrowUpFromLine, Heart, MapPinned, PackageCheck, Paperclip, Pencil, Trash2, Upload, X } from 'lucide-vue-next'

import StatusDot from '@/components/ui/StatusDot.vue'
import { downloadAttachmentFile } from '@/api/items'
import { useInventoryStore } from '@/stores/inventory'
import type { Attachment } from '@/types'

const store = useInventoryStore()
const emit = defineEmits<{
  addQuantity: []
  useQuantity: []
  edit: []
  delete: []
  favorite: []
  restock: []
  editTags: []
  editAttributes: []
  move: []
  uploadAttachment: [file: File]
  deleteAttachment: [id: number]
}>()

const item = computed(() => store.selectedItem)
const category = computed(() => (item.value?.category_id ? store.categoryById.get(item.value.category_id)?.name : '未分类'))
const location = computed(() => (item.value?.location_id ? store.locationById.get(item.value.location_id)?.full_code : item.value?.location_text))

function onAttachmentChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) emit('uploadAttachment', file)
  input.value = ''
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
      <div class="grid h-[112px] place-items-center rounded-[8px] border border-line bg-gradient-to-br from-white to-slate-100 2xl:h-[144px]">
        <div class="h-[70px] w-[120px] rounded-full bg-[radial-gradient(circle_at_center,#16191f_0,#16191f_40%,#2a2f36_42%,#0c0d10_64%,transparent_65%)] shadow-soft 2xl:h-[88px] 2xl:w-[150px]"></div>
      </div>

      <dl class="mt-3 grid grid-cols-[78px_1fr] gap-y-2 text-[14px] 2xl:mt-4 2xl:grid-cols-[92px_1fr] 2xl:gap-y-3">
        <dt class="text-muted">类型</dt><dd>{{ category }}</dd>
        <dt class="text-muted">编号</dt><dd>{{ item.code }}</dd>
        <dt class="text-muted">数量</dt><dd><b>{{ item.quantity ?? '—' }}</b> {{ item.unit }}</dd>
        <dt class="text-muted">位置</dt><dd>{{ item.location_text || location || '未记录' }}</dd>
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
          <button class="inline-flex h-10 items-center justify-center gap-2 rounded-[8px] border border-line text-[14px] font-medium" :class="item.is_favorite ? 'bg-blue/10 text-blue' : 'text-ink/80'" @click="emit('favorite')">
            <Heart :size="17" /> {{ item.is_favorite ? '取消常用' : '常用' }}
          </button>
          <button class="inline-flex h-10 items-center justify-center gap-2 rounded-[8px] border border-line text-[14px] font-medium text-ink/80" @click="emit('edit')">
            <Pencil :size="17" /> 编辑
          </button>
          <button class="col-span-2 inline-flex h-10 items-center justify-center gap-2 rounded-[8px] border border-line text-[14px] font-medium text-ink/80" @click="emit('move')">
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

      <div class="mt-4 border-t border-line pt-3 2xl:mt-5 2xl:pt-4">
        <div class="mb-3 flex items-center justify-between">
          <h3 class="inline-flex items-center gap-2 text-[15px] font-semibold"><Paperclip :size="17" />附件</h3>
          <label class="inline-flex h-8 cursor-pointer items-center gap-1 rounded-[6px] border border-line px-3 text-[13px] text-ink/80 hover:border-blue hover:text-blue">
            <Upload :size="15" /> 上传
            <input type="file" class="hidden" @change="onAttachmentChange" />
          </label>
        </div>
        <div class="overflow-hidden rounded-[8px] border border-line">
          <div v-for="attachment in store.selectedAttachments" :key="attachment.id" class="flex items-center justify-between gap-3 border-b border-line px-4 py-3 last:border-b-0">
            <div class="min-w-0">
              <div class="truncate text-[14px] font-medium">{{ attachment.original_name }}</div>
              <div class="text-[12px] text-muted">{{ attachment.mime_type || '未知类型' }}</div>
            </div>
            <div class="flex shrink-0 gap-2">
              <button class="grid h-8 w-8 place-items-center rounded-[6px] border border-line text-blue" title="下载" @click="downloadAttachment(attachment)">
                <ArrowDownToLine :size="15" />
              </button>
              <button class="grid h-8 w-8 place-items-center rounded-[6px] border border-red-200 text-red-600" title="删除" @click="emit('deleteAttachment', attachment.id)">
                <Trash2 :size="15" />
              </button>
            </div>
          </div>
          <div v-if="!store.selectedAttachments.length" class="px-4 py-6 text-[14px] text-muted">暂无附件</div>
        </div>
      </div>

      <div class="mt-4 border-t border-line pt-3 2xl:mt-5 2xl:pt-4">
        <div class="mb-3 flex items-center justify-between">
          <h3 class="text-[15px] font-semibold">库存记录</h3>
          <button class="text-[13px] text-blue">查看全部</button>
        </div>
        <div class="overflow-hidden rounded-[8px] border border-line">
          <div v-for="note in store.selectedNotes" :key="note.id" class="border-b border-line px-4 py-3 last:border-b-0">
            <div class="text-[14px]">{{ note.content }}</div>
            <div class="mt-1 text-[12px] text-muted">{{ note.created_at }} · {{ note.source }}</div>
          </div>
          <div v-if="!store.selectedNotes.length" class="px-4 py-6 text-[14px] text-muted">暂无记录</div>
        </div>
      </div>
    </div>
  </section>
</template>
