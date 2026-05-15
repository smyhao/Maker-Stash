<script setup lang="ts">
import { reactive, watch } from 'vue'
import { X } from 'lucide-vue-next'

import { getApiConfig, setApiConfig } from '@/api/client'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  close: []
  saved: []
}>()

const form = reactive({
  apiUrl: '',
  token: '',
})

watch(
  () => props.open,
  (open) => {
    if (!open) return
    const config = getApiConfig()
    form.apiUrl = config.apiUrl || ''
    form.token = config.token || ''
  },
  { immediate: true },
)

function save() {
  setApiConfig(form.apiUrl.trim(), form.token.trim())
  emit('saved')
  emit('close')
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-40 grid place-items-center bg-ink/25 px-4">
    <form class="w-full max-w-[520px] rounded-[8px] border border-line bg-white shadow-soft" @submit.prevent="save">
      <header class="flex h-14 items-center justify-between border-b border-line px-5">
        <h2 class="text-[18px] font-semibold">设置</h2>
        <button type="button" class="grid h-9 w-9 place-items-center rounded-[6px] text-muted hover:bg-slate-50" @click="emit('close')">
          <X :size="20" />
        </button>
      </header>

      <div class="space-y-4 p-5">
        <label>
          <span class="mb-1 block text-[13px] text-muted">API 地址</span>
          <input v-model="form.apiUrl" class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue" placeholder="留空使用当前站点代理 /api" />
        </label>
        <label>
          <span class="mb-1 block text-[13px] text-muted">API Token</span>
          <input v-model="form.token" type="password" class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue" autocomplete="off" />
        </label>
        <p class="text-[13px] leading-5 text-muted">
          后端默认要求 Bearer Token。留空 API 地址时，前端会通过 Vite 代理访问本机后端。
        </p>
      </div>

      <footer class="flex justify-end gap-3 border-t border-line px-5 py-4">
        <button type="button" class="h-10 rounded-[8px] border border-line px-4 text-[14px]" @click="emit('close')">取消</button>
        <button type="submit" class="h-10 rounded-[8px] bg-blue px-5 text-[14px] font-medium text-white">保存并同步</button>
      </footer>
    </form>
  </div>
</template>
