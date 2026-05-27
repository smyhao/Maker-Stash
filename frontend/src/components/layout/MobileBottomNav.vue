<script setup lang="ts">
import { Box, Heart, ListTodo, MapPinned, Settings } from 'lucide-vue-next'
</script>

<template>
  <nav class="grid h-16 grid-cols-5 border-t border-line bg-white text-[12px] text-muted">
    <RouterLink
      v-slot="{ isActive }"
      :to="{ name: 'items' }"
      class="grid place-items-center"
    >
      <span class="grid place-items-center" :class="isActive ? 'text-blue' : ''">
        <Box :size="21" />
        物品
      </span>
    </RouterLink>
    <RouterLink
      v-slot="{ isActive }"
      :to="{ name: 'locations' }"
      class="grid place-items-center"
    >
      <span class="grid place-items-center" :class="isActive ? 'text-blue' : ''">
        <MapPinned :size="21" />
        位置
      </span>
    </RouterLink>
    <RouterLink
      v-slot="{ isActive }"
      :to="{ name: 'favorites' }"
      class="grid place-items-center"
    >
      <span class="grid place-items-center" :class="isActive ? 'text-blue' : ''">
        <Heart :size="21" />
        常用
      </span>
    </RouterLink>
    <RouterLink
      v-slot="{ isActive }"
      :to="{ name: 'restock' }"
      class="grid place-items-center"
    >
      <span class="grid place-items-center" :class="isActive ? 'text-amber' : ''">
        <ListTodo :size="21" />
        补货
      </span>
    </RouterLink>
    <RouterLink
      v-slot="{ isActive }"
      :to="{ name: 'settings' }"
      class="grid place-items-center"
    >
      <span class="grid place-items-center" :class="isActive ? 'text-blue' : ''">
        <Settings :size="21" />
        设置
      </span>
    </RouterLink>
  </nav>
</template>
