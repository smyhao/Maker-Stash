<script setup lang="ts">
import { Cpu, Package, ScrollText, Wrench } from 'lucide-vue-next'

import type { Item } from '@/types'

defineProps<{ item: Item }>()
</script>

<template>
  <span class="grid h-[56px] w-[74px] shrink-0 place-items-center rounded-[8px] border border-line bg-gradient-to-br from-white to-slate-100">
    <Cpu v-if="item.code.startsWith('ELE')" :size="32" class="text-slate-700" />
    <Wrench v-else-if="item.code.startsWith('TOOL')" :size="32" class="text-slate-700" />
    <ScrollText v-else-if="item.code.startsWith('FIL')" :size="34" class="text-slate-900" />
    <Package v-else :size="32" class="text-slate-700" />
  </span>
</template>
