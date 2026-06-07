<script setup lang="ts">
import { computed, defineAsyncComponent } from 'vue'
import type { Component } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const extensionModules = import.meta.glob('../../../extensions/*/src/index.ts', { import: 'default' }) as Record<string, () => Promise<Component>>

const extensionId = computed(() => String(route.params.extensionId || ''))
const extensionComponent = computed(() => {
  const loader = extensionModules[`../../../extensions/${extensionId.value}/src/index.ts`]
  return loader ? defineAsyncComponent(loader) : null
})
</script>

<template>
  <section v-if="extensionComponent" class="h-full min-h-0 overflow-hidden">
    <component :is="extensionComponent" class="h-full min-h-0" />
  </section>
  <section v-else class="p-5 2xl:p-7">
    <h2 class="text-[26px] font-semibold tracking-tight">扩展不存在</h2>
    <p class="mt-2 text-[14px] text-muted">未找到该扩展的前端入口。</p>
  </section>
</template>
