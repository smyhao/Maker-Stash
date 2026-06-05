<script setup lang="ts">
import { reactive, watch } from 'vue'

import type { ExtensionSettingField } from '@/types'

const props = defineProps<{
  schema: Record<string, ExtensionSettingField>
  values: Record<string, unknown>
  disabled?: boolean
}>()

const emit = defineEmits<{
  save: [values: Record<string, unknown>]
}>()

const form = reactive<Record<string, unknown>>({})

function resetForm() {
  Object.keys(form).forEach((key) => delete form[key])
  Object.entries(props.schema).forEach(([key, field]) => {
    form[key] = props.values[key] ?? field.default ?? defaultValue(field)
  })
}

function defaultValue(field: ExtensionSettingField) {
  if (field.type === 'boolean') return false
  if (field.type === 'multiselect') return []
  if (field.type === 'number') return field.min ?? 0
  return ''
}

function fieldValue(key: string) {
  return form[key] as string | number | boolean | string[] | undefined
}

watch(
  () => [props.schema, props.values],
  resetForm,
  { immediate: true, deep: true },
)
</script>

<template>
  <form class="grid gap-3" @submit.prevent="emit('save', { ...form })">
    <div v-for="(field, key) in schema" :key="key" class="grid gap-1.5">
      <label class="text-[13px] font-medium text-ink/80">
        {{ field.label }}
        <span v-if="field.required" class="text-red-600">*</span>
      </label>

      <select
        v-if="field.type === 'select'"
        v-model="form[key]"
        :disabled="disabled"
        class="h-10 rounded-[8px] border border-line bg-white px-3 text-[14px] outline-none focus:border-blue disabled:bg-slate-50"
      >
        <option v-for="option in field.options || []" :key="option.value" :value="option.value">
          {{ option.label }}
        </option>
      </select>

      <select
        v-else-if="field.type === 'multiselect'"
        v-model="form[key]"
        :disabled="disabled"
        multiple
        class="min-h-[88px] rounded-[8px] border border-line bg-white px-3 py-2 text-[14px] outline-none focus:border-blue disabled:bg-slate-50"
      >
        <option v-for="option in field.options || []" :key="option.value" :value="option.value">
          {{ option.label }}
        </option>
      </select>

      <label v-else-if="field.type === 'boolean'" class="flex items-center justify-between rounded-[8px] border border-line px-3 py-2">
        <span class="text-[13px] text-muted">{{ fieldValue(String(key)) ? '已开启' : '未开启' }}</span>
        <input v-model="form[key]" :disabled="disabled" type="checkbox" class="h-4 w-4 accent-blue" />
      </label>

      <input
        v-else
        v-model="form[key]"
        :type="field.type === 'number' ? 'number' : field.type === 'secret' ? 'password' : 'text'"
        :min="field.min ?? undefined"
        :max="field.max ?? undefined"
        :disabled="disabled"
        class="h-10 rounded-[8px] border border-line px-3 text-[14px] outline-none focus:border-blue disabled:bg-slate-50"
        autocomplete="off"
      />
    </div>

    <div v-if="!Object.keys(schema).length" class="rounded-[8px] border border-line bg-slate-50 px-3 py-4 text-[13px] text-muted">
      这个扩展没有声明配置项。
    </div>

    <div class="flex justify-end">
      <button type="submit" :disabled="disabled" class="h-9 rounded-[8px] bg-blue px-4 text-[13px] font-medium text-white disabled:opacity-50">
        保存配置
      </button>
    </div>
  </form>
</template>
