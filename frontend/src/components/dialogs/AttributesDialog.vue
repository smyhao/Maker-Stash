<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { Pencil, Trash2, X } from 'lucide-vue-next'

import type { ItemAttribute } from '@/types'

const props = defineProps<{
  open: boolean
  attributes: ItemAttribute[]
  busy?: boolean
}>()

const emit = defineEmits<{
  close: []
  create: [payload: { name: string; key: string; value?: string | null; unit?: string | null }]
  update: [id: number, payload: { name?: string; value?: string | null; unit?: string | null }]
  remove: [id: number]
}>()

const editingId = ref<number | null>(null)
const form = reactive({
  name: '',
  key: '',
  value: '',
  unit: '',
})

watch(
  () => props.open,
  (open) => {
    if (open) reset()
  },
)

function reset() {
  editingId.value = null
  form.name = ''
  form.key = ''
  form.value = ''
  form.unit = ''
}

function edit(attr: ItemAttribute) {
  editingId.value = attr.id
  form.name = attr.name
  form.key = attr.key
  form.value = attr.value || ''
  form.unit = attr.unit || ''
}

function normalizeKey(name: string) {
  return name.trim().toLowerCase().replace(/\s+/g, '_')
}

function submit() {
  const name = form.name.trim()
  if (!name) return
  const payload = {
    name,
    key: form.key.trim() || normalizeKey(name),
    value: form.value.trim() || null,
    unit: form.unit.trim() || null,
  }
  if (editingId.value) {
    emit('update', editingId.value, payload)
  } else {
    emit('create', payload)
  }
  reset()
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-40 grid place-items-center bg-ink/25 px-4">
    <section class="w-full max-w-[620px] rounded-[8px] border border-line bg-white shadow-soft">
      <header class="flex h-14 items-center justify-between border-b border-line px-5">
        <h2 class="text-[18px] font-semibold">编辑属性</h2>
        <button type="button" class="grid h-9 w-9 place-items-center rounded-[6px] text-muted hover:bg-slate-50" @click="emit('close')">
          <X :size="20" />
        </button>
      </header>

      <div class="space-y-4 p-5">
        <form class="grid gap-3 sm:grid-cols-[1fr_1fr_1fr_90px_auto]" @submit.prevent="submit">
          <input v-model="form.name" required class="h-10 rounded-[8px] border border-line px-3 outline-none focus:border-blue" placeholder="名称" />
          <input v-model="form.key" class="h-10 rounded-[8px] border border-line px-3 outline-none focus:border-blue" placeholder="键名" />
          <input v-model="form.value" class="h-10 rounded-[8px] border border-line px-3 outline-none focus:border-blue" placeholder="值" />
          <input v-model="form.unit" class="h-10 rounded-[8px] border border-line px-3 outline-none focus:border-blue" placeholder="单位" />
          <button type="submit" :disabled="busy" class="h-10 rounded-[8px] bg-blue px-4 text-[14px] font-medium text-white disabled:opacity-50">
            {{ editingId ? '更新' : '添加' }}
          </button>
        </form>

        <div class="overflow-hidden rounded-[8px] border border-line">
          <div v-for="attr in attributes" :key="attr.id" class="grid grid-cols-[1fr_1fr_auto] items-center gap-3 border-b border-line px-4 py-3 last:border-b-0">
            <div class="min-w-0">
              <div class="truncate text-[14px] font-medium">{{ attr.name }}</div>
              <div class="truncate text-[12px] text-muted">{{ attr.key }}</div>
            </div>
            <div class="truncate text-[14px]">{{ attr.value || '—' }}{{ attr.unit ? ` ${attr.unit}` : '' }}</div>
            <div class="flex gap-2">
              <button class="grid h-8 w-8 place-items-center rounded-[6px] border border-line text-blue" :disabled="busy" @click="edit(attr)">
                <Pencil :size="15" />
              </button>
              <button class="grid h-8 w-8 place-items-center rounded-[6px] border border-red-200 text-red-600" :disabled="busy" @click="emit('remove', attr.id)">
                <Trash2 :size="15" />
              </button>
            </div>
          </div>
          <div v-if="!attributes.length" class="px-4 py-6 text-[14px] text-muted">暂无属性</div>
        </div>
      </div>
    </section>
  </div>
</template>
