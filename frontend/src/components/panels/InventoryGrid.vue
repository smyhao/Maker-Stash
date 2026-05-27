<script setup lang="ts">
import { computed } from 'vue'

import ItemThumb from '@/components/ui/ItemThumb.vue'
import StatusDot from '@/components/ui/StatusDot.vue'
import { useInventoryStore } from '@/stores/inventory'
import type { Item } from '@/types'

const store = useInventoryStore()

const cards = computed(() => store.items)
const totalPages = computed(() => Math.max(1, Math.ceil(store.total / store.pageSize)))
const startIndex = computed(() => (store.total === 0 ? 0 : (store.page - 1) * store.pageSize + 1))
const endIndex = computed(() => Math.min(store.page * store.pageSize, store.total))

function categoryName(item: Item) {
  return item.category_id ? store.categoryById.get(item.category_id)?.name || '未分类' : '未分类'
}
</script>

<template>
  <section class="px-4 py-4">
    <div v-if="cards.length" class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
      <button
        v-for="item in cards"
        :key="item.code"
        class="rounded-[8px] border bg-white p-4 text-left shadow-sm transition"
        :class="store.selectedItem?.code === item.code ? 'border-blue/30 bg-blue/5' : 'border-line hover:border-blue/20 hover:shadow-md'"
        @click="store.selectItem(item.code)"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="flex min-w-0 items-center gap-3">
            <ItemThumb :item="item" />
            <div class="min-w-0">
              <div class="truncate text-[15px] font-semibold">{{ item.name }}</div>
              <div class="mt-1 truncate text-[12px] text-muted">SKU: {{ item.code }}</div>
            </div>
          </div>
          <StatusDot :status="item.status" />
        </div>

        <dl class="mt-4 grid grid-cols-[56px_1fr] gap-y-2 text-[13px]">
          <dt class="text-muted">类型</dt>
          <dd class="truncate">{{ categoryName(item) }}</dd>
          <dt class="text-muted">位置</dt>
          <dd class="truncate">{{ item.location_text || '未记录' }}</dd>
          <dt class="text-muted">数量</dt>
          <dd><b class="text-[16px]">{{ item.quantity ?? '—' }}</b><span class="ml-1">{{ item.unit || '' }}</span></dd>
        </dl>

        <div class="mt-4 flex flex-wrap gap-2">
          <span class="rounded-[5px] border border-line px-2 py-1 text-[12px] text-ink/80">{{ item.code.split('-')[0] }}</span>
          <span v-if="item.need_restock" class="rounded-[5px] border border-amber/30 bg-amber/10 px-2 py-1 text-[12px] text-amber">低库存</span>
          <span v-if="item.is_favorite" class="rounded-[5px] border border-blue/25 bg-blue/10 px-2 py-1 text-[12px] text-blue">常用</span>
        </div>
      </button>
    </div>

    <div v-else class="rounded-[8px] border border-dashed border-line bg-white px-4 py-10 text-center text-[14px] text-muted">
      暂无匹配物品
    </div>

    <div class="flex flex-wrap items-center justify-between gap-3 px-1 pt-4 text-[13px] text-muted">
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
