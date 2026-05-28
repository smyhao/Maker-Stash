<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Heart, ListTodo, MapPinned, PackagePlus } from 'lucide-vue-next'

import { useInventoryStore } from '@/stores/inventory'

const store = useInventoryStore()
const router = useRouter()

const overviewCards = computed(() => [
  { label: '物品总数', value: store.stats?.item_count ?? store.total, tone: 'text-ink' },
  { label: '常用物品', value: store.stats?.favorite_count ?? 0, tone: 'text-blue' },
  { label: '补货标记', value: store.stats?.restock_count ?? 0, tone: 'text-amber' },
  { label: '未定位', value: store.stats?.unlocated_count ?? 0, tone: 'text-red-600' },
])

const topCategories = computed(() => (store.stats?.category_counts || []).slice(0, 5))
const topLocations = computed(() => (store.stats?.location_counts || []).slice(0, 5))
const lowStockItems = computed(() => store.items.filter((item) => item.status === 'low' || item.need_restock).slice(0, 6))

function openRoute(name: string) {
  void router.push({ name })
}

async function inspectItem(code: string) {
  await store.selectItem(code)
  void router.push({ name: 'items' })
}
</script>

<template>
  <section class="px-4 py-4 2xl:px-5">
    <div class="mb-5 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-[22px] font-semibold">工作台</h2>
        <p class="mt-1 text-[14px] text-muted">先处理补货风险，再回到库存列表做录入和调整。</p>
      </div>
      <div class="flex flex-wrap gap-2">
        <button class="inline-flex h-10 items-center gap-2 rounded-[8px] bg-blue px-4 text-[14px] font-medium text-white" @click="openRoute('items')">
          <PackagePlus :size="16" />
          新增物品
        </button>
      </div>
    </div>

    <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      <div v-for="card in overviewCards" :key="card.label" class="rounded-[8px] border border-line bg-white px-4 py-4 shadow-sm">
        <div class="text-[13px] text-muted">{{ card.label }}</div>
        <div class="mt-2 text-[28px] font-semibold" :class="card.tone">{{ card.value }}</div>
      </div>
    </div>

    <div class="mt-5 grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
      <div class="rounded-[8px] border border-line bg-white p-4 shadow-sm">
        <div class="mb-3 flex items-center justify-between">
          <h3 class="text-[16px] font-semibold">需要优先处理</h3>
          <button class="text-[13px] text-blue" @click="openRoute('restock')">查看补货页</button>
        </div>
        <div v-if="lowStockItems.length" class="space-y-2">
          <button
            v-for="item in lowStockItems"
            :key="item.code"
            class="grid w-full grid-cols-[1fr_auto] items-center gap-3 rounded-[8px] border border-line px-3 py-3 text-left hover:border-amber-300 hover:bg-amber-50/50"
            @click="inspectItem(item.code)"
          >
            <span class="min-w-0">
              <span class="block truncate text-[14px] font-medium">{{ item.name }}</span>
              <span class="mt-1 block truncate text-[12px] text-muted">{{ item.code }} · {{ item.location_display || item.location_text || '未记录位置' }}</span>
            </span>
            <span class="rounded-[6px] border border-amber/30 bg-amber/10 px-2 py-1 text-[12px] text-amber">
              {{ item.quantity ?? '—' }} {{ item.unit || '' }}
            </span>
          </button>
        </div>
        <div v-else class="rounded-[8px] border border-dashed border-line px-4 py-8 text-center text-[14px] text-muted">
          当前没有低库存或补货标记物品。
        </div>
      </div>

      <div class="grid gap-4">
        <div class="rounded-[8px] border border-line bg-white p-4 shadow-sm">
          <div class="mb-3 flex items-center gap-2 text-[16px] font-semibold">
            <Heart :size="16" class="text-blue" />
            常用分类
          </div>
          <div class="space-y-2">
            <div v-for="entry in topCategories" :key="entry.category_id" class="flex items-center justify-between rounded-[6px] bg-slate-50 px-3 py-2 text-[14px]">
              <span>{{ entry.name }}</span>
              <span class="text-muted">{{ entry.count }}</span>
            </div>
            <div v-if="!topCategories.length" class="text-[14px] text-muted">暂无分类统计。</div>
          </div>
        </div>

        <div class="rounded-[8px] border border-line bg-white p-4 shadow-sm">
          <div class="mb-3 flex items-center gap-2 text-[16px] font-semibold">
            <MapPinned :size="16" class="text-teal" />
            位置热点
          </div>
          <div class="space-y-2">
            <div v-for="entry in topLocations" :key="entry.location_id" class="flex items-center justify-between rounded-[6px] bg-slate-50 px-3 py-2 text-[14px]">
              <span class="min-w-0">
                <span class="block truncate">{{ entry.name }}</span>
                <span class="block text-[12px] text-muted">{{ entry.full_code }}</span>
              </span>
              <span class="text-muted">{{ entry.count }}</span>
            </div>
            <div v-if="!topLocations.length" class="text-[14px] text-muted">暂无位置统计。</div>
          </div>
        </div>

        <div class="rounded-[8px] border border-line bg-white p-4 shadow-sm">
          <div class="mb-3 flex items-center gap-2 text-[16px] font-semibold">
            <ListTodo :size="16" class="text-amber" />
            快捷入口
          </div>
          <div class="grid gap-2 sm:grid-cols-2">
            <button class="rounded-[8px] border border-line px-3 py-3 text-left text-[14px] hover:border-blue hover:text-blue" @click="openRoute('favorites')">查看常用物品</button>
            <button class="rounded-[8px] border border-line px-3 py-3 text-left text-[14px] hover:border-blue hover:text-blue" @click="openRoute('locations')">进入位置视图</button>
            <button class="rounded-[8px] border border-line px-3 py-3 text-left text-[14px] hover:border-blue hover:text-blue" @click="openRoute('items')">打开库存列表</button>
            <button class="rounded-[8px] border border-line px-3 py-3 text-left text-[14px] hover:border-blue hover:text-blue" @click="openRoute('restock')">查看补货清单</button>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
