<script setup lang="ts">
import { Boxes, MapPinned, Pencil, Plus, Trash2 } from 'lucide-vue-next'

import { useInventoryStore } from '@/stores/inventory'
import type { LocationNode } from '@/types'

const store = useInventoryStore()

const emit = defineEmits<{
  create: [parent: (LocationNode & { depth?: number }) | null]
  edit: [location: LocationNode & { depth?: number }]
  delete: [location: LocationNode & { depth?: number }]
}>()

async function selectLocation(location: LocationNode & { depth?: number }) {
  store.setLocation(location.full_code)
  await store.loadItems()
}

async function clearLocation() {
  store.setLocation(null)
  await store.loadItems()
}

function countFor(location: LocationNode) {
  return store.locationCounts.get(location.id) || 0
}
</script>

<template>
  <section class="border-t border-line px-5 py-4">
    <div class="mb-4 flex items-center justify-between gap-3">
      <div class="flex items-center gap-2 text-[16px] font-semibold">
        <MapPinned :size="20" />
        位置管理
        <span v-if="store.activeLocationCode" class="rounded-[5px] border border-blue/30 bg-blue/10 px-2 py-1 text-[12px] text-blue">
          {{ store.activeLocationCode }}
        </span>
      </div>
      <div class="flex gap-2">
        <button class="h-8 rounded-[6px] border border-line px-3 text-[13px] text-ink/80" @click="clearLocation">全部位置</button>
        <button class="inline-flex h-8 items-center gap-1 rounded-[6px] border border-blue/30 bg-blue/10 px-3 text-[13px] text-blue" @click="emit('create', null)">
          <Plus :size="15" />新增根位置
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-4 2xl:grid-cols-[minmax(260px,360px)_1fr] 2xl:gap-5">
      <div class="rounded-[8px] border border-line bg-white p-2">
        <button
          v-for="location in store.flatLocations"
          :key="location.id"
          class="mb-1 grid h-11 w-full grid-cols-[1fr_auto] items-center gap-3 rounded-[6px] px-2 text-left text-[14px]"
          :class="store.activeLocationCode === location.full_code ? 'bg-blue/10 text-blue' : 'text-ink/80 hover:bg-slate-50'"
          :style="{ paddingLeft: `${8 + location.depth * 18}px` }"
          @click="selectLocation(location)"
        >
          <span class="min-w-0">
            <span class="inline-flex max-w-full items-center gap-2">
              <Boxes :size="16" />
              <b class="truncate font-medium">{{ location.name }}</b>
            </span>
            <span class="ml-2 text-[12px] text-muted">{{ location.full_code }}</span>
          </span>
          <span class="text-[12px] text-muted">{{ countFor(location) }}</span>
        </button>
        <div v-if="!store.flatLocations.length" class="px-3 py-8 text-center text-[14px] text-muted">暂无位置</div>
      </div>

      <div class="rounded-[8px] border border-line bg-white p-4">
        <div v-if="store.activeLocationCode">
          <div
            v-for="location in store.flatLocations.filter((node) => node.full_code === store.activeLocationCode)"
            :key="location.id"
          >
            <div class="mb-4 flex items-start justify-between gap-4">
              <div>
                <div class="text-[20px] font-semibold">{{ location.name }}</div>
                <div class="mt-1 text-[13px] text-muted">{{ location.full_code }} · {{ location.type || '未设置类型' }}</div>
              </div>
              <div class="flex gap-2">
                <button class="inline-flex h-9 items-center gap-1 rounded-[6px] border border-line px-3 text-[13px]" @click="emit('create', location)">
                  <Plus :size="15" />子位置
                </button>
                <button class="grid h-9 w-9 place-items-center rounded-[6px] border border-line text-blue" @click="emit('edit', location)">
                  <Pencil :size="15" />
                </button>
                <button class="grid h-9 w-9 place-items-center rounded-[6px] border border-red-200 text-red-600" @click="emit('delete', location)">
                  <Trash2 :size="15" />
                </button>
              </div>
            </div>
            <dl class="grid grid-cols-[80px_1fr] gap-y-3 text-[14px]">
              <dt class="text-muted">编号</dt><dd>{{ location.code }}</dd>
              <dt class="text-muted">完整编号</dt><dd>{{ location.full_code }}</dd>
              <dt class="text-muted">类型</dt><dd>{{ location.type || '未设置' }}</dd>
              <dt class="text-muted">物品数</dt><dd>{{ countFor(location) }}</dd>
              <dt class="text-muted">描述</dt><dd>{{ location.description || '暂无描述' }}</dd>
            </dl>
          </div>
        </div>
        <div v-else class="grid h-full min-h-[180px] place-items-center text-center text-[14px] text-muted">
          <div>
            <MapPinned class="mx-auto mb-3" :size="28" />
            选择左侧位置查看详情，或新增根位置。
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
