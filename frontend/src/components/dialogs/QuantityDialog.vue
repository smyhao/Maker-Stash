<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import { X } from 'lucide-vue-next'

const props = defineProps<{
  open: boolean
  mode: 'add' | 'use' | 'adjust'
  unit: string | null
  busy?: boolean
}>()

const emit = defineEmits<{
  close: []
  submit: [amount: number, note: string]
}>()

const form = reactive({
  amount: '1',
  note: '',
})

const title = computed(() => {
  if (props.mode === 'add') return '入库'
  if (props.mode === 'use') return '出库'
  return '调整库存'
})
const actionClass = computed(() => {
  if (props.mode === 'add') return 'bg-blue text-white'
  if (props.mode === 'use') return 'bg-orange-600 text-white'
  return 'bg-slate-900 text-white'
})
const amountLabel = computed(() => (props.mode === 'adjust' ? `目标数量${props.unit ? `（${props.unit}）` : ''}` : `数量${props.unit ? `（${props.unit}）` : ''}`))

watch(
  () => props.open,
  (open) => {
    if (!open) return
    form.amount = '1'
    form.note = props.mode === 'add'
      ? '手动入库'
      : props.mode === 'use'
        ? '手动出库'
        : '手动调整库存'
  },
)

function submit() {
  const amount = Number(form.amount)
  if (!Number.isFinite(amount)) return
  if (props.mode === 'adjust' ? amount < 0 : amount <= 0) return
  emit('submit', amount, form.note.trim())
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-40 grid place-items-center bg-ink/25 px-4">
    <form class="w-full max-w-[420px] rounded-[8px] border border-line bg-white shadow-soft" @submit.prevent="submit">
      <header class="flex h-14 items-center justify-between border-b border-line px-5">
        <h2 class="text-[18px] font-semibold">{{ title }}</h2>
        <button type="button" class="grid h-9 w-9 place-items-center rounded-[6px] text-muted hover:bg-slate-50" @click="emit('close')">
          <X :size="20" />
        </button>
      </header>
      <div class="space-y-4 p-5">
        <label>
          <span class="mb-1 block text-[13px] text-muted">{{ amountLabel }}</span>
          <input v-model="form.amount" type="number" :min="props.mode === 'adjust' ? '0' : '0.001'" step="0.001" required class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue" />
        </label>
        <label>
          <span class="mb-1 block text-[13px] text-muted">记录</span>
          <input v-model="form.note" class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue" />
        </label>
      </div>
      <footer class="flex justify-end gap-3 border-t border-line px-5 py-4">
        <button type="button" class="h-10 rounded-[8px] border border-line px-4 text-[14px]" @click="emit('close')">取消</button>
        <button type="submit" :disabled="busy" class="h-10 rounded-[8px] px-5 text-[14px] font-medium disabled:opacity-50" :class="actionClass">
          确认{{ title }}
        </button>
      </footer>
    </form>
  </div>
</template>
