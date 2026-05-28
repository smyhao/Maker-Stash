<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { Boxes, Pencil, Plus, Check, Trash2, X } from 'lucide-vue-next'

import { useInventoryStore } from '@/stores/inventory'
import type { Category } from '@/types'

const store = useInventoryStore()

const busy = ref(false)
const error = ref('')
const editorMode = ref<'create' | 'edit'>('create')
const selectedId = ref<number | null>(null)

const form = reactive({
  name: '',
  slug: '',
  codePrefix: '',
  parentId: '',
  sortOrder: '0',
  description: '',
})

const flatCategories = computed(() => {
  const result: Array<Category & { depth: number }> = []
  const walk = (nodes: Category[], depth = 0) => {
    nodes.forEach((node) => {
      result.push({ ...node, depth })
      walk(node.children || [], depth + 1)
    })
  }
  walk(store.categories)
  return result
})

const selectedCategory = computed(() => flatCategories.value.find((category) => category.id === selectedId.value) || null)
const parentOptions = computed(() => {
  if (editorMode.value !== 'edit' || !selectedCategory.value) return flatCategories.value
  const excluded = new Set<number>([selectedCategory.value.id])
  const collect = (nodes: Category[]) => {
    nodes.forEach((node) => {
      excluded.add(node.id)
      collect(node.children || [])
    })
  }
  collect(selectedCategory.value.children || [])
  return flatCategories.value.filter((category) => !excluded.has(category.id))
})

function normalizeSlug(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '')
}

function normalizeCodePrefix(value: string) {
  return value
    .trim()
    .toUpperCase()
    .replace(/\s+/g, '-')
    .replace(/[^A-Z0-9-]/g, '')
}

function countLabel(category: Category) {
  const count = store.categoryCounts.get(category.id) || 0
  return category.children?.length ? `${count} 件（含子类）` : `${count} 件`
}

function resetForm() {
  editorMode.value = 'create'
  selectedId.value = null
  form.name = ''
  form.slug = ''
  form.codePrefix = ''
  form.parentId = ''
  form.sortOrder = '0'
  form.description = ''
  error.value = ''
}

function prepareCreate(parent?: Category | null) {
  editorMode.value = 'create'
  selectedId.value = null
  form.name = ''
  form.slug = ''
  form.codePrefix = ''
  form.parentId = parent ? String(parent.id) : ''
  form.sortOrder = parent?.sort_order != null ? String(parent.sort_order + 10) : '0'
  form.description = ''
  error.value = ''
}

function prepareEdit(category: Category) {
  editorMode.value = 'edit'
  selectedId.value = category.id
  form.name = category.name
  form.slug = category.slug
  form.codePrefix = category.code_prefix
  form.parentId = category.parent_id == null ? '' : String(category.parent_id)
  form.sortOrder = String(category.sort_order || 0)
  form.description = category.description || ''
  error.value = ''
}

async function save() {
  error.value = ''
  const name = form.name.trim()
  if (!name) {
    error.value = '分类名称不能为空'
    return
  }
  const slug = normalizeSlug(form.slug || name)
  const codePrefix = normalizeCodePrefix(form.codePrefix)
  if (editorMode.value === 'create' && !slug) {
    error.value = 'slug 不能为空，且只能使用英文、数字和横线'
    return
  }
  if (editorMode.value === 'create' && !codePrefix) {
    error.value = '编号前缀不能为空'
    return
  }
  busy.value = true
  try {
    await store.saveCategory(
      {
        name,
        slug,
        code_prefix: codePrefix,
        parent_id: form.parentId ? Number(form.parentId) : null,
        sort_order: Number(form.sortOrder) || 0,
        description: form.description.trim() || null,
      },
      editorMode.value === 'edit' ? selectedId.value || undefined : undefined,
    )
    resetForm()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '保存分类失败'
  } finally {
    busy.value = false
  }
}

async function removeCategory(category: Category) {
  if (!window.confirm(`删除分类「${category.name}」？如果分类下仍有物品，后端会拒绝删除。`)) return
  busy.value = true
  error.value = ''
  try {
    await store.deleteCategory(category.id)
    if (selectedId.value === category.id) {
      resetForm()
    }
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '删除分类失败'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="px-4 py-4 2xl:px-5">
    <div class="mb-4 flex items-center justify-between gap-3">
      <div>
        <h2 class="text-[22px] font-semibold">分类管理</h2>
        <p class="mt-1 text-[14px] text-muted">维护分类树、显示名称和编号前缀。已有分类的 slug 与前缀当前保持稳定，不在前端直接改写。</p>
      </div>
      <button class="inline-flex h-10 items-center gap-2 rounded-[8px] bg-blue px-4 text-[14px] font-medium text-white" @click="prepareCreate(null)">
        <Plus :size="16" />
        新增根分类
      </button>
    </div>

    <div v-if="error" class="mb-4 rounded-[8px] border border-red-200 bg-red-50 px-3 py-2 text-[13px] text-red-700">
      {{ error }}
    </div>

    <div class="grid gap-4 xl:grid-cols-[minmax(320px,420px)_1fr]">
      <div class="rounded-[8px] border border-line bg-white p-2 shadow-sm">
        <div class="mb-2 flex items-center gap-2 px-2 py-2 text-[15px] font-semibold">
          <Boxes :size="18" />
          分类树
        </div>
        <div
          v-for="category in flatCategories"
          :key="category.id"
          class="mb-1 grid w-full cursor-pointer grid-cols-[1fr_auto_auto] items-center gap-2 rounded-[6px] px-2 py-2 text-left focus:outline-none focus:ring-2 focus:ring-blue/30"
          :class="selectedId === category.id ? 'bg-blue/10 text-blue' : 'hover:bg-slate-50'"
          :style="{ paddingLeft: `${8 + category.depth * 18}px` }"
          role="button"
          tabindex="0"
          @click="prepareEdit(category)"
          @keydown.enter.prevent="prepareEdit(category)"
          @keydown.space.prevent="prepareEdit(category)"
        >
          <span class="min-w-0">
            <span class="block truncate text-[14px] font-medium">{{ category.name }}</span>
            <span class="block text-[12px] text-muted">{{ category.slug }} · {{ category.code_prefix }}</span>
          </span>
          <span class="rounded-[6px] bg-slate-100 px-2 py-1 text-[12px] text-muted" :title="countLabel(category)">{{ countLabel(category) }}</span>
          <button class="grid h-8 w-8 place-items-center rounded-[6px] border border-line text-ink/70 hover:border-blue hover:text-blue" @click.stop="prepareCreate(category)">
            <Plus :size="14" />
          </button>
        </div>
      </div>

      <div class="rounded-[8px] border border-line bg-white p-5 shadow-sm">
        <div class="mb-4 flex items-center justify-between">
          <h3 class="text-[18px] font-semibold">{{ editorMode === 'create' ? '新增分类' : '编辑分类' }}</h3>
          <button v-if="editorMode === 'edit'" class="inline-flex h-9 items-center gap-2 rounded-[8px] border border-red-200 px-3 text-[13px] text-red-600" @click="selectedCategory && removeCategory(selectedCategory)">
            <Trash2 :size="14" />
            删除
          </button>
          <button v-else class="grid h-9 w-9 place-items-center rounded-[8px] border border-line text-muted" @click="resetForm">
            <X :size="16" />
          </button>
        </div>

        <div class="grid gap-4 md:grid-cols-2">
          <label class="md:col-span-2">
            <span class="mb-1 block text-[13px] text-muted">名称</span>
            <input v-model="form.name" class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue" />
          </label>

          <label>
            <span class="mb-1 block text-[13px] text-muted">slug</span>
            <input
              v-model="form.slug"
              :disabled="editorMode === 'edit'"
              class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue disabled:bg-slate-50"
              placeholder="components"
              @blur="form.slug = normalizeSlug(form.slug || form.name)"
            />
          </label>

          <label>
            <span class="mb-1 block text-[13px] text-muted">编号前缀</span>
            <input
              v-model="form.codePrefix"
              :disabled="editorMode === 'edit'"
              class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue disabled:bg-slate-50"
              placeholder="ELE"
              @blur="form.codePrefix = normalizeCodePrefix(form.codePrefix)"
            />
          </label>

          <label>
            <span class="mb-1 block text-[13px] text-muted">父分类</span>
            <select v-model="form.parentId" class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue">
              <option value="">无</option>
              <option v-for="category in parentOptions" :key="category.id" :value="String(category.id)">
                {{ `${'　'.repeat(category.depth)}${category.name}` }}
              </option>
            </select>
          </label>

          <label>
            <span class="mb-1 block text-[13px] text-muted">排序</span>
            <input v-model="form.sortOrder" type="number" class="h-10 w-full rounded-[8px] border border-line px-3 outline-none focus:border-blue" />
          </label>

          <label class="md:col-span-2">
            <span class="mb-1 block text-[13px] text-muted">描述</span>
            <textarea v-model="form.description" rows="4" class="w-full rounded-[8px] border border-line px-3 py-2 outline-none focus:border-blue" />
          </label>
        </div>

        <div v-if="editorMode === 'edit'" class="mt-4 rounded-[8px] border border-amber-200 bg-amber-50 px-3 py-2 text-[13px] text-amber-800">
          slug 与编号前缀保持稳定，避免已有物品编号和外部调用失配；可调整父分类以整理分类层级。
        </div>

        <div class="mt-5 flex justify-end gap-3">
          <button class="h-10 rounded-[8px] border border-line px-4 text-[14px]" @click="resetForm">重置</button>
          <button :disabled="busy" class="inline-flex h-10 items-center gap-2 rounded-[8px] bg-blue px-5 text-[14px] font-medium text-white disabled:opacity-50" @click="save">
            <Check :size="16" />
            保存分类
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
