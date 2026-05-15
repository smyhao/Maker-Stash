<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { AlertTriangle, Check, Copy, Plus, Trash2, X } from 'lucide-vue-next'

import { getApiConfig, setApiConfig } from '@/api/client'
import { createToken, deleteToken, fetchTokens, updateToken } from '@/api/tokens'
import type { ApiTokenRead } from '@/api/tokens'

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

const tokens = ref<ApiTokenRead[]>([])
const newName = ref('')
const newDesc = ref('')
const createdTokenValue = ref<string | null>(null)
const copied = ref(false)
const loading = ref(false)
const busyId = ref<number | null>(null)

watch(
  () => props.open,
  async (open) => {
    if (!open) return
    const config = getApiConfig()
    form.apiUrl = config.apiUrl || ''
    form.token = config.token || ''
    createdTokenValue.value = null
    copied.value = false
    await loadTokens()
  },
  { immediate: true },
)

async function loadTokens() {
  loading.value = true
  try {
    const config = getApiConfig()
    const data = await fetchTokens(config.token || undefined)
    tokens.value = data.tokens
  } catch {
    tokens.value = []
  } finally {
    loading.value = false
  }
}

function save() {
  setApiConfig(form.apiUrl.trim(), form.token.trim())
  emit('saved')
  emit('close')
}

async function handleCreate() {
  const name = newName.value.trim()
  if (!name) return
  try {
    const data = await createToken({ name, description: newDesc.value.trim() || null })
    createdTokenValue.value = data.token
    copied.value = false
    newName.value = ''
    newDesc.value = ''
    await loadTokens()
  } catch (e: any) {
    alert(e.message || '创建失败')
  }
}

async function handleToggle(token: ApiTokenRead) {
  busyId.value = token.id
  try {
    await updateToken(token.id, { enabled: !token.enabled })
    await loadTokens()
  } catch (e: any) {
    alert(e.message || '操作失败')
  } finally {
    busyId.value = null
  }
}

async function handleDelete(token: ApiTokenRead) {
  if (!window.confirm(`删除 Token「${token.name}」？删除后使用此 Token 的客户端将无法访问。`)) return
  busyId.value = token.id
  try {
    await deleteToken(token.id)
    await loadTokens()
  } catch (e: any) {
    alert(e.message || '删除失败')
  } finally {
    busyId.value = null
  }
}

async function copyToClipboard() {
  if (!createdTokenValue.value) return
  await navigator.clipboard.writeText(createdTokenValue.value)
  copied.value = true
}

function fmtTime(iso: string | null) {
  if (!iso) return '-'
  const d = new Date(iso)
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-40 grid place-items-center bg-ink/25 px-4">
    <form class="flex max-h-[85vh] w-full max-w-[620px] flex-col rounded-[8px] border border-line bg-white shadow-soft" @submit.prevent="save">
      <header class="flex h-14 shrink-0 items-center justify-between border-b border-line px-5">
        <h2 class="text-[18px] font-semibold">设置</h2>
        <button type="button" class="grid h-9 w-9 place-items-center rounded-[6px] text-muted hover:bg-slate-50" @click="emit('close')">
          <X :size="20" />
        </button>
      </header>

      <div class="flex-1 space-y-4 overflow-y-auto p-5">
        <!-- 连接设置 -->
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
        <div class="rounded-[8px] border border-amber-200 bg-amber-50 px-3 py-2 text-[13px] leading-5 text-amber-800">
          首次部署还没有 Token 时，请先在后端运行 <code class="rounded bg-white px-1 font-mono">python -m app.scripts.create_token --name web</code> 创建初始 Token；出于安全考虑，网页不会匿名创建第一个 Token。
        </div>

        <!-- Token 管理 -->
        <div class="border-t border-line pt-4">
          <h3 class="mb-3 text-[15px] font-semibold">Token 管理</h3>

          <!-- 新创建的 Token 提示 -->
          <div v-if="createdTokenValue" class="mb-4 rounded-[8px] border border-amber-200 bg-amber-50 p-4">
            <div class="mb-2 flex items-center gap-2 text-[14px] font-medium text-amber-800">
              <AlertTriangle :size="16" />
              此 Token 仅显示一次，请立即复制保存
            </div>
            <div class="flex items-center gap-2">
              <code class="min-w-0 flex-1 select-all break-all rounded-[6px] bg-white px-3 py-2 font-mono text-[13px] text-ink">{{ createdTokenValue }}</code>
              <button type="button" class="grid h-9 w-9 shrink-0 place-items-center rounded-[6px] border border-line hover:bg-slate-50" @click="copyToClipboard">
                <Check v-if="copied" :size="16" class="text-teal" />
                <Copy v-else :size="16" class="text-muted" />
              </button>
            </div>
          </div>

          <!-- 创建表单 -->
          <div class="mb-3 flex gap-2">
            <input v-model="newName" class="h-10 min-w-0 flex-1 rounded-[8px] border border-line px-3 outline-none focus:border-blue" placeholder="Token 名称" />
            <button type="button" :disabled="!newName.trim()" class="flex h-10 shrink-0 items-center gap-1 rounded-[8px] bg-blue px-4 text-[14px] font-medium text-white disabled:opacity-50" @click="handleCreate">
              <Plus :size="16" />
              创建
            </button>
          </div>
          <input v-model="newDesc" class="mb-3 h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue" placeholder="描述（选填）" />

          <!-- Token 列表 -->
          <div class="overflow-hidden rounded-[8px] border border-line">
            <div v-for="t in tokens" :key="t.id" class="flex items-center gap-3 border-b border-line px-4 py-3 last:border-b-0">
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-2">
                  <span class="text-[14px] font-medium">{{ t.name }}</span>
                  <span v-if="t.is_current" class="rounded-full bg-blue/15 px-2 py-0.5 text-[12px] text-blue">当前使用</span>
                  <span v-else-if="t.enabled" class="rounded-full bg-teal/15 px-2 py-0.5 text-[12px] text-teal">启用</span>
                  <span v-else class="rounded-full bg-slate-100 px-2 py-0.5 text-[12px] text-muted">禁用</span>
                </div>
                <div class="mt-0.5 text-[12px] text-muted">
                  {{ t.description || '' }} · 创建 {{ fmtTime(t.created_at) }} · 最近使用 {{ fmtTime(t.last_used_at) }}
                </div>
              </div>
              <button
                v-if="!t.is_current"
                type="button"
                :disabled="busyId === t.id"
                class="h-8 shrink-0 rounded-[6px] border px-3 text-[13px] disabled:opacity-50"
                :class="t.enabled ? 'border-amber-200 text-amber-700 hover:bg-amber-50' : 'border-teal-200 text-teal hover:bg-teal-50'"
                @click="handleToggle(t)"
              >
                {{ t.enabled ? '禁用' : '启用' }}
              </button>
              <button
                v-if="!t.is_current"
                type="button"
                :disabled="busyId === t.id"
                class="grid h-8 w-8 shrink-0 place-items-center rounded-[6px] border border-red-200 text-red-600 disabled:opacity-50"
                @click="handleDelete(t)"
              >
                <Trash2 :size="14" />
              </button>
            </div>
            <div v-if="!tokens.length && !loading" class="px-4 py-6 text-center text-[14px] text-muted">
              暂无 Token
            </div>
            <div v-if="loading" class="px-4 py-6 text-center text-[14px] text-muted">
              加载中...
            </div>
          </div>
        </div>
      </div>

      <footer class="flex shrink-0 justify-end gap-3 border-t border-line px-5 py-4">
        <button type="button" class="h-10 rounded-[8px] border border-line px-4 text-[14px]" @click="emit('close')">取消</button>
        <button type="submit" class="h-10 rounded-[8px] bg-blue px-5 text-[14px] font-medium text-white">保存并同步</button>
      </footer>
    </form>
  </div>
</template>
