import { defineStore } from 'pinia'

import { createLocation, deleteLocation, fetchCategories, fetchLocations, updateLocation } from '@/api/catalog'
import { fetchStatsOverview } from '@/api/stats'
import {
  addItemQuantity,
  addItemTags,
  createItemAttribute,
  createItem,
  deleteItem,
  deleteAttachment,
  deleteItemAttribute,
  fetchItemAttachments,
  fetchItemAttributes,
  fetchItemNotes,
  fetchItems,
  fetchItemTags,
  moveItem,
  updateItem,
  toggleFavorite,
  toggleRestock,
  removeItemTag,
  uploadItemAttachment,
  updateItemAttribute,
  useItem,
} from '@/api/items'
import type { Attachment, Category, Item, ItemAttribute, ItemFormPayload, LocationFormPayload, LocationNode, Note, StatsOverview, Tag } from '@/types'

interface InventoryState {
  items: Item[]
  categories: Category[]
  locations: LocationNode[]
  selectedCode: string | null
  total: number
  page: number
  pageSize: number
  loading: boolean
  error: string | null
  query: string
  activeCategory: string | null
  activeLocationCode: string | null
  favoriteOnly: boolean
  restockOnly: boolean
  lowOnly: boolean
  selectedAttributes: ItemAttribute[]
  selectedTags: Tag[]
  selectedNotes: Note[]
  selectedAttachments: Attachment[]
  stats: StatsOverview | null
}

export const useInventoryStore = defineStore('inventory', {
  state: (): InventoryState => ({
    items: [],
    categories: [],
    locations: [],
    selectedCode: null,
    total: 0,
    page: 1,
    pageSize: 10,
    loading: false,
    error: null,
    query: '',
    activeCategory: null,
    activeLocationCode: null,
    favoriteOnly: false,
    restockOnly: false,
    lowOnly: false,
    selectedAttributes: [],
    selectedTags: [],
    selectedNotes: [],
    selectedAttachments: [],
    stats: null,
  }),

  getters: {
    selectedItem(state) {
      return state.items.find((item) => item.code === state.selectedCode) || state.items[0] || null
    },
    categoryById(state) {
      const map = new Map<number, Category>()
      const walk = (nodes: Category[]) => {
        nodes.forEach((node) => {
          map.set(node.id, node)
          walk(node.children || [])
        })
      }
      walk(state.categories)
      return map
    },
    locationById(state) {
      const map = new Map<number, LocationNode>()
      const walk = (nodes: LocationNode[]) => {
        nodes.forEach((node) => {
          map.set(node.id, node)
          walk(node.children || [])
        })
      }
      walk(state.locations)
      return map
    },
    flatLocations(state) {
      const result: Array<LocationNode & { depth: number }> = []
      const walk = (nodes: LocationNode[], depth = 0) => {
        nodes.forEach((node) => {
          result.push({ ...node, depth })
          walk(node.children || [], depth + 1)
        })
      }
      walk(state.locations)
      return result
    },
    locationCounts(state) {
      const counts = new Map<number, number>()
      state.stats?.location_counts.forEach((item) => counts.set(item.location_id, item.count))
      return counts
    },
    flatCategories(state) {
      const result: Array<Category & { depth: number }> = []
      const walk = (nodes: Category[], depth = 0) => {
        nodes.forEach((node) => {
          if (node.slug) {
            result.push({ ...node, depth })
          }
          walk(node.children || [], depth + 1)
        })
      }
      walk(state.categories)
      return result
    },
    categoryCounts(state) {
      const counts = new Map<number, number>()
      state.stats?.category_counts.forEach((item) => counts.set(item.category_id, item.count))
      return counts
    },
  },

  actions: {
    async bootstrap() {
      this.loading = true
      this.error = null
      try {
        const [categories, locations, stats] = await Promise.all([fetchCategories(), fetchLocations(), fetchStatsOverview()])
        this.categories = categories.categories
        this.locations = locations.locations
        this.stats = stats
        await this.loadItems()
      } catch (error) {
        this.error = error instanceof Error ? error.message : '无法连接后端，已显示演示数据'
        this.useDemoData()
      } finally {
        this.loading = false
      }
    },

    async loadItems() {
      const data = await fetchItems({
        q: this.query || undefined,
        category: this.activeCategory || undefined,
        location: this.activeLocationCode || undefined,
        favorite: this.favoriteOnly || undefined,
        need_restock: this.restockOnly || undefined,
        page: this.page,
        page_size: this.pageSize,
      })
      this.items = this.lowOnly ? data.items.filter((item) => item.status === 'low') : data.items
      this.total = this.lowOnly ? this.items.length : data.total
      if (this.selectedCode && !this.items.some((item) => item.code === this.selectedCode)) {
        this.selectedCode = null
      }
      if (!this.selectedCode && this.items[0]) {
        this.selectedCode = this.items[0].code
        await this.loadSelectedMeta()
      }
      if (!this.items.length) {
        this.selectedCode = null
        this.selectedAttributes = []
        this.selectedTags = []
        this.selectedNotes = []
        this.selectedAttachments = []
      }
    },

    async selectItem(code: string) {
      this.selectedCode = code
      await this.loadSelectedMeta()
    },

    async loadSelectedMeta() {
      const item = this.selectedItem
      if (!item) return
      try {
        const [attributes, tags, notes, attachments] = await Promise.all([
          fetchItemAttributes(item.code),
          fetchItemTags(item.code),
          fetchItemNotes(item.code),
          fetchItemAttachments(item.code),
        ])
        this.selectedAttributes = attributes.attributes
        this.selectedTags = tags.tags
        this.selectedNotes = notes.notes
        this.selectedAttachments = attachments.attachments
      } catch {
        this.selectedAttributes = []
        this.selectedTags = []
        this.selectedNotes = []
        this.selectedAttachments = []
      }
    },

    setQuery(query: string) {
      this.query = query
      this.page = 1
    },

    setCategory(slug: string | null) {
      this.activeCategory = slug
      this.page = 1
    },

    setLocation(code: string | null) {
      this.activeLocationCode = code
      this.page = 1
    },

    setFavoriteOnly(value: boolean) {
      this.favoriteOnly = value
      this.page = 1
    },

    setRestockOnly(value: boolean) {
      this.restockOnly = value
      this.page = 1
    },

    setLowOnly(value: boolean) {
      this.lowOnly = value
      this.page = 1
    },

    clearFilters() {
      this.favoriteOnly = false
      this.restockOnly = false
      this.lowOnly = false
      this.activeLocationCode = null
      this.page = 1
    },

    async setPage(page: number) {
      const totalPages = Math.max(1, Math.ceil(this.total / this.pageSize))
      this.page = Math.min(Math.max(page, 1), totalPages)
      await this.loadItems()
    },

    useDemoData() {
      this.categories = demoCategories
      this.locations = demoLocations
      this.items = demoItems
      this.total = 126
      this.selectedCode = demoItems[0]?.code || null
      this.selectedAttributes = demoAttributes
      this.selectedTags = demoTags
      this.selectedNotes = demoNotes
      this.selectedAttachments = []
      this.stats = demoStats
      this.page = 1
      this.pageSize = 10
    },

    async refreshStats() {
      try {
        this.stats = await fetchStatsOverview()
      } catch {
        if (!this.stats) this.stats = demoStats
      }
    },

    async saveItem(payload: ItemFormPayload, code?: string) {
      let saved: Item | null = null
      if (code) {
        saved = await updateItem(code, payload)
      } else {
        saved = await createItem(payload)
        this.query = ''
        this.activeCategory = null
        this.activeLocationCode = null
        this.favoriteOnly = false
        this.restockOnly = false
        this.lowOnly = false
        this.page = 1
      }
      await this.loadItems()
      await this.refreshStats()
      if (code) {
        await this.selectItem(code)
      } else if (saved) {
        if (!this.items.some((item) => item.code === saved.code)) {
          this.items = [saved, ...this.items]
        }
        await this.selectItem(saved.code)
      } else if (this.items[0]) {
        await this.selectItem(this.items[0].code)
      }
    },

    async addQuantity(amount: number, note: string) {
      const item = this.selectedItem
      if (!item) return
      await addItemQuantity(item.code, amount, item.unit || undefined, note || '前端入库')
      await this.loadItems()
      await this.refreshStats()
      await this.selectItem(item.code)
    },

    async useQuantity(amount: number, note: string) {
      const item = this.selectedItem
      if (!item) return
      await useItem(item.code, amount, item.unit || undefined, note || '前端出库')
      await this.loadItems()
      await this.refreshStats()
      await this.selectItem(item.code)
    },

    async archiveSelected(deleteAttachments: boolean) {
      const item = this.selectedItem
      if (!item) return
      await deleteItem(item.code, deleteAttachments)
      this.selectedCode = null
      await this.loadItems()
      await this.refreshStats()
      if (this.items[0]) {
        await this.selectItem(this.items[0].code)
      }
    },

    async toggleSelectedFavorite() {
      const item = this.selectedItem
      if (!item) return
      await toggleFavorite(item.code, !item.is_favorite)
      await this.loadItems()
      await this.refreshStats()
      await this.selectItem(item.code)
    },

    async toggleSelectedRestock() {
      const item = this.selectedItem
      if (!item) return
      await toggleRestock(item.code, !item.need_restock)
      await this.loadItems()
      await this.refreshStats()
      await this.selectItem(item.code)
    },

    async uploadSelectedAttachment(file: File) {
      const item = this.selectedItem
      if (!item) return
      await uploadItemAttachment(item.code, file)
      await this.loadSelectedMeta()
      await this.refreshStats()
    },

    async deleteSelectedAttachment(id: number) {
      await deleteAttachment(id)
      await this.loadSelectedMeta()
      await this.refreshStats()
    },

    async addSelectedTags(tags: string[]) {
      const item = this.selectedItem
      if (!item || !tags.length) return
      await addItemTags(item.code, tags)
      await this.loadSelectedMeta()
    },

    async removeSelectedTag(tag: string) {
      const item = this.selectedItem
      if (!item) return
      await removeItemTag(item.code, tag)
      await this.loadSelectedMeta()
    },

    async createSelectedAttribute(payload: { name: string; key: string; value?: string | null; unit?: string | null }) {
      const item = this.selectedItem
      if (!item) return
      await createItemAttribute(item.code, { ...payload, value_type: 'text' })
      await this.loadSelectedMeta()
    },

    async updateSelectedAttribute(id: number, payload: { name?: string; value?: string | null; unit?: string | null }) {
      await updateItemAttribute(id, { ...payload, value_type: 'text' })
      await this.loadSelectedMeta()
    },

    async deleteSelectedAttribute(id: number) {
      await deleteItemAttribute(id)
      await this.loadSelectedMeta()
    },

    async saveLocation(payload: LocationFormPayload, id?: number) {
      if (id) {
        await updateLocation(id, {
          name: payload.name,
          type: payload.type || null,
          description: payload.description || null,
          sort_order: payload.sort_order || 0,
        })
      } else {
        await createLocation({
          name: payload.name,
          code: payload.code || '',
          parent_code: payload.parent_code || null,
          type: payload.type || null,
          description: payload.description || null,
          sort_order: payload.sort_order || 0,
        })
      }
      const locations = await fetchLocations()
      this.locations = locations.locations
      await this.refreshStats()
    },

    async deleteLocation(id: number) {
      await deleteLocation(id)
      const locations = await fetchLocations()
      this.locations = locations.locations
      await this.refreshStats()
      if (this.activeLocationCode && !this.flatLocations.some((location) => location.full_code === this.activeLocationCode)) {
        this.activeLocationCode = null
        await this.loadItems()
      }
    },

    async moveSelectedToLocation(locationCode: string | null, locationText?: string | null) {
      const item = this.selectedItem
      if (!item) return
      await moveItem(item.code, locationCode, locationText || null, '前端移动位置')
      await this.loadItems()
      await this.refreshStats()
      await this.selectItem(item.code)
    },
  },
})

const demoCategories: Category[] = [
  { id: 1, name: '全部', slug: '', code_prefix: '', parent_id: null, sort_order: 0, is_system: true },
  { id: 2, name: '元器件', slug: 'components', code_prefix: 'ELE', parent_id: null, sort_order: 1, is_system: true },
  { id: 3, name: '3D耗材', slug: 'filament', code_prefix: 'FIL', parent_id: null, sort_order: 2, is_system: true },
  { id: 4, name: '工具', slug: 'tools', code_prefix: 'TOOL', parent_id: null, sort_order: 3, is_system: true },
  { id: 5, name: '备用材料', slug: 'materials', code_prefix: 'MAT', parent_id: null, sort_order: 4, is_system: true },
  { id: 6, name: '线材', slug: 'cables', code_prefix: 'CAB', parent_id: null, sort_order: 5, is_system: true },
]

const demoLocations: LocationNode[] = [
  {
    id: 1,
    name: '工坊',
    code: 'WS',
    full_code: 'WS',
    parent_id: null,
    type: 'room',
    description: null,
    sort_order: 0,
    children: [
      { id: 2, name: '干燥箱 A', code: 'DRY-A', full_code: 'WS.DRY-A', parent_id: 1, type: 'drybox', description: null, sort_order: 1, children: [] },
      { id: 3, name: '元件柜', code: 'ELE-CAB', full_code: 'WS.ELE-CAB', parent_id: 1, type: 'cabinet', description: null, sort_order: 2, children: [] },
      { id: 4, name: '工具墙', code: 'TOOL-WALL', full_code: 'WS.TOOL-WALL', parent_id: 1, type: 'wall', description: null, sort_order: 3, children: [] },
    ],
  },
]

const demoItems: Item[] = [
  { id: 1, code: 'FIL-000001', name: '黑色 PLA', category_id: 3, location_id: 2, location_text: '干燥箱 A · 格 03', quantity: '0.42', unit: 'kg', status: 'normal', description: '打印前建议烘干 4 小时。', need_restock: false, is_favorite: true, cover_attachment_id: null, is_archived: false },
  { id: 2, code: 'ELE-000012', name: 'ESP32-S3 模块', category_id: 2, location_id: 3, location_text: '元件柜 · 抽屉 02', quantity: '12', unit: '片', status: 'normal', description: null, need_restock: false, is_favorite: true, cover_attachment_id: null, is_archived: false },
  { id: 3, code: 'TOOL-000003', name: '精密螺丝刀套装', category_id: 4, location_id: 4, location_text: '工具墙 · 挂钩 07', quantity: '1', unit: '套', status: 'normal', description: null, need_restock: false, is_favorite: false, cover_attachment_id: null, is_archived: false },
  { id: 4, code: 'MAT-000018', name: 'M3 热熔螺母', category_id: 5, location_id: 3, location_text: '零件盒 · Bin 15', quantity: '250', unit: '个', status: 'low', description: null, need_restock: true, is_favorite: false, cover_attachment_id: null, is_archived: false },
  { id: 5, code: 'CAB-000007', name: 'Type-C 硅胶线', category_id: 6, location_id: 3, location_text: '线材架 · 层 02', quantity: '3', unit: '根', status: 'normal', description: null, need_restock: false, is_favorite: false, cover_attachment_id: null, is_archived: false },
]

const demoAttributes: ItemAttribute[] = [
  { id: 1, item_id: 1, name: '材质', key: 'material', value: 'PLA', unit: null },
  { id: 2, item_id: 1, name: '颜色', key: 'color', value: '黑色', unit: null },
  { id: 3, item_id: 1, name: '线径', key: 'diameter', value: '1.75', unit: 'mm' },
  { id: 4, item_id: 1, name: '净重', key: 'weight', value: '1', unit: 'kg' },
]

const demoTags: Tag[] = [
  { id: 1, name: 'PLA', slug: null },
  { id: 2, name: '1.75mm', slug: null },
  { id: 3, name: '黑色', slug: null },
]

const demoNotes: Note[] = [
  { id: 1, content: '入库 +0.50kg，手动入库', note_type: 'add', source: 'web', created_at: '2024-05-20 10:15' },
  { id: 2, content: '出库 -0.30kg，3D 打印消耗', note_type: 'use', source: 'web', created_at: '2024-05-18 14:32' },
  { id: 3, content: '入库 +1.00kg，手动入库', note_type: 'add', source: 'web', created_at: '2024-05-15 09:08' },
]

const demoStats: StatsOverview = {
  item_count: 126,
  archived_item_count: 0,
  low_stock_count: 7,
  restock_count: 7,
  favorite_count: 12,
  unlocated_count: 0,
  uncategorized_count: 0,
  attachment_count: 0,
  category_counts: [
    { category_id: 2, name: '元器件', count: 48 },
    { category_id: 3, name: '3D耗材', count: 12 },
    { category_id: 4, name: '工具', count: 23 },
    { category_id: 5, name: '备用材料', count: 18 },
    { category_id: 6, name: '线材', count: 13 },
  ],
  location_counts: [
    { location_id: 1, name: '工坊', full_code: 'WS', count: 126 },
    { location_id: 2, name: '干燥箱 A', full_code: 'WS.DRY-A', count: 12 },
    { location_id: 3, name: '元件柜', full_code: 'WS.ELE-CAB', count: 46 },
    { location_id: 4, name: '工具墙', full_code: 'WS.TOOL-WALL', count: 23 },
  ],
}
