<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Printer, QrCode, Search } from 'lucide-vue-next'

import { fetchContainerBoard } from '@/api/catalog'
import LocationQrCode from '@/components/ui/LocationQrCode.vue'
import { useInventoryStore } from '@/stores/inventory'
import type { ContainerBoard, LocationNode } from '@/types'
import { parseMsloc, toMsloc } from '@/utils/msloc'

const store = useInventoryStore()
const router = useRouter()

const selectedContainerId = ref<number | null>(null)
const board = ref<ContainerBoard | null>(null)
const loading = ref(false)
const message = ref<{ type: 'error' | 'success'; text: string } | null>(null)
const scanText = ref('')

const containers = computed(() => store.flatLocations.filter((location) => location.layout_type && !location.is_slot))
const selectedContainer = computed(() => containers.value.find((location) => location.id === selectedContainerId.value) || null)

watch(
  containers,
  (items) => {
    if (!selectedContainerId.value && items[0]) selectedContainerId.value = items[0].id
  },
  { immediate: true },
)

watch(selectedContainerId, () => {
  void loadBoard()
})

async function loadBoard() {
  if (!selectedContainerId.value) {
    board.value = null
    return
  }
  loading.value = true
  message.value = null
  try {
    board.value = await fetchContainerBoard(selectedContainerId.value)
  } catch (error) {
    board.value = null
    message.value = { type: 'error', text: error instanceof Error ? error.message : '格位加载失败' }
  } finally {
    loading.value = false
  }
}

function printLabels(scope: 'container' | 'slots' | 'all', location?: LocationNode) {
  const target = location || selectedContainer.value
  if (!target) return
  const route = router.resolve({ name: 'location-label-print', query: { id: String(target.id), scope } })
  window.open(route.href, '_blank')
}

async function testScan() {
  const fullCode = parseMsloc(scanText.value)
  if (!fullCode) {
    message.value = { type: 'error', text: '二维码内容必须以 MSLOC: 开头' }
    return
  }
  await router.push({ name: 'location-scan', query: { code: scanText.value.trim() } })
}
</script>

<template>
  <section class="p-5 2xl:p-7">
    <div class="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-[26px] font-semibold tracking-tight">位置二维码与标签</h2>
        <p class="mt-1 text-[14px] text-muted">为收纳盒和格位生成 MSLOC 标签，使用浏览器打印 A4 标签页。</p>
      </div>
      <button class="inline-flex h-10 items-center gap-2 rounded-xl border border-line bg-white px-4 text-[14px] text-green" @click="router.push({ name: 'location-scan' })">
        <QrCode :size="17" /> 扫码查看
      </button>
    </div>

    <div v-if="message" class="mb-4 rounded-xl border px-4 py-3 text-[13px]" :class="message.type === 'error' ? 'border-red-200 bg-red-50 text-red-700' : 'border-green/20 bg-green/10 text-green'">
      {{ message.text }}
    </div>

    <div class="grid gap-4 xl:grid-cols-[300px_minmax(0,1fr)_320px]">
      <aside class="rounded-2xl border border-line bg-white p-3">
        <div class="mb-3 px-2 text-[13px] font-medium text-muted">选择容器</div>
        <button
          v-for="container in containers"
          :key="container.id"
          class="mb-1 w-full rounded-xl px-3 py-3 text-left"
          :class="container.id === selectedContainerId ? 'bg-green/10 text-green' : 'hover:bg-wash'"
          @click="selectedContainerId = container.id"
        >
          <span class="block truncate text-[14px] font-medium">{{ container.name }}</span>
          <span class="mt-1 block truncate text-[12px] text-muted">{{ container.full_code }} · {{ container.layout_type === 'row' ? `${container.layout_columns} 格` : `${container.layout_rows} x ${container.layout_columns}` }}</span>
        </button>
        <div v-if="!containers.length" class="px-3 py-8 text-center text-[14px] text-muted">暂无收纳盒，请先在位置页创建。</div>
      </aside>

      <main class="min-w-0 rounded-2xl border border-line bg-white p-4 lg:p-5">
        <template v-if="selectedContainer">
          <div class="mb-5 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 class="text-[21px] font-semibold">{{ selectedContainer.name }}</h3>
              <p class="mt-1 text-[13px] text-muted">{{ selectedContainer.full_code }}</p>
            </div>
            <div class="flex flex-wrap gap-2">
              <button class="inline-flex h-9 items-center gap-2 rounded-xl border border-line px-3 text-[13px]" @click="printLabels('container')">
                <Printer :size="15" /> 容器标签
              </button>
              <button class="inline-flex h-9 items-center gap-2 rounded-xl bg-green px-3 text-[13px] font-medium text-white" @click="printLabels('all')">
                <Printer :size="15" /> 容器 + 全部格位
              </button>
            </div>
          </div>

          <div class="mb-5 flex items-center gap-4 rounded-xl border border-line bg-wash p-4">
            <LocationQrCode :value="toMsloc(selectedContainer.full_code)" :size="104" />
            <div class="min-w-0">
              <div class="text-[13px] text-muted">容器二维码内容</div>
              <div class="mt-1 break-all font-mono text-[14px]">{{ toMsloc(selectedContainer.full_code) }}</div>
            </div>
          </div>

          <div v-if="loading" class="py-16 text-center text-[14px] text-muted">正在加载格位...</div>
          <div v-else-if="board" class="grid gap-2 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
            <div v-for="slot in board.slots" :key="slot.location.id" class="rounded-xl border border-line p-3">
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <div class="text-[19px] font-semibold">{{ slot.location.slot_key }}</div>
                  <div class="mt-1 break-all font-mono text-[11px] text-muted">{{ slot.location.full_code }}</div>
                </div>
                <LocationQrCode :value="toMsloc(slot.location.full_code)" :size="62" />
              </div>
              <button class="mt-3 h-8 w-full rounded-lg border border-line text-[12px] text-green" @click="printLabels('container', slot.location)">打印此格</button>
            </div>
          </div>
        </template>
        <div v-else class="grid min-h-[360px] place-items-center text-[14px] text-muted">选择容器后生成标签。</div>
      </main>

      <aside class="rounded-2xl border border-line bg-white p-4">
        <h3 class="inline-flex items-center gap-2 text-[17px] font-semibold"><Search :size="17" />扫码内容测试</h3>
        <p class="mt-2 text-[13px] leading-5 text-muted">粘贴二维码原始内容，验证 MSLOC 解析和跳转。</p>
        <textarea v-model="scanText" class="mt-4 min-h-[112px] w-full rounded-xl border border-line p-3 font-mono text-[13px] outline-none focus:border-green" placeholder="MSLOC:WS.BOX-A.A01"></textarea>
        <button class="mt-3 h-10 w-full rounded-xl bg-green text-[14px] font-medium text-white" @click="testScan">解析并查看</button>
      </aside>
    </div>
  </section>
</template>
