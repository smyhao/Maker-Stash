<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { fetchExtensions, notifyExtensionsChanged, setExtensionEnabled, updateExtensionSettings } from '@/api/extensions'
import ExtensionSettingsForm from '@/components/extensions/ExtensionSettingsForm.vue'
import type { ExtensionManifest } from '@/types'

const extensions = ref<ExtensionManifest[]>([])
const loading = ref(false)
const busyId = ref<string | null>(null)
const message = ref<{ type: 'error' | 'success'; text: string } | null>(null)

function setMessage(type: 'error' | 'success', text: string) {
  message.value = { type, text }
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback
}

async function loadExtensions() {
  loading.value = true
  try {
    const data = await fetchExtensions()
    extensions.value = data.extensions
  } catch (e) {
    extensions.value = []
    setMessage('error', errorMessage(e, '扩展列表加载失败'))
  } finally {
    loading.value = false
  }
}

async function toggleExtension(extension: ExtensionManifest) {
  busyId.value = extension.id
  try {
    await setExtensionEnabled(extension.id, !extension.enabled)
    await loadExtensions()
    notifyExtensionsChanged()
    setMessage('success', extension.enabled ? '扩展已禁用' : '扩展已启用')
  } catch (e) {
    setMessage('error', errorMessage(e, '扩展开关保存失败'))
  } finally {
    busyId.value = null
  }
}

async function saveSettings(extension: ExtensionManifest, values: Record<string, unknown>) {
  busyId.value = extension.id
  try {
    await updateExtensionSettings(extension.id, values)
    await loadExtensions()
    notifyExtensionsChanged()
    setMessage('success', '扩展配置已保存')
  } catch (e) {
    setMessage('error', errorMessage(e, '扩展配置保存失败'))
  } finally {
    busyId.value = null
  }
}

onMounted(loadExtensions)
</script>

<template>
  <section class="p-5 2xl:p-7">
    <div class="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h2 class="text-[26px] font-semibold tracking-tight">扩展管理</h2>
        <p class="mt-1 text-[14px] text-muted">管理已安装扩展的启用状态和必要配置。</p>
      </div>
      <button type="button" class="h-9 rounded-[8px] border border-line bg-white px-3 text-[13px] font-medium text-ink/75 hover:border-green hover:text-green" :disabled="loading" @click="loadExtensions">
        刷新
      </button>
    </div>

    <div v-if="message" class="rounded-[8px] border px-3 py-2 text-[13px]" :class="message.type === 'error' ? 'border-red-200 bg-red-50 text-red-700' : 'border-teal-200 bg-teal-50 text-teal'">
      {{ message.text }}
    </div>

    <div v-if="loading" class="mt-4 rounded-[8px] border border-line bg-white px-4 py-6 text-center text-[14px] text-muted">
      加载扩展中...
    </div>

    <div v-else-if="!extensions.length" class="mt-4 rounded-[8px] border border-line bg-white px-4 py-6 text-center text-[14px] text-muted">
      暂未发现扩展。请在项目根目录的 extensions/*/extension.json 中添加扩展声明。
    </div>

    <div v-else class="mt-4 overflow-hidden rounded-[8px] border border-line bg-white shadow-sm">
      <article v-for="extension in extensions" :key="extension.id" class="border-b border-line last:border-b-0">
        <div class="flex flex-col gap-3 px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <h3 class="text-[15px] font-semibold">{{ extension.name }}</h3>
              <span class="rounded-full bg-slate-100 px-2 py-0.5 text-[12px] text-muted">{{ extension.id }}</span>
              <span class="rounded-full px-2 py-0.5 text-[12px]" :class="extension.enabled ? 'bg-teal/15 text-teal' : 'bg-slate-100 text-muted'">
                {{ extension.enabled ? '已启用' : '已禁用' }}
              </span>
              <span v-if="!extension.configured" class="rounded-full bg-amber/15 px-2 py-0.5 text-[12px] text-amber">待配置</span>
            </div>
            <p class="mt-1 truncate text-[13px] text-muted">
              {{ extension.description || '无描述' }} · v{{ extension.version }}
            </p>
            <div v-if="extension.contributions.length" class="mt-2 flex flex-wrap gap-1.5">
              <span v-for="contribution in extension.contributions" :key="`${contribution.place}:${contribution.action}`" class="rounded-full bg-slate-50 px-2 py-0.5 text-[12px] text-ink/60">
                {{ contribution.label }}
              </span>
            </div>
          </div>
          <button
            type="button"
            :disabled="busyId === extension.id"
            class="h-9 shrink-0 rounded-[8px] border px-4 text-[13px] font-medium disabled:opacity-50"
            :class="extension.enabled ? 'border-amber-200 text-amber hover:bg-amber/10' : 'border-teal/25 text-teal hover:bg-teal/10'"
            @click="toggleExtension(extension)"
          >
            {{ extension.enabled ? '禁用' : '启用' }}
          </button>
        </div>

        <div v-if="Object.keys(extension.settings.schema).length" class="border-t border-line bg-slate-50 px-4 py-3">
          <ExtensionSettingsForm
            :schema="extension.settings.schema"
            :values="extension.settings_values"
            :disabled="busyId === extension.id"
            @save="(values) => saveSettings(extension, values)"
          />
        </div>
      </article>
    </div>
  </section>
</template>
