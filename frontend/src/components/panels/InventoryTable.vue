<script setup lang="ts">
import { computed } from 'vue'

import ItemThumb from '@/components/ui/ItemThumb.vue'
import StatusDot from '@/components/ui/StatusDot.vue'
import { useInventoryStore } from '@/stores/inventory'
import type { Item } from '@/types'

const store = useInventoryStore()

const rows = computed(() => store.items)
const totalPages = computed(() => Math.max(1, Math.ceil(store.total / store.pageSize)))
const startIndex = computed(() => (store.total === 0 ? 0 : (store.page - 1) * store.pageSize + 1))
const endIndex = computed(() => Math.min(store.page * store.pageSize, store.total))

function categoryName(item: Item) {
  return item.category_id ? store.categoryById.get(item.category_id)?.name || '未分类' : '未分类'
}
</script>

<template>
  <section class="px-4 py-4">
    <div class="thin-scrollbar overflow-x-auto">
      <div class="min-w-[780px]">
        <div class="grid grid-cols-[minmax(210px,1fr)_100px_95px_130px_90px_150px] gap-3 px-3 pb-3 text-[13px] text-muted 2xl:grid-cols-[minmax(230px,1fr)_110px_110px_145px_100px_180px] 2xl:gap-4">
          <span>物品</span>
          <span>类型 ↓</span>
          <span>数量 ↕</span>
          <span>位置</span>
          <span>状态</span>
          <span>标签 / 规格</span>
        </div>

        <button
          v-for="item in rows"
          :key="item.code"
          class="mb-2 grid w-full grid-cols-[minmax(210px,1fr)_100px_95px_130px_90px_150px] items-center gap-3 rounded-[8px] border px-3 py-2 text-left transition 2xl:grid-cols-[minmax(230px,1fr)_110px_110px_145px_100px_180px] 2xl:gap-4"
          :class="store.selectedItem?.code === item.code ? 'border-blue/25 bg-blue/5 shadow-sm' : 'border-transparent bg-white hover:border-line hover:shadow-sm'"
          @click="store.selectItem(item.code)"
        >
          <span class="flex min-w-0 items-center gap-3 2xl:gap-4">
            <ItemThumb :item="item" />
            <span class="min-w-0">
              <span class="block truncate text-[15px] font-semibold">{{ item.name }}</span>
              <span class="mt-1 block truncate text-[12px] text-muted">SKU: {{ item.code }}</span>
            </span>
          </span>
          <span class="truncate text-[14px]">{{ categoryName(item) }}</span>
          <span>
            <b class="text-[16px] 2xl:text-[17px]">{{ item.quantity ?? '—' }}</b>
            <span class="ml-1 text-[13px]">{{ item.unit }}</span>
          </span>
          <span class="truncate text-[14px]">{{ item.location_text || '未记录' }}</span>
          <StatusDot :status="item.status" />
          <span class="flex flex-wrap gap-2">
            <span class="rounded-[5px] border border-line px-2 py-1 text-[12px] text-ink/80">{{ item.code.split('-')[0] }}</span>
            <span v-if="item.need_restock" class="rounded-[5px] border border-amber/30 bg-amber/10 px-2 py-1 text-[12px] text-amber">低库存</span>
            <span v-if="item.is_favorite" class="rounded-[5px] border border-blue/25 bg-blue/10 px-2 py-1 text-[12px] text-blue">常用</span>
          </span>
        </button>
      </div>
    </div>

    <div class="flex flex-wrap items-center justify-between gap-3 px-3 pt-2 text-[13px] text-muted">
      <span>第 {{ startIndex }}-{{ endIndex }} 项，共 {{ store.total }} 项</span>
      <div class="flex items-center gap-2">
        <button
          class="h-8 rounded-[6px] border border-line bg-white px-3 text-[13px] text-ink/80 disabled:cursor-not-allowed disabled:opacity-40"
          :disabled="store.page <= 1"
          @click="store.setPage(store.page - 1)"
        >
          上一页
        </button>
        <span class="min-w-16 text-center text-[13px] text-ink">{{ store.page }} / {{ totalPages }}</span>
        <button
          class="h-8 rounded-[6px] border border-line bg-white px-3 text-[13px] text-ink/80 disabled:cursor-not-allowed disabled:opacity-40"
          :disabled="store.page >= totalPages"
          @click="store.setPage(store.page + 1)"
        >
          下一页
        </button>
      </div>
    </div>
  </section>
</template>
