<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import { Container, Grid2X2, X } from 'lucide-vue-next'

import type { ContainerCreatePayload, ContainerLayoutPayload, Item, LocationNode, SlotAssignment } from '@/types'
import { useInventoryStore } from '@/stores/inventory'

const props = defineProps<{
  open: boolean
  mode: 'create' | 'convert' | 'edit'
  location: LocationNode | null
  items: Item[]
  busy?: boolean
}>()

const emit = defineEmits<{
  close: []
  create: [payload: ContainerCreatePayload]
  convert: [id: number, payload: ContainerLayoutPayload & { assignments: SlotAssignment[] }]
  edit: [id: number, payload: ContainerLayoutPayload]
}>()

const store = useInventoryStore()
const form = reactive({
  name: '',
  code: '',
  parentCode: '',
  layoutType: 'grid' as 'grid' | 'row',
  rows: 3,
  columns: 5,
  colorChoice: 'sage',
  customColor: '#5F7F67',
  icon: 'box' as 'box' | 'drawer' | 'shelf',
  assignments: {} as Record<string, string>,
})

const PRESET_COLORS: Record<string, string> = {
  sage: '#5F7F67',
  clay: '#C56A45',
  sand: '#C9AD7A',
  ink: '#29313A',
}

const title = computed(() => {
  if (props.mode === 'edit') return '编辑收纳盒布局'
  if (props.mode === 'convert') return '配置为收纳盒'
  return '新建收纳盒'
})
const slotKeys = computed(() => {
  const rows = form.layoutType === 'row' ? 1 : form.rows
  return Array.from({ length: rows }).flatMap((_, row) =>
    Array.from({ length: form.columns }, (__, column) =>
      form.layoutType === 'row'
        ? String(column + 1).padStart(2, '0')
        : `${String.fromCharCode(65 + row)}${String(column + 1).padStart(2, '0')}`,
    ),
  )
})
const assignedSlots = computed(() => Object.values(form.assignments).filter(Boolean))
const assignmentComplete = computed(() =>
  props.mode !== 'convert'
    || (props.items.every((item) => Boolean(form.assignments[item.code])) && new Set(assignedSlots.value).size === assignedSlots.value.length),
)
const availableParents = computed(() => store.flatLocations.filter((location) => !location.is_slot && !location.layout_type))
const selectedColor = computed(() => form.colorChoice === 'custom' ? normalizeCustomColor(form.customColor) : form.colorChoice)
const previewColor = computed(() => resolveColor(selectedColor.value))
const previewStyle = computed(() => ({
  backgroundColor: withAlpha(previewColor.value, 0.1),
  borderColor: withAlpha(previewColor.value, 0.28),
}))
const previewSlotStyle = computed(() => ({
  borderColor: withAlpha(previewColor.value, 0.32),
}))

watch(
  () => [props.open, props.location, props.mode] as const,
  () => {
    if (!props.open) return
    form.name = props.location?.name || ''
    form.code = props.mode === 'create' ? '' : props.location?.code || ''
    const proposedParent = props.location?.layout_type
      ? availableParents.value.find((parent) => parent.id === props.location?.parent_id)?.full_code
      : props.location?.full_code
    form.parentCode = props.mode === 'create' ? proposedParent || 'WS' : ''
    form.layoutType = props.location?.layout_type || 'grid'
    form.rows = props.location?.layout_rows || 3
    form.columns = props.location?.layout_columns || 5
    const color = props.location?.appearance_color || 'sage'
    if (PRESET_COLORS[color]) {
      form.colorChoice = color
      form.customColor = PRESET_COLORS[color]
    } else {
      form.colorChoice = 'custom'
      form.customColor = normalizeCustomColor(color)
    }
    form.icon = props.location?.appearance_icon || 'box'
    form.assignments = {}
  },
  { immediate: true },
)

function normalizeCode(value: string) {
  return value.trim().toUpperCase().replace(/\s+/g, '-').replace(/[^A-Z0-9_-]/g, '')
}

function layoutPayload(): ContainerLayoutPayload {
  return {
    layout_type: form.layoutType,
    layout_rows: form.layoutType === 'row' ? 1 : form.rows,
    layout_columns: form.columns,
    appearance_color: selectedColor.value,
    appearance_icon: form.icon,
  }
}

function submit() {
  const layout = layoutPayload()
  if (props.mode === 'edit' && props.location) {
    emit('edit', props.location.id, layout)
    return
  }
  if (props.mode === 'convert' && props.location) {
    emit('convert', props.location.id, {
      ...layout,
      assignments: props.items.map((item) => ({ item_code: item.code, slot_key: form.assignments[item.code] })),
    })
    return
  }
  emit('create', {
    ...layout,
    name: form.name.trim(),
    code: normalizeCode(form.code),
    parent_code: form.parentCode || null,
    type: 'box',
  })
}

function normalizeCustomColor(value: string) {
  const color = value.trim()
  if (/^#[0-9A-Fa-f]{6}$/.test(color)) return color.toUpperCase()
  return '#5F7F67'
}

function resolveColor(value: string) {
  return PRESET_COLORS[value] || normalizeCustomColor(value)
}

function withAlpha(hex: string, alpha: number) {
  const normalized = normalizeCustomColor(hex).slice(1)
  const red = parseInt(normalized.slice(0, 2), 16)
  const green = parseInt(normalized.slice(2, 4), 16)
  const blue = parseInt(normalized.slice(4, 6), 16)
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-50 grid place-items-center bg-ink/30 p-4">
    <form class="max-h-[92vh] w-full max-w-[820px] overflow-y-auto rounded-2xl border border-line bg-white shadow-soft" @submit.prevent="submit">
      <header class="flex items-start justify-between border-b border-line px-6 py-5">
        <div>
          <h2 class="text-[20px] font-semibold">{{ title }}</h2>
          <p v-if="mode === 'convert' && items.length" class="mt-1 text-[13px] text-muted">
            当前位置已有 {{ items.length }} 个物品，全部分配格位后才能启用布局。
          </p>
        </div>
        <button type="button" class="grid h-9 w-9 place-items-center rounded-lg text-muted hover:bg-wash" @click="emit('close')"><X :size="19" /></button>
      </header>

      <div class="grid gap-6 p-6 lg:grid-cols-[280px_1fr]">
        <div class="space-y-4">
          <label v-if="mode === 'create'" class="block">
            <span class="mb-1 block text-[13px] text-muted">名称</span>
            <input v-model="form.name" required class="h-11 w-full rounded-xl border border-line px-3 outline-none focus:border-green" placeholder="透明分格盒 A" />
          </label>
          <label v-if="mode === 'create'" class="block">
            <span class="mb-1 block text-[13px] text-muted">父位置</span>
            <select v-model="form.parentCode" class="h-11 w-full rounded-xl border border-line px-3 outline-none focus:border-green">
              <option value="">无</option>
              <option v-for="parent in availableParents" :key="parent.id" :value="parent.full_code">{{ parent.name }} ({{ parent.full_code }})</option>
            </select>
          </label>
          <label v-if="mode === 'create'" class="block">
            <span class="mb-1 block text-[13px] text-muted">编号</span>
            <input v-model="form.code" required class="h-11 w-full rounded-xl border border-line px-3 outline-none focus:border-green" placeholder="BOX-01" @blur="form.code = normalizeCode(form.code)" />
          </label>
          <div>
            <span class="mb-2 block text-[13px] text-muted">布局模板</span>
            <div class="grid grid-cols-2 gap-2">
              <button type="button" class="flex h-11 items-center justify-center gap-2 rounded-xl border text-[14px]" :class="form.layoutType === 'grid' ? 'border-green bg-green/10 text-green' : 'border-line'" @click="form.layoutType = 'grid'">
                <Grid2X2 :size="17" /> 网格
              </button>
              <button type="button" class="flex h-11 items-center justify-center gap-2 rounded-xl border text-[14px]" :class="form.layoutType === 'row' ? 'border-green bg-green/10 text-green' : 'border-line'" @click="form.layoutType = 'row'">
                <Container :size="17" /> 单排
              </button>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <label v-if="form.layoutType === 'grid'">
              <span class="mb-1 block text-[13px] text-muted">行数</span>
              <input v-model.number="form.rows" type="number" min="1" max="26" class="h-11 w-full rounded-xl border border-line px-3 focus:border-green" />
            </label>
            <label>
              <span class="mb-1 block text-[13px] text-muted">列 / 格数</span>
              <input v-model.number="form.columns" type="number" min="1" max="30" class="h-11 w-full rounded-xl border border-line px-3 focus:border-green" />
            </label>
          </div>
          <label class="block">
            <span class="mb-1 block text-[13px] text-muted">外观颜色</span>
            <select v-model="form.colorChoice" class="h-11 w-full rounded-xl border border-line px-3">
              <option value="sage">鼠尾草绿</option>
              <option value="clay">陶土橙</option>
              <option value="sand">砂岩色</option>
              <option value="ink">墨色</option>
              <option value="custom">自定义 RGB</option>
            </select>
          </label>
          <label v-if="form.colorChoice === 'custom'" class="block">
            <span class="mb-1 block text-[13px] text-muted">RGB 编号（#RRGGBB）</span>
            <div class="flex items-center gap-2">
              <input v-model="form.customColor" type="color" class="h-11 w-14 rounded-xl border border-line bg-white p-1" />
              <input v-model="form.customColor" class="h-11 min-w-0 flex-1 rounded-xl border border-line px-3 font-mono text-[13px] outline-none focus:border-green" placeholder="#5F7F67" @blur="form.customColor = normalizeCustomColor(form.customColor)" />
            </div>
          </label>
          <label class="block">
            <span class="mb-1 block text-[13px] text-muted">容器图标</span>
            <select v-model="form.icon" class="h-11 w-full rounded-xl border border-line px-3">
              <option value="box">分格盒</option>
              <option value="drawer">抽屉</option>
              <option value="shelf">层板</option>
            </select>
          </label>
        </div>

        <div>
          <div class="mb-3 flex items-center justify-between">
            <h3 class="text-[15px] font-semibold">{{ mode === 'convert' && items.length ? '分配现有物品' : '格位预览' }}</h3>
            <span class="text-[12px] text-muted">{{ slotKeys.length }} 个格位</span>
          </div>
          <div v-if="mode === 'convert' && items.length" class="mb-4 space-y-2">
            <label v-for="item in items" :key="item.code" class="grid grid-cols-[1fr_112px] items-center gap-3 rounded-xl border border-line bg-wash px-3 py-2">
              <span class="min-w-0">
                <span class="block truncate text-[14px] font-medium">{{ item.name }}</span>
                <span class="text-[12px] text-muted">{{ item.code }} · {{ item.quantity ?? '-' }} {{ item.unit || '' }}</span>
              </span>
              <select v-model="form.assignments[item.code]" class="h-9 rounded-lg border border-line bg-white px-2 text-[13px]">
                <option value="">选择格位</option>
                <option v-for="key in slotKeys" :key="key" :value="key" :disabled="assignedSlots.includes(key) && form.assignments[item.code] !== key">{{ key }}</option>
              </select>
            </label>
          </div>
          <div class="grid gap-2 rounded-2xl border p-3" :style="{ ...previewStyle, gridTemplateColumns: `repeat(${form.columns}, minmax(0, 1fr))` }">
            <div v-for="key in slotKeys" :key="key" class="grid min-h-14 place-items-center rounded-lg border border-dashed bg-white text-[12px] font-medium text-muted" :style="previewSlotStyle">
              {{ key }}
            </div>
          </div>
        </div>
      </div>

      <footer class="flex flex-wrap items-center justify-between gap-3 border-t border-line px-6 py-4">
        <span v-if="mode === 'convert' && items.length" class="text-[13px]" :class="assignmentComplete ? 'text-green' : 'text-clay'">
          已分配 {{ assignedSlots.length }} / {{ items.length }}，全部分配后才能启用。
        </span>
        <span v-else class="text-[13px] text-muted">格位编号创建后保持稳定，便于实物贴标。</span>
        <div class="ml-auto flex gap-3">
          <button type="button" class="h-10 rounded-xl border border-line px-4 text-[14px]" @click="emit('close')">取消</button>
          <button type="submit" :disabled="busy || !assignmentComplete || (mode === 'create' && (!form.name.trim() || !form.code.trim()))" class="h-10 rounded-xl bg-green px-5 text-[14px] font-medium text-white disabled:opacity-45">
            {{ mode === 'edit' ? '保存布局' : '启用收纳盒' }}
          </button>
        </div>
      </footer>
    </form>
  </div>
</template>
