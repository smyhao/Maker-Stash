<script setup lang="ts">
import { Boxes, Home, MapPinned, PackagePlus, Settings } from 'lucide-vue-next'
</script>

<template>
  <nav class="grid h-16 grid-cols-5 border-t border-line bg-white text-[12px] text-muted">
    <RouterLink
      v-slot="{ isActive }"
      :to="{ name: 'home' }"
      class="grid place-items-center"
    >
      <span class="grid place-items-center" :class="isActive ? 'text-blue' : ''">
        <Home :size="21" />
        工作台
      </span>
    </RouterLink>
    <RouterLink
      v-slot="{ isActive }"
      :to="{ name: 'items' }"
      class="grid place-items-center"
    >
      <span class="grid place-items-center" :class="isActive ? 'text-blue' : ''">
        <Boxes :size="21" />
        库存
      </span>
    </RouterLink>
    <RouterLink
      v-slot="{ isActive }"
      :to="{ name: 'quick-entry' }"
      class="grid place-items-center"
    >
      <span class="grid place-items-center" :class="isActive ? 'text-blue' : ''">
        <PackagePlus :size="21" />
        录入
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
      :to="{ name: 'management' }"
      class="grid place-items-center"
    >
      <span class="grid place-items-center" :class="isActive ? 'text-blue' : ''">
        <Settings :size="21" />
        管理
      </span>
    </RouterLink>
  </nav>
</template>
