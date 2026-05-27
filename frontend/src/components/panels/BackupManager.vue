<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { AlertTriangle, Box, ArrowDownToLine, ScrollText, Settings } from 'lucide-vue-next'

import { createBackup, downloadBackupFile, fetchBackups, restoreBackup } from '@/api/backups'
import type { Backup } from '@/types'

const backups = ref<Backup[]>([])
const note = ref('')
const includeUploads = ref(true)
const loading = ref(false)
const busy = ref(false)
const message = ref<{ type: 'error' | 'success'; text: string } | null>(null)

function setMessage(type: 'error' | 'success', text: string) {
  message.value = { type, text }
}

function fmtTime(iso: string) {
  return new Date(iso).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function fmtBytes(size: number | null) {
  if (!size) return '-'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

async function loadBackups() {
  loading.value = true
  try {
    const data = await fetchBackups()
    backups.value = data.backups
  } catch (cause) {
    backups.value = []
    setMessage('error', cause instanceof Error ? cause.message : '备份列表加载失败')
  } finally {
    loading.value = false
  }
}

async function submitBackup() {
  busy.value = true
  try {
    await createBackup({
      include_uploads: includeUploads.value,
      note: note.value.trim() || null,
    })
    note.value = ''
    includeUploads.value = true
    await loadBackups()
    setMessage('success', '备份已创建')
  } catch (cause) {
    setMessage('error', cause instanceof Error ? cause.message : '创建备份失败')
  } finally {
    busy.value = false
  }
}

async function downloadBackup(backup: Backup) {
  busy.value = true
  try {
    const blob = await downloadBackupFile(backup.backup_id)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${backup.backup_id}.zip`
    link.click()
    URL.revokeObjectURL(url)
    setMessage('success', `已开始下载 ${backup.backup_id}.zip`)
  } catch (cause) {
    setMessage('error', cause instanceof Error ? cause.message : '下载备份失败')
  } finally {
    busy.value = false
  }
}

async function recoverBackup(backup: Backup) {
  if (!window.confirm(`恢复备份「${backup.backup_id}」？恢复前后端会自动创建当前快照。`)) return
  busy.value = true
  try {
    await restoreBackup(backup.backup_id)
    await loadBackups()
    setMessage('success', '备份已恢复')
  } catch (cause) {
    setMessage('error', cause instanceof Error ? cause.message : '恢复备份失败')
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  void loadBackups()
})
</script>

<template>
  <section class="px-4 py-4 2xl:px-5">
    <div class="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-[22px] font-semibold">备份中心</h2>
        <p class="mt-1 text-[14px] text-muted">这里处理创建、下载和恢复。恢复前会自动生成当前快照，但仍然属于高风险操作。</p>
      </div>
      <button class="inline-flex h-10 items-center gap-2 rounded-[8px] border border-line bg-white px-4 text-[14px] font-medium text-ink/80" :disabled="loading" @click="loadBackups">
        <Settings :size="16" />
        刷新
      </button>
    </div>

    <div v-if="message" class="mb-4 rounded-[8px] border px-3 py-2 text-[13px]" :class="message.type === 'error' ? 'border-red-200 bg-red-50 text-red-700' : 'border-teal-200 bg-teal-50 text-teal'">
      {{ message.text }}
    </div>

    <div class="grid gap-4 xl:grid-cols-[360px_1fr]">
      <div class="rounded-[8px] border border-line bg-white p-4 shadow-sm">
        <div class="mb-3 flex items-center gap-2 text-[16px] font-semibold">
          <Box :size="18" />
          创建备份
        </div>
        <label class="mb-3 block">
          <span class="mb-1 block text-[13px] text-muted">备注</span>
          <input v-model="note" class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue" placeholder="例如：批量改分类前" />
        </label>
        <label class="mb-3 flex items-center gap-2 text-[13px] text-ink/80">
          <input v-model="includeUploads" type="checkbox" class="h-4 w-4 accent-blue" />
          包含上传文件
        </label>
        <div class="mb-4 rounded-[8px] border border-amber-200 bg-amber-50 px-3 py-2 text-[13px] text-amber-800">
          备份包含数据库与配置。恢复会覆盖当前状态，建议先确认最近一次备份可下载。
        </div>
        <button :disabled="busy" class="flex h-10 w-full items-center justify-center gap-2 rounded-[8px] bg-blue px-4 text-[14px] font-medium text-white disabled:opacity-50" @click="submitBackup">
          <Box :size="16" />
          创建备份
        </button>
      </div>

      <div class="rounded-[8px] border border-line bg-white p-4 shadow-sm">
        <div class="mb-3 flex items-center gap-2 text-[16px] font-semibold">
          <ScrollText :size="18" />
          备份列表
        </div>
        <div v-if="loading" class="px-2 py-8 text-center text-[14px] text-muted">加载中...</div>
        <div v-else-if="!backups.length" class="grid min-h-[220px] place-items-center rounded-[8px] border border-dashed border-line text-center text-[14px] text-muted">
          <div>
            <AlertTriangle class="mx-auto mb-3" :size="24" />
            暂无备份记录
          </div>
        </div>
        <div v-else class="space-y-3">
          <div v-for="backup in backups" :key="backup.id" class="rounded-[8px] border border-line px-4 py-3">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="truncate text-[14px] font-medium">{{ backup.backup_id }}</div>
                <div class="mt-1 text-[12px] text-muted">
                  {{ fmtTime(backup.created_at) }} · {{ fmtBytes(backup.size_bytes) }} · {{ backup.include_uploads ? '含上传文件' : '仅数据' }}
                </div>
                <div v-if="backup.note" class="mt-1 text-[12px] text-muted">{{ backup.note }}</div>
              </div>
              <div class="flex gap-2">
                <button :disabled="busy" class="inline-flex h-9 items-center gap-2 rounded-[8px] border border-line px-3 text-[13px] text-blue disabled:opacity-50" @click="downloadBackup(backup)">
                  <ArrowDownToLine :size="14" />
                  下载
                </button>
                <button :disabled="busy" class="h-9 rounded-[8px] border border-amber-200 px-3 text-[13px] text-amber-700 disabled:opacity-50" @click="recoverBackup(backup)">
                  恢复
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
