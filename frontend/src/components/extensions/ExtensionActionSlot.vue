<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import { fetchExtensionContributions, runExtensionAction } from '@/api/extensions'
import type { ExtensionContribution } from '@/types'

const props = defineProps<{
  place: string
  context?: Record<string, unknown>
}>()

const contributions = ref<ExtensionContribution[]>([])
const busyKey = ref<string | null>(null)
const message = ref<string | null>(null)

function keyFor(contribution: ExtensionContribution) {
  return `${contribution.extension_id}:${contribution.action}`
}

async function loadContributions() {
  try {
    const data = await fetchExtensionContributions(props.place)
    contributions.value = data.contributions
  } catch {
    contributions.value = []
  }
}

async function runAction(contribution: ExtensionContribution) {
  const key = keyFor(contribution)
  busyKey.value = key
  message.value = null
  try {
    await runExtensionAction(contribution.extension_id, contribution.action, props.context || {})
    message.value = `${contribution.label} 已执行`
  } catch (error) {
    message.value = error instanceof Error ? error.message : '扩展操作执行失败'
  } finally {
    busyKey.value = null
  }
}

onMounted(loadContributions)
watch(() => props.place, loadContributions)
</script>

<template>
  <div v-if="contributions.length" class="mt-4 border-t border-line pt-3 2xl:mt-5 2xl:pt-4">
    <h3 class="mb-2 text-[15px] font-semibold">扩展操作</h3>
    <div class="grid gap-2">
      <button
        v-for="contribution in contributions"
        :key="keyFor(contribution)"
        type="button"
        :disabled="busyKey === keyFor(contribution)"
        class="inline-flex h-10 items-center justify-center rounded-[8px] border border-line text-[14px] font-medium text-ink/80 hover:border-blue hover:text-blue disabled:opacity-50"
        @click="runAction(contribution)"
      >
        {{ contribution.label }}
      </button>
    </div>
    <div v-if="message" class="mt-2 rounded-[8px] border border-line bg-slate-50 px-3 py-2 text-[12px] text-muted">
      {{ message }}
    </div>
  </div>
</template>
