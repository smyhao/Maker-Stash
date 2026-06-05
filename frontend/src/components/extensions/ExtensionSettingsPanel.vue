<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { fetchExtensions, setExtensionEnabled, updateExtensionSettings } from '@/api/extensions'
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
  <section class="grid gap-4">
    <div v-if="message" class="rounded-[8px] border px-3 py-2 text-[13px]" :class="message.type === 'error' ? 'border-red-200 bg-red-50 text-red-700' : 'border-teal-200 bg-teal-50 text-teal'">
      {{ message.text }}
    </div>

    <div class="rounded-[8px] border border-blue/20 bg-blue/5 px-3 py-2 text-[13px] leading-5 text-blue">
      这里只管理“当前电脑启用哪些已安装扩展”和扩展本机配置。扩展源码仍通过 GitHub 或本地文件部署。
    </div>

    <div v-if="loading" class="rounded-[8px] border border-line bg-white px-4 py-6 text-center text-[14px] text-muted">
      加载扩展中...
    </div>

    <div v-else-if="!extensions.length" class="rounded-[8px] border border-line bg-white px-4 py-6 text-center text-[14px] text-muted">
      暂未发现扩展。请在项目根目录的 extensions/*/extension.json 中添加扩展声明。
    </div>

    <article v-for="extension in extensions" v-else :key="extension.id" class="rounded-[8px] border border-line bg-white p-4 shadow-sm">
      <div class="mb-4 flex items-start justify-between gap-3">
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-2">
            <h3 class="text-[16px] font-semibold">{{ extension.name }}</h3>
            <span class="rounded-full bg-slate-100 px-2 py-0.5 text-[12px] text-muted">{{ extension.id }}</span>
            <span class="rounded-full px-2 py-0.5 text-[12px]" :class="extension.configured ? 'bg-teal/15 text-teal' : 'bg-amber/15 text-amber'">
              {{ extension.configured ? '配置完整' : '待配置' }}
            </span>
          </div>
          <p class="mt-1 text-[13px] text-muted">
            {{ extension.description || '这个扩展没有提供描述。' }} · v{{ extension.version }} · API {{ extension.api_version }}
          </p>
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

      <ExtensionSettingsForm
        :schema="extension.settings.schema"
        :values="extension.settings_values"
        :disabled="busyId === extension.id"
        @save="(values) => saveSettings(extension, values)"
      />

      <div v-if="extension.contributions.length" class="mt-4 rounded-[8px] border border-line bg-slate-50 px-3 py-2">
        <div class="mb-1 text-[12px] font-medium text-muted">声明的界面入口</div>
        <div class="flex flex-wrap gap-2">
          <span v-for="contribution in extension.contributions" :key="`${contribution.place}:${contribution.action}`" class="rounded-full bg-white px-2 py-1 text-[12px] text-ink/70">
            {{ contribution.place }} / {{ contribution.label }}
          </span>
        </div>
      </div>
    </article>
  </section>
</template>
