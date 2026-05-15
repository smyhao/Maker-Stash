<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { X } from 'lucide-vue-next'

import type { Item } from '@/types'

const props = defineProps<{
  open: boolean
  item: Item | null
  attachmentCount: number
  busy?: boolean
}>()

const emit = defineEmits<{
  close: []
  confirm: [deleteAttachments: boolean]
}>()

const deleteAttachments = ref(false)
const hasAttachments = computed(() => props.attachmentCount > 0)

watch(
  () => props.open,
  (open) => {
    if (open) deleteAttachments.value = false
  },
)
</script>

<template>
  <div v-if="open && item" class="fixed inset-0 z-40 grid place-items-center bg-ink/25 px-4">
    <section class="w-full max-w-[460px] rounded-[8px] border border-line bg-white shadow-soft">
      <header class="flex h-14 items-center justify-between border-b border-line px-5">
        <h2 class="text-[18px] font-semibold">删除物品</h2>
        <button type="button" class="grid h-9 w-9 place-items-center rounded-[6px] text-muted hover:bg-slate-50" @click="emit('close')">
          <X :size="20" />
        </button>
      </header>

      <div class="space-y-4 p-5 text-[14px]">
        <p>
          将删除 <b>{{ item.name }}</b>。系统会先归档物品记录，后续默认不在库存里显示。
        </p>
        <label v-if="hasAttachments" class="flex gap-3 rounded-[8px] border border-amber/30 bg-amber/10 p-3 text-amber">
          <input v-model="deleteAttachments" type="checkbox" class="mt-1" />
          <span>
            同时删除 {{ attachmentCount }} 个附件。这个选择会影响附件文件，请确认不再需要它们。
          </span>
        </label>
        <p v-else class="text-muted">当前物品没有附件，删除时不会触发附件清理。</p>
      </div>

      <footer class="flex justify-end gap-3 border-t border-line px-5 py-4">
        <button type="button" class="h-10 rounded-[8px] border border-line px-4 text-[14px]" @click="emit('close')">取消</button>
        <button type="button" :disabled="busy" class="h-10 rounded-[8px] bg-red-600 px-5 text-[14px] font-medium text-white disabled:opacity-50" @click="emit('confirm', deleteAttachments)">
          删除
        </button>
      </footer>
    </section>
  </div>
</template>
