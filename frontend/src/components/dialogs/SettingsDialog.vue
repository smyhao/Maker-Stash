<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { AlertTriangle, Check, Copy, Plus, Trash2, X } from 'lucide-vue-next'

import { createBackup, downloadBackupFile, fetchBackups, restoreBackup } from '@/api/backups'
import { getApiConfig, setApiConfig } from '@/api/client'
import { createToken, deleteToken, fetchTokens, updateToken } from '@/api/tokens'
import type { ApiTokenRead } from '@/api/tokens'
import type { Backup } from '@/types'

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
const backups = ref<Backup[]>([])
const backupNote = ref('')
const includeUploads = ref(true)
const backupLoading = ref(false)
const backupBusy = ref(false)
const message = ref<{ type: 'error' | 'success'; text: string } | null>(null)
const activeTab = ref<'connection' | 'tokens' | 'backups'>('connection')

const tabs = [
  { key: 'connection', label: '连接' },
  { key: 'tokens', label: 'Token' },
  { key: 'backups', label: '备份' },
] as const

function setMessage(type: 'error' | 'success', text: string) {
  message.value = { type, text }
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback
}

watch(
  () => props.open,
  async (open) => {
    if (!open) return
    const config = getApiConfig()
    form.apiUrl = config.apiUrl || ''
    form.token = config.token || ''
    createdTokenValue.value = null
    copied.value = false
    message.value = null
    activeTab.value = 'connection'
    await Promise.all([loadTokens(), loadBackups()])
  },
  { immediate: true },
)

async function loadTokens() {
  loading.value = true
  try {
    const config = getApiConfig()
    const data = await fetchTokens(config.token || undefined)
    tokens.value = data.tokens
  } catch (e) {
    tokens.value = []
    setMessage('error', errorMessage(e, 'Token 列表加载失败'))
  } finally {
    loading.value = false
  }
}

async function loadBackups() {
  backupLoading.value = true
  try {
    const data = await fetchBackups()
    backups.value = data.backups
  } catch (e) {
    backups.value = []
    setMessage('error', errorMessage(e, '备份列表加载失败'))
  } finally {
    backupLoading.value = false
  }
}

function save() {
  setApiConfig(form.apiUrl.trim(), form.token.trim())
  setMessage('success', '设置已保存，正在重新同步数据')
  emit('saved')
  emit('close')
}

async function handleCreateBackup() {
  backupBusy.value = true
  try {
    await createBackup({
      include_uploads: includeUploads.value,
      note: backupNote.value.trim() || null,
    })
    backupNote.value = ''
    includeUploads.value = true
    await loadBackups()
    setMessage('success', '备份已创建')
  } catch (e) {
    setMessage('error', errorMessage(e, '备份失败'))
  } finally {
    backupBusy.value = false
  }
}

async function handleDownloadBackup(backup: Backup) {
  backupBusy.value = true
  try {
    const blob = await downloadBackupFile(backup.backup_id)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${backup.backup_id}.zip`
    link.click()
    URL.revokeObjectURL(url)
    setMessage('success', `已开始下载 ${backup.backup_id}.zip`)
  } catch (e) {
    setMessage('error', errorMessage(e, '下载失败'))
  } finally {
    backupBusy.value = false
  }
}

async function handleRestoreBackup(backup: Backup) {
  if (!window.confirm(`恢复备份「${backup.backup_id}」？恢复前后端会自动创建当前快照，但当前页面数据会被刷新。`)) return
  backupBusy.value = true
  try {
    await restoreBackup(backup.backup_id)
    await loadBackups()
    emit('saved')
    setMessage('success', '备份已恢复，页面数据已重新同步')
  } catch (e) {
    setMessage('error', errorMessage(e, '恢复失败'))
  } finally {
    backupBusy.value = false
  }
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
    setMessage('success', 'Token 已创建')
  } catch (e) {
    setMessage('error', errorMessage(e, '创建失败'))
  }
}

async function handleToggle(token: ApiTokenRead) {
  busyId.value = token.id
  try {
    await updateToken(token.id, { enabled: !token.enabled })
    await loadTokens()
    setMessage('success', token.enabled ? 'Token 已禁用' : 'Token 已启用')
  } catch (e) {
    setMessage('error', errorMessage(e, '操作失败'))
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
    setMessage('success', 'Token 已删除')
  } catch (e) {
    setMessage('error', errorMessage(e, '删除失败'))
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

function fmtBytes(size: number | null) {
  if (!size) return '-'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-40 grid place-items-center bg-ink/25 px-4">
    <form class="flex max-h-[85vh] w-full max-w-[760px] flex-col rounded-[8px] border border-line bg-white shadow-soft" @submit.prevent="save">
      <header class="flex h-14 shrink-0 items-center justify-between border-b border-line px-5">
        <h2 class="text-[18px] font-semibold">设置</h2>
        <button type="button" class="grid h-9 w-9 place-items-center rounded-[6px] text-muted hover:bg-slate-50" @click="emit('close')">
          <X :size="20" />
        </button>
      </header>

      <div class="shrink-0 border-b border-line px-5 py-3">
        <div class="inline-flex rounded-[8px] border border-line bg-slate-50 p-1">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            type="button"
            class="h-8 rounded-[6px] px-4 text-[13px] font-medium"
            :class="activeTab === tab.key ? 'bg-white text-blue shadow-sm' : 'text-ink/70 hover:text-ink'"
            @click="activeTab = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-5">
        <div v-if="message" class="rounded-[8px] border px-3 py-2 text-[13px]" :class="message.type === 'error' ? 'border-red-200 bg-red-50 text-red-700' : 'border-teal-200 bg-teal-50 text-teal'">
          {{ message.text }}
        </div>

        <section v-if="activeTab === 'connection'" class="mt-4 space-y-4">
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
        </section>

        <section v-else-if="activeTab === 'tokens'" class="mt-4 space-y-4">
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

          <div class="mb-3 flex gap-2">
            <input v-model="newName" class="h-10 min-w-0 flex-1 rounded-[8px] border border-line px-3 outline-none focus:border-blue" placeholder="Token 名称" />
            <button type="button" :disabled="!newName.trim()" class="flex h-10 shrink-0 items-center gap-1 rounded-[8px] bg-blue px-4 text-[14px] font-medium text-white disabled:opacity-50" @click="handleCreate">
              <Plus :size="16" />
              创建
            </button>
          </div>
          <input v-model="newDesc" class="mb-3 h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue" placeholder="描述（选填）" />

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
        </section>

        <section v-else class="mt-4 space-y-4">
          <div class="mb-3 flex items-center justify-between gap-3">
            <div>
              <h3 class="text-[15px] font-semibold">备份</h3>
              <p class="mt-1 text-[13px] text-muted">创建、下载或恢复后端备份。</p>
            </div>
            <button type="button" class="h-8 rounded-[6px] border border-line px-3 text-[13px] text-ink/80 hover:border-blue hover:text-blue" :disabled="backupLoading" @click="loadBackups">
              刷新
            </button>
          </div>

          <div class="mb-3 rounded-[8px] border border-line p-3">
            <label class="mb-2 block">
              <span class="mb-1 block text-[13px] text-muted">备份备注</span>
              <input v-model="backupNote" class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue" placeholder="例如：调整分类前" />
            </label>
            <label class="mb-3 flex items-center gap-2 text-[13px] text-ink/80">
              <input v-model="includeUploads" type="checkbox" class="h-4 w-4 accent-blue" />
              包含上传文件
            </label>
            <button type="button" :disabled="backupBusy" class="flex h-10 w-full items-center justify-center gap-2 rounded-[8px] bg-blue px-4 text-[14px] font-medium text-white disabled:opacity-50" @click="handleCreateBackup">
              <Plus :size="16" />
              创建备份
            </button>
          </div>

          <div class="overflow-hidden rounded-[8px] border border-line">
            <div v-for="backup in backups" :key="backup.id" class="border-b border-line px-4 py-3 last:border-b-0">
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <div class="truncate text-[14px] font-medium">{{ backup.backup_id }}</div>
                  <div class="mt-0.5 text-[12px] text-muted">
                    {{ fmtTime(backup.created_at) }} · {{ fmtBytes(backup.size_bytes) }} · {{ backup.include_uploads ? '含上传文件' : '仅数据' }}
                  </div>
                  <div v-if="backup.note" class="mt-1 truncate text-[12px] text-muted">{{ backup.note }}</div>
                </div>
                <div class="flex shrink-0 gap-2">
                  <button type="button" :disabled="backupBusy" class="h-8 rounded-[6px] border border-line px-3 text-[13px] text-blue disabled:opacity-50" @click="handleDownloadBackup(backup)">
                    下载
                  </button>
                  <button type="button" :disabled="backupBusy" class="h-8 rounded-[6px] border border-amber-200 px-3 text-[13px] text-amber-700 disabled:opacity-50" @click="handleRestoreBackup(backup)">
                    恢复
                  </button>
                </div>
              </div>
            </div>
            <div v-if="!backups.length && !backupLoading" class="px-4 py-6 text-center text-[14px] text-muted">
              暂无备份
            </div>
            <div v-if="backupLoading" class="px-4 py-6 text-center text-[14px] text-muted">
              加载中...
            </div>
          </div>
        </section>
      </div>

      <footer class="flex shrink-0 justify-end gap-3 border-t border-line px-5 py-4">
        <button type="button" class="h-10 rounded-[8px] border border-line px-4 text-[14px]" @click="emit('close')">{{ activeTab === 'connection' ? '取消' : '关闭' }}</button>
        <button v-if="activeTab === 'connection'" type="submit" class="h-10 rounded-[8px] bg-blue px-5 text-[14px] font-medium text-white">保存并同步</button>
      </footer>
    </form>
  </div>
</template>
