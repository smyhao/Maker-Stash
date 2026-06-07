<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { CheckCircle2, Copy, PackageCheck, RefreshCw } from 'lucide-vue-next'

import { fetchCategoryAttributeDefinitions } from '@/api/catalog'
import { createItem } from '@/api/items'
import { useInventoryStore } from '@/stores/inventory'
import type { AttributeDefinition, Item, ItemFormPayload, LocationNode, Status } from '@/types'

interface SessionEntry {
  item: Item
  attributeCount: number
}

const store = useInventoryStore()
const router = useRouter()

const nameInput = ref<HTMLInputElement | null>(null)
const busy = ref(false)
const notice = ref<{ type: 'error' | 'success'; message: string } | null>(null)
const sessionItems = ref<SessionEntry[]>([])
const lastPayload = ref<ItemFormPayload | null>(null)
const definitions = ref<AttributeDefinition[]>([])
const definitionsLoading = ref(false)
let definitionRequest = 0

const settings = reactive({
  defaultCategory: '',
  defaultLocationCode: '',
  locationText: '',
  lockCategory: true,
  lockLocation: true,
})

const form = reactive({
  name: '',
  category: '',
  locationCode: '',
  locationText: '',
  quantity: '',
  unit: '',
  status: 'normal' as Status,
  tags: '',
  description: '',
})

const attributeValues = reactive<Record<string, string>>({})

const categories = computed(() => store.flatCategories)
const locations = computed(() => store.flatLocations)
const selectedCategory = computed(() => categories.value.find((category) => category.slug === form.category))
const sessionTitle = computed(() => `本次已录入 ${sessionItems.value.length} 件`)
const categorySummary = computed(() => {
  const counts = new Map<number, number>()
  sessionItems.value.forEach(({ item }) => {
    if (item.category_id) counts.set(item.category_id, (counts.get(item.category_id) || 0) + 1)
  })
  return Array.from(counts.entries())
    .map(([id, count]) => ({ label: store.categoryById.get(id)?.name || '未分类', count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 2)
})
const unpicturedCount = computed(() => sessionItems.value.filter((entry) => !entry.item.cover_attachment_id).length)
const unfilledAttributeCount = computed(() => sessionItems.value.filter((entry) => entry.attributeCount === 0).length)
const quantityError = computed(() => {
  const value = form.quantity.trim()
  if (!value) return ''
  const parsed = parseQuantity(value)
  if (parsed === null) return '数量格式不正确'
  if (parsed < 0) return '数量不能为负'
  return ''
})

watch(
  () => settings.defaultCategory,
  (value) => {
    if (!form.category || settings.lockCategory) form.category = value
  },
)

watch(
  () => [settings.defaultLocationCode, settings.locationText] as const,
  ([code, text]) => {
    if (!form.locationCode || settings.lockLocation) form.locationCode = code
    if (!form.locationText || settings.lockLocation) form.locationText = text
  },
)

watch(
  () => form.category,
  (slug) => {
    void loadDefinitions(slug)
  },
  { immediate: true },
)

function parseQuantity(value: string) {
  const normalized = value
    .trim()
    .replace(/，/g, '.')
    .replace(/,/g, '.')
    .replace(/[０-９]/g, (char) => String.fromCharCode(char.charCodeAt(0) - 0xff10 + 48))
  if (!normalized) return null
  const parsed = Number(normalized)
  return Number.isFinite(parsed) ? parsed : null
}

function parseTags(value: string) {
  return value
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean)
}

function statusLabel(status: Status) {
  const labels: Record<Status, string> = {
    normal: '正常',
    low: '较低',
    empty: '用尽',
    broken: '损坏',
    missing: '丢失',
    idle: '闲置',
    archived: '已归档',
  }
  return labels[status] || status
}

function locationLabel(item: Item) {
  return item.location_display || item.location_text || '未记录位置'
}

function selectedLocationLabel(code: string) {
  return locations.value.find((location) => location.full_code === code)?.name || code
}

function indentedName(node: { name: string; depth: number }) {
  return `${'　'.repeat(node.depth)}${node.name}`
}

async function loadDefinitions(slug: string) {
  const category = categories.value.find((item) => item.slug === slug)
  const requestId = ++definitionRequest
  definitions.value = []
  Object.keys(attributeValues).forEach((key) => delete attributeValues[key])
  if (!category) return
  definitionsLoading.value = true
  try {
    const data = await fetchCategoryAttributeDefinitions(category.id)
    if (requestId !== definitionRequest) return
    definitions.value = data.attribute_definitions.filter((definition) => definition.is_enabled)
  } catch {
    if (requestId === definitionRequest) definitions.value = []
  } finally {
    if (requestId === definitionRequest) definitionsLoading.value = false
  }
}

function buildPayload(): ItemFormPayload | null {
  notice.value = null
  const name = form.name.trim()
  if (!name) {
    notice.value = { type: 'error', message: '名称不能为空' }
    return null
  }
  const quantity = form.quantity.trim() === '' ? null : parseQuantity(form.quantity)
  if (form.quantity.trim() && (quantity === null || quantity < 0)) {
    notice.value = { type: 'error', message: quantityError.value || '数量格式不正确' }
    return null
  }

  const attributes = definitions.value
    .map((definition) => ({
      definition,
      value: (attributeValues[definition.key] || '').trim(),
    }))
    .filter((entry) => entry.value)
    .map(({ definition, value }) => ({
      name: definition.name,
      key: definition.key,
      value,
      value_type: definition.field_type || 'text',
      unit: definition.unit,
    }))

  return {
    name,
    category: form.category || null,
    location_code: form.locationCode || null,
    location_text: form.locationText.trim() || null,
    quantity,
    unit: form.unit.trim() || null,
    status: form.status,
    description: form.description.trim() || null,
    tags: parseTags(form.tags),
    note: '连续快速录入',
    attributes,
  }
}

async function save(mode: 'next' | 'detail') {
  const payload = buildPayload()
  if (!payload) return
  busy.value = true
  try {
    const item = await createItem(payload)
    sessionItems.value = [{ item, attributeCount: payload.attributes?.length || 0 }, ...sessionItems.value]
    lastPayload.value = payload
    await store.loadItems()
    await store.refreshStats()
    await store.selectItem(item.code)
    notice.value = { type: 'success', message: `已保存 ${item.code} · ${item.name}` }
    if (mode === 'detail') {
      await router.push({ name: 'items' })
      return
    }
    resetForNext()
  } catch (error) {
    notice.value = { type: 'error', message: error instanceof Error ? error.message : '保存失败' }
  } finally {
    busy.value = false
  }
}

function resetForNext() {
  form.name = ''
  form.quantity = ''
  form.tags = ''
  form.description = ''
  Object.keys(attributeValues).forEach((key) => delete attributeValues[key])
  if (settings.lockCategory) {
    form.category = settings.defaultCategory || form.category
  } else {
    form.category = ''
  }
  if (settings.lockLocation) {
    form.locationCode = settings.defaultLocationCode || form.locationCode
    form.locationText = settings.locationText || form.locationText
  } else {
    form.locationCode = ''
    form.locationText = ''
  }
  void nextTick(() => nameInput.value?.focus())
}

function copyPrevious() {
  const payload = lastPayload.value
  if (!payload) return
  form.name = payload.name
  form.category = typeof payload.category === 'string' ? payload.category : ''
  form.locationCode = payload.location_code || ''
  form.locationText = payload.location_text || ''
  form.quantity = payload.quantity == null ? '' : String(payload.quantity)
  form.unit = payload.unit || ''
  form.status = payload.status || 'normal'
  form.tags = (payload.tags || []).join(', ')
  form.description = payload.description || ''
  Object.keys(attributeValues).forEach((key) => delete attributeValues[key])
  void nextTick(() => {
    ;(payload.attributes || []).forEach((attribute) => {
      attributeValues[attribute.key] = attribute.value || ''
    })
    nameInput.value?.focus()
    nameInput.value?.select()
  })
}

async function viewItem(item: Item) {
  store.setQuery(item.code)
  store.setCategory(null)
  store.setLocation(null)
  store.setFavoriteOnly(false)
  store.setRestockOnly(false)
  await router.push({ name: 'items' })
  await store.loadItems()
  await store.selectItem(item.code)
}
</script>

<template>
  <section class="p-4 lg:p-5">
    <div class="mb-5 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-[24px] font-semibold">连续录入</h2>
        <p class="mt-1 text-[14px] text-muted">锁定分类和位置，边整理实物边快速建档。</p>
      </div>
      <div class="rounded-[8px] border border-green/20 bg-green/10 px-3 py-2 text-[13px] text-green">
        默认锁定分类和位置
      </div>
    </div>

    <div v-if="notice" class="mb-4 rounded-[8px] border px-3 py-2 text-[13px]" :class="notice.type === 'error' ? 'border-red-200 bg-red-50 text-red-700' : 'border-green/20 bg-green/10 text-green'">
      {{ notice.message }}
    </div>

    <div class="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
      <div class="grid gap-4">
        <section class="rounded-[8px] border border-line bg-white p-4 shadow-sm">
          <div class="mb-4 flex items-center justify-between gap-3">
            <h3 class="text-[16px] font-semibold">本次整理设置</h3>
            <button type="button" class="inline-flex h-9 items-center gap-2 rounded-[8px] border border-line px-3 text-[13px] text-ink/75" @click="settings.defaultCategory = ''; settings.defaultLocationCode = ''; settings.locationText = ''">
              <RefreshCw :size="15" />重置
            </button>
          </div>
          <div class="grid gap-4 md:grid-cols-2">
            <label>
              <span class="mb-1 block text-[13px] text-muted">默认分类</span>
              <select v-model="settings.defaultCategory" class="h-10 w-full rounded-[8px] border border-line bg-white px-3 outline-none focus:border-green">
                <option value="">未分类</option>
                <option v-for="category in categories" :key="category.id" :value="category.slug">{{ indentedName(category) }}</option>
              </select>
            </label>
            <label>
              <span class="mb-1 block text-[13px] text-muted">主位置</span>
              <select v-model="settings.defaultLocationCode" class="h-10 w-full rounded-[8px] border border-line bg-white px-3 outline-none focus:border-green">
                <option value="">未选择结构化位置</option>
                <option v-for="location in locations" :key="location.id" :value="location.full_code">{{ indentedName(location) }}</option>
              </select>
            </label>
            <label class="md:col-span-2">
              <span class="mb-1 block text-[13px] text-muted">文本位置</span>
              <input v-model="settings.locationText" class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-green" placeholder="例如 箱子2 · A03" />
            </label>
            <div class="flex flex-wrap gap-4 text-[14px] text-ink/80 md:col-span-2">
              <label class="inline-flex items-center gap-2"><input v-model="settings.lockCategory" type="checkbox" />锁定分类</label>
              <label class="inline-flex items-center gap-2"><input v-model="settings.lockLocation" type="checkbox" />锁定位置</label>
            </div>
          </div>
        </section>

        <form class="rounded-[8px] border border-line bg-white p-4 shadow-sm" @submit.prevent="save('next')">
          <div class="mb-4 flex items-center justify-between">
            <h3 class="text-[16px] font-semibold">快速添加物品</h3>
            <span v-if="selectedCategory" class="rounded-full bg-green/10 px-2.5 py-1 text-[12px] text-green">{{ selectedCategory.name }}</span>
          </div>
          <div class="grid gap-4 md:grid-cols-2">
            <label class="md:col-span-2">
              <span class="mb-1 block text-[13px] text-muted">名称</span>
              <input ref="nameInput" v-model="form.name" required class="h-11 w-full rounded-[8px] border border-line px-3 text-[15px] outline-none focus:border-green" placeholder="例如 10k 电阻" />
            </label>
            <label>
              <span class="mb-1 block text-[13px] text-muted">分类</span>
              <select v-model="form.category" class="h-10 w-full rounded-[8px] border border-line bg-white px-3 outline-none focus:border-green">
                <option value="">未分类</option>
                <option v-for="category in categories" :key="category.id" :value="category.slug">{{ indentedName(category) }}</option>
              </select>
            </label>
            <label>
              <span class="mb-1 block text-[13px] text-muted">主位置</span>
              <select v-model="form.locationCode" class="h-10 w-full rounded-[8px] border border-line bg-white px-3 outline-none focus:border-green">
                <option value="">不选择结构化位置</option>
                <option v-for="location in locations" :key="location.id" :value="location.full_code">{{ indentedName(location) }}</option>
              </select>
            </label>
            <label>
              <span class="mb-1 block text-[13px] text-muted">文本位置</span>
              <input v-model="form.locationText" class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-green" :placeholder="form.locationCode ? selectedLocationLabel(form.locationCode) : '箱子2 · A03'" />
            </label>
            <label>
              <span class="mb-1 block text-[13px] text-muted">数量</span>
              <input v-model="form.quantity" inputmode="decimal" class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-green" placeholder="100" />
              <span v-if="quantityError" class="mt-1 block text-[12px] text-red-600">{{ quantityError }}</span>
            </label>
            <label>
              <span class="mb-1 block text-[13px] text-muted">单位</span>
              <input v-model="form.unit" class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-green" placeholder="个 / 片 / 套" />
            </label>
            <label>
              <span class="mb-1 block text-[13px] text-muted">状态</span>
              <select v-model="form.status" class="h-10 w-full rounded-[8px] border border-line bg-white px-3 outline-none focus:border-green">
                <option value="normal">正常</option>
                <option value="low">较低</option>
                <option value="empty">用尽</option>
                <option value="broken">损坏</option>
                <option value="missing">丢失</option>
                <option value="idle">闲置</option>
              </select>
            </label>
            <label class="md:col-span-2">
              <span class="mb-1 block text-[13px] text-muted">标签</span>
              <input v-model="form.tags" class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-green" placeholder="0603, 1%" />
            </label>
            <label class="md:col-span-2">
              <span class="mb-1 block text-[13px] text-muted">备注</span>
              <textarea v-model="form.description" rows="3" class="w-full rounded-[8px] border border-line px-3 py-2 outline-none focus:border-green" placeholder="可选"></textarea>
            </label>
          </div>

          <section class="mt-4 rounded-[8px] border border-line bg-wash/60 p-3">
            <div class="mb-3 flex items-center justify-between gap-3">
              <h4 class="text-[14px] font-semibold">快速属性</h4>
              <span class="text-[12px] text-muted">{{ definitionsLoading ? '正在读取模板...' : definitions.length ? '选填' : '当前分类暂无模板' }}</span>
            </div>
            <div v-if="definitions.length" class="grid gap-3 md:grid-cols-2">
              <label v-for="definition in definitions" :key="definition.id">
                <span class="mb-1 block truncate text-[12px] text-muted">{{ definition.name }}{{ definition.unit ? ` (${definition.unit})` : '' }}</span>
                <input v-model="attributeValues[definition.key]" class="h-9 w-full rounded-[8px] border border-line bg-white px-3 text-[13px] outline-none focus:border-green" :placeholder="definition.key" />
              </label>
            </div>
          </section>

          <footer class="mt-4 flex flex-wrap justify-end gap-3 border-t border-line pt-4">
            <button type="button" :disabled="busy || !lastPayload" class="inline-flex h-10 items-center gap-2 rounded-[8px] border border-line px-4 text-[14px] disabled:opacity-50" @click="copyPrevious">
              <Copy :size="16" />复制上一条
            </button>
            <button type="button" :disabled="busy || !form.name.trim() || !!quantityError" class="inline-flex h-10 items-center gap-2 rounded-[8px] border border-green/30 px-4 text-[14px] font-medium text-green disabled:opacity-50" @click="save('detail')">
              <PackageCheck :size="16" />保存并查看详情
            </button>
            <button type="submit" :disabled="busy || !form.name.trim() || !!quantityError" class="inline-flex h-10 items-center gap-2 rounded-[8px] bg-green px-5 text-[14px] font-medium text-white disabled:opacity-50">
              <CheckCircle2 :size="16" />保存并录入下一个
            </button>
          </footer>
        </form>
      </div>

      <aside class="grid content-start gap-4">
        <section class="rounded-[8px] border border-line bg-white p-4 shadow-sm">
          <div class="mb-3 flex items-center justify-between gap-3">
            <h3 class="text-[16px] font-semibold">{{ sessionTitle }}</h3>
            <span class="rounded-full bg-wash px-2.5 py-1 text-[12px] text-muted">页面会话</span>
          </div>
          <div class="mb-3 flex flex-wrap gap-2">
            <span class="rounded-full border border-line px-2.5 py-1 text-[12px] text-muted">未补图 {{ unpicturedCount }}</span>
            <span class="rounded-full border border-line px-2.5 py-1 text-[12px] text-muted">待补属性 {{ unfilledAttributeCount }}</span>
            <span v-for="entry in categorySummary" :key="entry.label" class="rounded-full border border-line px-2.5 py-1 text-[12px] text-muted">{{ entry.label }} {{ entry.count }}</span>
          </div>
          <div v-if="!sessionItems.length" class="grid min-h-[180px] place-items-center rounded-[8px] border border-dashed border-line text-center text-[14px] text-muted">
            本次保存的物品会显示在这里。
          </div>
          <div v-else class="thin-scrollbar max-h-[520px] overflow-y-auto">
            <button v-for="entry in sessionItems" :key="entry.item.code" type="button" class="mb-2 w-full rounded-[8px] border border-line px-3 py-3 text-left hover:border-green hover:bg-green/5" @click="viewItem(entry.item)">
              <div class="flex items-start justify-between gap-3">
                <span class="min-w-0">
                  <span class="block truncate text-[14px] font-semibold">{{ entry.item.name }}</span>
                  <span class="mt-1 block text-[12px] text-muted">{{ entry.item.code }} · {{ statusLabel(entry.item.status) }}</span>
                </span>
                <span class="shrink-0 text-[13px] font-medium">{{ entry.item.quantity ?? '—' }} {{ entry.item.unit || '' }}</span>
              </div>
              <div class="mt-2 truncate text-[12px] text-muted">{{ locationLabel(entry.item) }}</div>
            </button>
          </div>
        </section>

        <section class="rounded-[8px] border border-line bg-white p-4 shadow-sm">
          <h3 class="mb-3 text-[16px] font-semibold">整理建议</h3>
          <div class="grid gap-2 text-[13px] text-ink/75">
            <div class="rounded-[8px] bg-wash px-3 py-2">同一抽屉连续录入时保持分类和位置锁定。</div>
            <div class="rounded-[8px] bg-wash px-3 py-2">相近规格用“复制上一条”后直接改名称和数量。</div>
            <div class="rounded-[8px] bg-wash px-3 py-2">照片、资料和完整属性可以稍后在详情页补齐。</div>
          </div>
        </section>
      </aside>
    </div>
  </section>
</template>
