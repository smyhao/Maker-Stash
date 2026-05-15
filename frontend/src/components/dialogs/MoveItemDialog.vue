<script setup lang="ts">
import { ref, watch } from 'vue'
import { X } from 'lucide-vue-next'

import { useInventoryStore } from '@/stores/inventory'

const props = defineProps<{
  open: boolean
  busy?: boolean
}>()

const emit = defineEmits<{
  close: []
  submit: [locationCode: string | null, locationText: string | null]
}>()

const store = useInventoryStore()
const locationCode = ref('')
const locationText = ref('')

watch(
  () => props.open,
  (open) => {
    if (!open) return
    const item = store.selectedItem
    locationCode.value = item?.location_id ? store.locationById.get(item.location_id)?.full_code || '' : ''
    locationText.value = item?.location_text || ''
  },
)
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-40 grid place-items-center bg-ink/25 px-4">
    <form class="w-full max-w-[460px] rounded-[8px] border border-line bg-white shadow-soft" @submit.prevent="emit('submit', locationCode || null, locationText || null)">
      <header class="flex h-14 items-center justify-between border-b border-line px-5">
        <h2 class="text-[18px] font-semibold">移动位置</h2>
        <button type="button" class="grid h-9 w-9 place-items-center rounded-[6px] text-muted hover:bg-slate-50" @click="emit('close')">
          <X :size="20" />
        </button>
      </header>

      <div class="space-y-4 p-5">
        <label>
          <span class="mb-1 block text-[13px] text-muted">绑定位置</span>
          <select v-model="locationCode" class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue">
            <option value="">不绑定结构化位置</option>
            <option v-for="location in store.flatLocations" :key="location.id" :value="location.full_code">
              {{ `${'　'.repeat(location.depth)}${location.name} (${location.full_code})` }}
            </option>
          </select>
        </label>
        <label>
          <span class="mb-1 block text-[13px] text-muted">位置备注</span>
          <input v-model="locationText" class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue" placeholder="例如：格 03 / 抽屉 02" />
        </label>
      </div>

      <footer class="flex justify-end gap-3 border-t border-line px-5 py-4">
        <button type="button" class="h-10 rounded-[8px] border border-line px-4 text-[14px]" @click="emit('close')">取消</button>
        <button type="submit" :disabled="busy" class="h-10 rounded-[8px] bg-blue px-5 text-[14px] font-medium text-white disabled:opacity-50">保存</button>
      </footer>
    </form>
  </div>
</template>
