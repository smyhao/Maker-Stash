<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { X } from 'lucide-vue-next'

import type { Item, ItemFormPayload, Status } from '@/types'
import { useInventoryStore } from '@/stores/inventory'

const props = defineProps<{
  open: boolean
  mode: 'create' | 'edit'
  item: Item | null
  busy?: boolean
}>()

const emit = defineEmits<{
  close: []
  submit: [payload: ItemFormPayload]
}>()

const store = useInventoryStore()

const form = reactive({
  name: '',
  category: '',
  locationText: '',
  quantity: '',
  unit: '',
  status: 'normal' as Status,
  description: '',
  tags: '',
  note: '',
  needRestock: false,
  isFavorite: false,
})
const formError = ref('')

const title = computed(() => (props.mode === 'create' ? '快速添加' : '编辑物品'))
const categories = computed(() => store.flatCategories)
const quantityError = computed(() => {
  const value = form.quantity.trim()
  if (!value) return ''
  return parseQuantity(value) === null ? '数量格式不正确' : ''
})

watch(
  () => [props.open, props.item, props.mode] as const,
  () => {
    if (!props.open) return
    form.name = props.item?.name || ''
    form.category = props.mode === 'create'
      ? ''
      : props.item?.category_id
        ? String(props.item.category_id)
        : ''
    form.locationText = props.item?.location_text || ''
    form.quantity = props.item?.quantity == null ? '' : String(props.item.quantity)
    form.unit = props.item?.unit || ''
    form.status = props.item?.status || 'normal'
    form.description = props.item?.description || ''
    form.tags = store.selectedTags.map((tag) => tag.name).join(', ')
    form.note = ''
    form.needRestock = props.item?.need_restock || false
    form.isFavorite = props.item?.is_favorite || false
    formError.value = ''
  },
  { immediate: true },
)

function parseQuantity(value: string) {
  const normalized = value
    .trim()
    .replace(/，/g, '.')
    .replace(/,/g, '.')
    .replace(/[０-９]/g, (char) => String.fromCharCode(char.charCodeAt(0) - 0xff10 + 48))
  if (!normalized) return null
  const parsed = Number(normalized)
  return Number.isFinite(parsed) ? parsed : null
}

function submit() {
  formError.value = ''
  const quantity = form.quantity.trim() === '' ? null : parseQuantity(form.quantity)
  if (form.quantity.trim() && quantity === null) {
    formError.value = '数量格式不正确，请输入数字，例如 1、0.5、12.25'
    return
  }
  const tags = form.tags
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean)

  const payload: ItemFormPayload = {
    name: form.name.trim(),
    location_text: form.locationText.trim() || null,
    quantity,
    unit: form.unit.trim() || null,
    status: form.status,
    description: form.description.trim() || null,
    need_restock: form.needRestock,
    is_favorite: form.isFavorite,
  }

  if (props.mode === 'create') {
    payload.category = form.category || null
    payload.tags = tags
    payload.note = form.note.trim() || null
  } else {
    payload.category_id = form.category ? Number(form.category) : null
  }

  emit('submit', payload)
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-40 grid place-items-center bg-ink/25 px-4">
    <form class="w-full max-w-[560px] rounded-[8px] border border-line bg-white shadow-soft" @submit.prevent="submit">
      <header class="flex h-14 items-center justify-between border-b border-line px-5">
        <h2 class="text-[18px] font-semibold">{{ title }}</h2>
        <button type="button" class="grid h-9 w-9 place-items-center rounded-[6px] text-muted hover:bg-slate-50" @click="emit('close')">
          <X :size="20" />
        </button>
      </header>

      <div class="grid gap-4 p-5 sm:grid-cols-2">
        <label class="sm:col-span-2">
          <span class="mb-1 block text-[13px] text-muted">名称</span>
          <input v-model="form.name" required class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue" />
        </label>

        <label>
          <span class="mb-1 block text-[13px] text-muted">分类</span>
          <select v-model="form.category" class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue">
            <option value="">未分类</option>
            <option v-for="category in categories" :key="category.id" :value="mode === 'create' ? category.slug : String(category.id)">
              {{ `${'　'.repeat(category.depth)}${category.name}` }}
            </option>
          </select>
        </label>

        <label>
          <span class="mb-1 block text-[13px] text-muted">位置</span>
          <input v-model="form.locationText" class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue" placeholder="干燥箱 A · 格 03" />
        </label>

        <label>
          <span class="mb-1 block text-[13px] text-muted">数量</span>
          <input v-model="form.quantity" inputmode="decimal" class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue" placeholder="例如 1 / 0.5" />
          <span v-if="quantityError" class="mt-1 block text-[12px] text-red-600">{{ quantityError }}</span>
        </label>

        <label>
          <span class="mb-1 block text-[13px] text-muted">单位</span>
          <input v-model="form.unit" class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue" placeholder="kg / 个 / 套" />
        </label>

        <label>
          <span class="mb-1 block text-[13px] text-muted">状态</span>
          <select v-model="form.status" class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue">
            <option value="normal">正常</option>
            <option value="low">较低</option>
            <option value="empty">用尽</option>
            <option value="broken">损坏</option>
            <option value="missing">丢失</option>
          </select>
        </label>

        <label>
          <span class="mb-1 block text-[13px] text-muted">标签</span>
          <input v-model="form.tags" :disabled="mode === 'edit'" class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue disabled:bg-slate-50" placeholder="PLA, 1.75mm" />
        </label>

        <label class="sm:col-span-2">
          <span class="mb-1 block text-[13px] text-muted">备注</span>
          <textarea v-model="form.description" rows="3" class="w-full rounded-[8px] border border-line px-3 py-2 outline-none focus:border-blue" />
        </label>

        <div class="flex gap-5 text-[14px]">
          <label class="inline-flex items-center gap-2"><input v-model="form.needRestock" type="checkbox" /> 补货</label>
          <label class="inline-flex items-center gap-2"><input v-model="form.isFavorite" type="checkbox" /> 常用</label>
        </div>

        <label v-if="mode === 'create'">
          <span class="mb-1 block text-[13px] text-muted">入库记录</span>
          <input v-model="form.note" class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue" placeholder="首次录入" />
        </label>
      </div>

      <footer class="flex justify-end gap-3 border-t border-line px-5 py-4">
        <div v-if="formError" class="mr-auto self-center text-[13px] text-red-600">{{ formError }}</div>
        <button type="button" class="h-10 rounded-[8px] border border-line px-4 text-[14px]" @click="emit('close')">取消</button>
        <button type="submit" :disabled="busy || !form.name.trim() || !!quantityError" class="h-10 rounded-[8px] bg-blue px-5 text-[14px] font-medium text-white disabled:opacity-50">
          保存
        </button>
      </footer>
    </form>
  </div>
</template>
