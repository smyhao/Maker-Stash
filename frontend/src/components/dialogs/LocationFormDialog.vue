<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { X } from 'lucide-vue-next'

import type { LocationFormPayload, LocationNode } from '@/types'
import { useInventoryStore } from '@/stores/inventory'

const props = defineProps<{
  open: boolean
  mode: 'create' | 'edit'
  location: (LocationNode & { depth?: number }) | null
  busy?: boolean
}>()

const emit = defineEmits<{
  close: []
  submit: [payload: LocationFormPayload]
}>()

const store = useInventoryStore()
const title = computed(() => (props.mode === 'create' ? '新增位置' : '编辑位置'))
const codeHint = computed(() => (props.mode === 'create' ? '留空会自动生成编号' : '编号创建后不可修改'))
const formError = ref('')

const form = reactive({
  name: '',
  code: '',
  parentCode: '',
  type: '',
  description: '',
  sortOrder: '0',
})

watch(
  () => [props.open, props.location, props.mode] as const,
  () => {
    if (!props.open) return
    form.name = props.location?.name || ''
    form.code = props.mode === 'edit' ? props.location?.code || '' : ''
    form.parentCode = props.mode === 'create' ? props.location?.full_code || '' : ''
    form.type = props.location?.type || ''
    form.description = props.location?.description || ''
    form.sortOrder = String(props.location?.sort_order || 0)
    formError.value = ''
  },
  { immediate: true },
)

function normalizeCode(value: string) {
  return value.trim().toUpperCase().replace(/\s+/g, '-').replace(/[^A-Z0-9._-]/g, '')
}

function autoCode() {
  const suffix = Date.now().toString(36).toUpperCase().slice(-6)
  return `LOC-${suffix}`
}

function submit() {
  formError.value = ''
  const code = normalizeCode(form.code) || autoCode()
  if (props.mode === 'create' && !/^[A-Z0-9._-]+$/.test(code)) {
    formError.value = '编号只能包含 A-Z、0-9、点、横线和下划线'
    return
  }
  emit('submit', {
    name: form.name.trim(),
    code,
    parent_code: form.parentCode || null,
    type: form.type || null,
    description: form.description.trim() || null,
    sort_order: Number(form.sortOrder) || 0,
  })
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-40 grid place-items-center bg-ink/25 px-4">
    <form class="w-full max-w-[520px] rounded-[8px] border border-line bg-white shadow-soft" @submit.prevent="submit">
      <header class="flex h-14 items-center justify-between border-b border-line px-5">
        <h2 class="text-[18px] font-semibold">{{ title }}</h2>
        <button type="button" class="grid h-9 w-9 place-items-center rounded-[6px] text-muted hover:bg-slate-50" @click="emit('close')">
          <X :size="20" />
        </button>
      </header>

      <div class="grid gap-4 p-5 sm:grid-cols-2">
        <label>
          <span class="mb-1 block text-[13px] text-muted">名称</span>
          <input v-model="form.name" required class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue" />
        </label>

        <label>
          <span class="mb-1 block text-[13px] text-muted">编号</span>
          <input v-model="form.code" :disabled="mode === 'edit'" class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue disabled:bg-slate-50" placeholder="DRY-A" @blur="form.code = normalizeCode(form.code)" />
          <span class="mt-1 block text-[12px] text-muted">{{ codeHint }}</span>
        </label>

        <label>
          <span class="mb-1 block text-[13px] text-muted">父位置</span>
          <select v-model="form.parentCode" :disabled="mode === 'edit'" class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue disabled:bg-slate-50">
            <option value="">无</option>
            <option v-for="location in store.flatLocations" :key="location.id" :value="location.full_code">
              {{ `${'　'.repeat(location.depth)}${location.name} (${location.full_code})` }}
            </option>
          </select>
        </label>

        <label>
          <span class="mb-1 block text-[13px] text-muted">类型</span>
          <select v-model="form.type" class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue">
            <option value="">未设置</option>
            <option value="room">房间</option>
            <option value="cabinet">柜子</option>
            <option value="shelf">层架</option>
            <option value="box">盒子</option>
            <option value="bin">格位</option>
            <option value="wall">墙面</option>
            <option value="drybox">干燥箱</option>
          </select>
        </label>

        <label>
          <span class="mb-1 block text-[13px] text-muted">排序</span>
          <input v-model="form.sortOrder" type="number" class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue" />
        </label>

        <label class="sm:col-span-2">
          <span class="mb-1 block text-[13px] text-muted">描述</span>
          <textarea v-model="form.description" rows="3" class="w-full rounded-[8px] border border-line px-3 py-2 outline-none focus:border-blue" />
        </label>
      </div>

      <footer class="flex justify-end gap-3 border-t border-line px-5 py-4">
        <div v-if="formError" class="mr-auto self-center text-[13px] text-red-600">{{ formError }}</div>
        <button type="button" class="h-10 rounded-[8px] border border-line px-4 text-[14px]" @click="emit('close')">取消</button>
        <button type="submit" :disabled="busy || !form.name.trim()" class="h-10 rounded-[8px] bg-blue px-5 text-[14px] font-medium text-white disabled:opacity-50">
          保存
        </button>
      </footer>
    </form>
  </div>
</template>
