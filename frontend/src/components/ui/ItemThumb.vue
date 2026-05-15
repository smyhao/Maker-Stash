<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { Cpu, Package, ScrollText, Wrench } from 'lucide-vue-next'

import { downloadAttachmentFile } from '@/api/items'
import type { Item } from '@/types'

const props = defineProps<{ item: Item }>()
const imageUrl = ref<string | null>(null)

function clearImage() {
  if (imageUrl.value) URL.revokeObjectURL(imageUrl.value)
  imageUrl.value = null
}

watch(
  () => props.item.cover_attachment_id,
  async (attachmentId) => {
    clearImage()
    if (!attachmentId) return
    try {
      const blob = await downloadAttachmentFile(attachmentId)
      imageUrl.value = URL.createObjectURL(blob)
    } catch {
      imageUrl.value = null
    }
  },
  { immediate: true },
)

onBeforeUnmount(clearImage)
</script>

<template>
  <span class="grid h-[56px] w-[74px] shrink-0 place-items-center overflow-hidden rounded-[8px] border border-line bg-gradient-to-br from-white to-slate-100">
    <img v-if="imageUrl" :src="imageUrl" :alt="item.name" class="h-full w-full object-cover" />
    <Cpu v-else-if="item.code.startsWith('ELE')" :size="32" class="text-slate-700" />
    <Wrench v-else-if="item.code.startsWith('TOOL')" :size="32" class="text-slate-700" />
    <ScrollText v-else-if="item.code.startsWith('FIL')" :size="34" class="text-slate-900" />
    <Package v-else :size="32" class="text-slate-700" />
  </span>
</template>
