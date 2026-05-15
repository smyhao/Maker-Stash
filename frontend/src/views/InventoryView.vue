<script setup lang="ts">
import { onMounted } from 'vue'

import AppShell from '@/components/layout/AppShell.vue'
import { useInventoryStore } from '@/stores/inventory'

const inventory = useInventoryStore()

onMounted(() => {
  void inventory.bootstrap()
})
</script>

<template>
  <AppShell />
</template>
