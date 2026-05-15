<script setup lang="ts">
import { ref, watch } from 'vue'
import { Trash2, X } from 'lucide-vue-next'

import type { Tag } from '@/types'

const props = defineProps<{
  open: boolean
  tags: Tag[]
  busy?: boolean
}>()

const emit = defineEmits<{
  close: []
  add: [tags: string[]]
  remove: [tag: string]
}>()

const input = ref('')

watch(
  () => props.open,
  (open) => {
    if (open) input.value = ''
  },
)

function addTags() {
  const tags = input.value
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean)
  if (!tags.length) return
  emit('add', tags)
  input.value = ''
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-40 grid place-items-center bg-ink/25 px-4">
    <section class="w-full max-w-[460px] rounded-[8px] border border-line bg-white shadow-soft">
      <header class="flex h-14 items-center justify-between border-b border-line px-5">
        <h2 class="text-[18px] font-semibold">编辑标签</h2>
        <button type="button" class="grid h-9 w-9 place-items-center rounded-[6px] text-muted hover:bg-slate-50" @click="emit('close')">
          <X :size="20" />
        </button>
      </header>

      <div class="space-y-4 p-5">
        <form class="flex gap-2" @submit.prevent="addTags">
          <input v-model="input" class="h-10 min-w-0 flex-1 rounded-[8px] border border-line px-3 outline-none focus:border-blue" placeholder="多个标签用英文逗号分隔" />
          <button type="submit" :disabled="busy" class="h-10 rounded-[8px] bg-blue px-4 text-[14px] font-medium text-white disabled:opacity-50">添加</button>
        </form>

        <div class="overflow-hidden rounded-[8px] border border-line">
          <div v-for="tag in tags" :key="tag.id" class="flex items-center justify-between border-b border-line px-4 py-3 last:border-b-0">
            <span class="text-[14px]">{{ tag.name }}</span>
            <button class="grid h-8 w-8 place-items-center rounded-[6px] border border-red-200 text-red-600" :disabled="busy" @click="emit('remove', tag.name)">
              <Trash2 :size="15" />
            </button>
          </div>
          <div v-if="!tags.length" class="px-4 py-6 text-[14px] text-muted">暂无标签</div>
        </div>
      </div>
    </section>
  </div>
</template>
