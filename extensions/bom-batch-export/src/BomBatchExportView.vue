<script setup lang="ts">
import { computed, ref } from 'vue'
import { AlertTriangle, CheckCircle2, Download, FileDown, FileSpreadsheet, RefreshCw, Search, Trash2, UploadCloud } from 'lucide-vue-next'
import * as XLSX from 'xlsx'

import {
  confirmWorkflowPlan,
  createBatchOutboundPlan,
  fetchCapabilities,
  fetchItem,
  fetchItemsByTag,
  fetchTaskStatus,
  searchItems,
  type Item,
  type SearchItem,
  type TaskStatus,
  type WorkflowPlan,
} from './api'

type MatchStatus = 'pending' | 'matched' | 'conflict' | 'unmatched' | 'excluded'

interface MatchCandidate {
  code: string
  name: string
  quantity: string | number | null
  unit: string | null
  location_display?: string | null
  score: number
  reason: string
}

interface BomRow {
  id: number
  original: Record<string, string>
  included: boolean
  quantity: number | null
  supplierPart: string
  comment: string
  footprint: string
  candidates: MatchCandidate[]
  selected: MatchCandidate | null
  status: MatchStatus
  matchReason: string
  manualQuery: string
}

const MODULE_NAME = 'bom-batch-export'
const OPERATOR = 'web-ui'

const fileName = ref('')
const headers = ref<string[]>([])
const rows = ref<BomRow[]>([])
const busy = ref(false)
const matching = ref(false)
const message = ref('')
const error = ref('')
const currentPlan = ref<WorkflowPlan | null>(null)
const taskStatus = ref<TaskStatus | null>(null)
const confirming = ref(false)
const confirmError = ref('')

const includedRows = computed(() => rows.value.filter((row) => row.included))
const matchedRows = computed(() => includedRows.value.filter((row) => row.status === 'matched' && row.selected && row.quantity && row.quantity > 0))
const unresolvedRows = computed(() => includedRows.value.filter((row) => row.status === 'conflict' || row.status === 'unmatched' || row.status === 'pending'))
const summary = computed(() => ({
  total: rows.value.length,
  included: includedRows.value.length,
  matched: includedRows.value.filter((row) => row.status === 'matched').length,
  conflict: includedRows.value.filter((row) => row.status === 'conflict').length,
  unmatched: includedRows.value.filter((row) => row.status === 'unmatched').length,
  excluded: rows.value.filter((row) => !row.included).length,
}))
const canCreatePlan = computed(() => matchedRows.value.length > 0 && unresolvedRows.value.length === 0)
const canConfirmPlan = computed(() => currentPlan.value && currentPlan.value.failures.length === 0 && currentPlan.value.status !== 'confirmed')
const hasIncludedUnresolvedRows = computed(() => unresolvedRows.value.some((row) => row.included))
const planFailureMessages = computed(() => currentPlan.value?.failures.map(formatPlanFailure) || [])
const outboundDone = computed(() => taskStatus.value?.status === 'succeeded' || currentPlan.value?.status === 'confirmed')

async function handleFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  await loadFile(file)
  input.value = ''
}

async function loadFile(file: File) {
  resetState()
  busy.value = true
  try {
    await ensureCapabilities(file)
    const matrix = await parseBomFile(file)
    if (matrix.length < 2) {
      throw new Error('BOM 文件至少需要表头和一行数据')
    }
    headers.value = matrix[0].map((value) => cleanCell(value)).filter(Boolean)
    rows.value = matrix.slice(1)
      .filter((line) => line.some((value) => cleanCell(value)))
      .map((line, index) => createBomRow(index + 1, headers.value, line))
    fileName.value = file.name
    message.value = `已读取 ${rows.value.length} 行 BOM 数据`
    await matchAllRows()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '读取 BOM 文件失败'
  } finally {
    busy.value = false
  }
}

function resetState() {
  headers.value = []
  rows.value = []
  fileName.value = ''
  message.value = ''
  error.value = ''
  currentPlan.value = null
  taskStatus.value = null
  confirming.value = false
  confirmError.value = ''
}

async function ensureCapabilities(file: File) {
  const capabilities = await fetchCapabilities()
  if (!capabilities.features.items || !capabilities.features.search || !capabilities.features.workflow_plan_confirm) {
    throw new Error('当前主干能力不足：需要 items、search 和 workflow_plan_confirm')
  }
  if (file.size > capabilities.limits.max_upload_bytes) {
    throw new Error(`文件大小超过限制：${Math.round(capabilities.limits.max_upload_bytes / 1024 / 1024)} MB`)
  }
}

async function parseBomFile(file: File): Promise<string[][]> {
  const name = file.name.toLowerCase()
  if (name.endsWith('.xlsx') || name.endsWith('.xls')) {
    const data = await file.arrayBuffer()
    const workbook = XLSX.read(data, { type: 'array' })
    const sheet = workbook.Sheets[workbook.SheetNames[0]]
    return XLSX.utils.sheet_to_json<string[]>(sheet, { header: 1, defval: '' })
  }
  const text = decodeTextFile(await file.arrayBuffer())
  return parseDelimitedText(text)
}

function decodeTextFile(buffer: ArrayBuffer) {
  const bytes = new Uint8Array(buffer)
  if (bytes[0] === 0xFF && bytes[1] === 0xFE) {
    return new TextDecoder('utf-16le').decode(bytes)
  }
  if (bytes[0] === 0xFE && bytes[1] === 0xFF) {
    return new TextDecoder('utf-16be').decode(bytes)
  }
  const sample = bytes.slice(0, Math.min(bytes.length, 200))
  const nulOdd = sample.filter((_, index) => index % 2 === 1 && sample[index] === 0).length
  if (nulOdd > sample.length / 4) {
    return new TextDecoder('utf-16le').decode(bytes)
  }
  return new TextDecoder('utf-8').decode(bytes)
}

function parseDelimitedText(text: string) {
  const normalized = text.replace(/^\uFEFF/, '').replace(/\r\n/g, '\n').replace(/\r/g, '\n')
  const firstLine = normalized.split('\n').find((line) => line.trim()) || ''
  const delimiter = (firstLine.match(/\t/g)?.length || 0) >= (firstLine.match(/,/g)?.length || 0) ? '\t' : ','
  const parsed = XLSX.read(normalized, { type: 'string', raw: false, FS: delimiter })
  const sheet = parsed.Sheets[parsed.SheetNames[0]]
  return XLSX.utils.sheet_to_json<string[]>(sheet, { header: 1, defval: '' })
}

function createBomRow(id: number, rowHeaders: string[], line: string[]): BomRow {
  const original: Record<string, string> = {}
  rowHeaders.forEach((header, index) => {
    original[header] = cleanCell(line[index])
  })
  const supplierPart = readField(original, ['Supplier Part', 'SupplierPart', 'LCSC', 'LCSC Part', '供应商料号'])
  const comment = readField(original, ['Comment', 'Name', '名称', '备注'])
  const footprint = readField(original, ['Footprint', 'Package', '封装'])
  return {
    id,
    original,
    included: true,
    quantity: parseQuantity(readField(original, ['Quantity', 'Qty', '数量'])),
    supplierPart,
    comment,
    footprint,
    candidates: [],
    selected: null,
    status: 'pending',
    matchReason: '',
    manualQuery: supplierPart || [comment, footprint].filter(Boolean).join(' '),
  }
}

function cleanCell(value: unknown) {
  return String(value ?? '').trim()
}

function normalizeKey(value: string) {
  return value.toLowerCase().replace(/[\s_.-]+/g, '')
}

function readField(source: Record<string, string>, names: string[]) {
  const wanted = names.map(normalizeKey)
  const found = Object.entries(source).find(([key]) => wanted.includes(normalizeKey(key)))
  return found?.[1]?.trim() || ''
}

function parseQuantity(value: string) {
  const parsed = Number(value.replace(/,/g, '').trim())
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
}

async function matchAllRows() {
  matching.value = true
  currentPlan.value = null
  taskStatus.value = null
  confirmError.value = ''
  try {
    for (const row of rows.value) {
      if (row.included) {
        await matchRow(row)
      }
    }
    message.value = `匹配完成：${summary.value.matched} 行已匹配，${summary.value.conflict} 行冲突，${summary.value.unmatched} 行未匹配`
  } catch (err) {
    error.value = err instanceof Error ? err.message : '匹配失败'
  } finally {
    matching.value = false
  }
}

async function matchRow(row: BomRow) {
  row.status = 'pending'
  row.selected = null
  row.candidates = []
  row.matchReason = ''

  if (row.supplierPart) {
    const exact = await fetchItemsByTag(row.supplierPart)
    row.candidates = exact.items.map((item) => itemToCandidate(item, 100, `标签命中 ${row.supplierPart}`))
    if (applyCandidates(row)) {
      return
    }
  }

  const fuzzyCandidates = await fuzzySearch(row)
  row.candidates = fuzzyCandidates
  applyCandidates(row)
}

function applyCandidates(row: BomRow) {
  if (row.candidates.length === 1 && row.candidates[0].score >= 70) {
    row.selected = row.candidates[0]
    row.status = 'matched'
    row.matchReason = row.selected.reason
    return true
  }
  if (row.candidates.length > 1) {
    row.status = 'conflict'
    row.matchReason = '存在多个候选，需要人工指定'
    return true
  }
  row.status = 'unmatched'
  row.matchReason = '未找到匹配物品'
  return false
}

async function fuzzySearch(row: BomRow) {
  const queries = [row.comment, row.footprint].filter(Boolean)
  const candidateMap = new Map<string, MatchCandidate>()
  for (const query of queries) {
    const result = await searchItems(query, 20)
    for (const item of result.items) {
      const candidate = searchItemToCandidate(item, row)
      const existing = candidateMap.get(candidate.code)
      if (!existing || candidate.score > existing.score) {
        candidateMap.set(candidate.code, candidate)
      }
    }
  }
  return [...candidateMap.values()]
    .filter((candidate) => candidate.score >= 45)
    .sort((a, b) => b.score - a.score)
    .slice(0, 8)
}

function itemToCandidate(item: Item, score: number, reason: string): MatchCandidate {
  return {
    code: item.code,
    name: item.name,
    quantity: item.quantity,
    unit: item.unit,
    location_display: item.location_display || item.location_text,
    score,
    reason,
  }
}

function searchItemToCandidate(item: SearchItem, row: BomRow): MatchCandidate {
  const text = `${item.code} ${item.name} ${item.category_name || ''} ${item.location_full_code || ''}`.toLowerCase()
  const comment = row.comment.toLowerCase()
  const footprint = row.footprint.toLowerCase()
  let score = 35
  if (comment && text.includes(comment)) score += 35
  if (footprint && text.includes(footprint)) score += 20
  if (item.matched_by.includes('tag')) score += 20
  if (item.matched_by.includes('attribute') || item.matched_by.includes('alias')) score += 15
  return {
    code: item.code,
    name: item.name,
    quantity: item.quantity,
    unit: item.unit,
    location_display: item.location_full_code || null,
    score,
    reason: `模糊匹配 ${item.matched_by.join('/')}`,
  }
}

async function manualSearch(row: BomRow) {
  const query = row.manualQuery.trim()
  if (!query) return
  const result = await searchItems(query, 20)
  row.candidates = result.items.map((item) => searchItemToCandidate(item, row)).sort((a, b) => b.score - a.score)
  row.status = row.candidates.length ? 'conflict' : 'unmatched'
  row.matchReason = row.candidates.length ? '人工搜索候选' : '人工搜索无结果'
}

async function selectCandidate(row: BomRow, code: string) {
  if (!code) {
    row.selected = null
    row.status = row.candidates.length ? 'conflict' : 'unmatched'
    row.matchReason = '已清空匹配'
    return
  }
  const found = row.candidates.find((candidate) => candidate.code === code)
  if (!found) return
  try {
    const detail = await fetchItem(found.code)
    row.selected = itemToCandidate(detail, found.score, found.reason)
  } catch {
    row.selected = found
  }
  row.status = 'matched'
  row.matchReason = '人工指定'
  currentPlan.value = null
  taskStatus.value = null
  confirmError.value = ''
}

function toggleIncluded(row: BomRow) {
  row.included = !row.included
  row.status = row.included ? (row.selected ? 'matched' : row.candidates.length ? 'conflict' : 'unmatched') : 'excluded'
  currentPlan.value = null
  taskStatus.value = null
  confirmError.value = ''
}

function clearMatch(row: BomRow) {
  row.selected = null
  row.status = row.included ? (row.candidates.length ? 'conflict' : 'unmatched') : 'excluded'
  row.matchReason = '已清空匹配'
  currentPlan.value = null
  taskStatus.value = null
  confirmError.value = ''
}

function excludeUnresolvedRows() {
  unresolvedRows.value.forEach((row) => {
    row.included = false
    row.status = 'excluded'
  })
  currentPlan.value = null
  taskStatus.value = null
  confirmError.value = ''
  message.value = '已取消未匹配物品的出库勾选'
}

function exportRows(format: 'xlsx' | 'csv') {
  const data = rows.value.map(exportRecord)
  if (format === 'xlsx') {
    const sheet = XLSX.utils.json_to_sheet(data)
    const workbook = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(workbook, sheet, 'BOM Export')
    XLSX.writeFile(workbook, exportFileName('xlsx'))
    return
  }
  const csv = XLSX.utils.sheet_to_csv(XLSX.utils.json_to_sheet(data))
  downloadBlob(new Blob(['\uFEFF', csv], { type: 'text/csv;charset=utf-8' }), exportFileName('csv'))
}

function exportRecord(row: BomRow) {
  return {
    ...row.original,
    'Included': row.included ? 'yes' : 'no',
    'Match Status': statusLabel(row),
    'Matched Code': row.selected?.code || '',
    'Matched Name': row.selected?.name || '',
    'Inventory Quantity': row.selected?.quantity ?? '',
    'Unit': row.selected?.unit || '',
    'Location': row.selected?.location_display || '',
    'Outbound Quantity': row.included && row.selected ? row.quantity ?? '' : '',
    'Match Reason': row.matchReason,
  }
}

function exportFileName(ext: string) {
  const stamp = new Date().toISOString().slice(0, 19).replace(/[-:]/g, '').replace('T', '')
  const base = fileName.value.replace(/\.[^.]+$/, '') || 'bom'
  return `${base}-matched-${stamp}.${ext}`
}

function downloadBlob(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = name
  link.click()
  URL.revokeObjectURL(url)
}

async function createPlan() {
  if (!canCreatePlan.value) return
  busy.value = true
  error.value = ''
  currentPlan.value = null
  taskStatus.value = null
  confirming.value = false
  confirmError.value = ''
  try {
    const requestId = `${MODULE_NAME}-plan-${Date.now()}`
    const outboundRows = matchedRows.value.map((row) => ({
      id_or_code: row.selected!.code,
      amount: row.quantity!,
      unit: row.selected!.unit,
      note: `BOM 批量出库：${fileName.value || '未命名文件'} / ${row.comment || row.supplierPart || `row ${row.id}`}`,
    }))
    const response = await createBatchOutboundPlan({ operator: OPERATOR, request_id: requestId, outbound_rows: outboundRows })
    currentPlan.value = response.plan
    message.value = response.plan.failures.length ? '计划包含失败项，请修正后重新创建' : '出库计划已创建，请检查风险后确认'
  } catch (err) {
    error.value = err instanceof Error ? err.message : '创建出库计划失败'
  } finally {
    busy.value = false
  }
}

async function confirmPlan() {
  if (!currentPlan.value || !canConfirmPlan.value) return
  busy.value = true
  confirming.value = true
  error.value = ''
  confirmError.value = ''
  try {
    const requestId = `${MODULE_NAME}-confirm-${currentPlan.value.plan_id}-${Date.now()}`
    const response = await confirmWorkflowPlan(currentPlan.value, OPERATOR, requestId)
    currentPlan.value = response.plan
    taskStatus.value = response.task
    if (response.task?.task_id) {
      const status = await fetchTaskStatus(response.task.task_id)
      taskStatus.value = status.task
    }
    message.value = '批量出库已完成'
  } catch (err) {
    confirmError.value = err instanceof Error ? err.message : '确认出库失败'
    error.value = confirmError.value
  } finally {
    confirming.value = false
    busy.value = false
  }
}

function statusLabel(row: BomRow) {
  if (!row.included) return '已排除'
  if (row.status === 'matched') return '已匹配'
  if (row.status === 'conflict') return '冲突'
  if (row.status === 'unmatched') return '未匹配'
  return '待匹配'
}

function formatPlanFailure(failure: Record<string, unknown>) {
  const row = typeof failure.row === 'number' ? `第 ${failure.row + 1} 项：` : ''
  const code = String(failure.code || '')
  const message = String(failure.message || '出库计划存在问题')
  if (code === 'NEGATIVE_QUANTITY_NOT_ALLOWED') return `${row}库存不足，${message}`
  if (code === 'ITEM_NOT_FOUND') return `${row}${message}`
  if (code === 'ARCHIVED_ITEM_QUANTITY_FORBIDDEN') return `${row}${message}`
  return `${row}${message}`
}
</script>

<template>
  <section class="flex h-full min-h-0 flex-col gap-2 p-3 2xl:p-4">
    <div class="flex min-h-0 flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
      <div>
        <h2 class="text-[22px] font-semibold tracking-tight">BOM 批量出库</h2>
        <p class="text-[13px] text-muted">上传 BOM，匹配库存位置，导出清单或生成批量出库计划。</p>
      </div>
      <label class="inline-flex h-10 cursor-pointer items-center justify-center gap-2 rounded-[8px] bg-green px-4 text-[14px] font-medium text-white shadow-sm hover:bg-green/90">
        <UploadCloud :size="18" />
        上传 BOM
        <input class="hidden" type="file" accept=".xlsx,.xls,.csv,.tsv,.txt" @change="handleFile" />
      </label>
    </div>

    <div class="grid min-h-0 grid-cols-2 overflow-hidden rounded-[8px] border border-line bg-white text-[13px] sm:grid-cols-3 xl:grid-cols-6">
      <span class="flex h-11 items-center justify-center gap-2 border-line px-3 text-muted sm:border-r">
        总行数 <b class="text-[20px] leading-none text-ink">{{ summary.total }}</b>
      </span>
      <span class="flex h-11 items-center justify-center gap-2 border-l border-line px-3 text-muted sm:border-l-0 sm:border-r">
        纳入出库 <b class="text-[20px] leading-none text-ink">{{ summary.included }}</b>
      </span>
      <span class="flex h-11 items-center justify-center gap-2 border-t border-line px-3 text-muted sm:border-t-0 xl:border-r">
        已匹配 <b class="text-[20px] leading-none text-green">{{ summary.matched }}</b>
      </span>
      <span class="flex h-11 items-center justify-center gap-2 border-l border-t border-line px-3 text-muted sm:border-l sm:border-t xl:border-l-0 xl:border-t-0 xl:border-r">
        冲突 <b class="text-[20px] leading-none text-clay">{{ summary.conflict }}</b>
      </span>
      <span class="flex h-11 items-center justify-center gap-2 border-t border-line px-3 text-muted sm:border-r xl:border-t-0">
        未匹配 <b class="text-[20px] leading-none text-amber">{{ summary.unmatched }}</b>
      </span>
      <span class="flex h-11 items-center justify-center gap-2 border-l border-t border-line px-3 text-muted sm:border-l-0 xl:border-t-0">
        已排除 <b class="text-[20px] leading-none text-ink">{{ summary.excluded }}</b>
      </span>
    </div>

    <div v-if="message || error" class="grid min-h-0 gap-2">
      <div v-if="message" class="rounded-[8px] border border-green/20 bg-green/5 px-3 py-2 text-[13px] text-green">{{ message }}</div>
      <div v-if="error" class="rounded-[8px] border border-clay/25 bg-clay/5 px-3 py-2 text-[13px] text-clay">{{ error }}</div>
    </div>

    <div class="flex min-h-0 flex-col gap-2 rounded-[8px] border border-line bg-white p-2 lg:flex-row lg:items-center lg:justify-between">
      <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
        <div class="inline-flex items-center gap-2 text-[14px] text-ink/80">
          <FileSpreadsheet :size="18" class="text-green" />
          <span>{{ fileName || '尚未上传 BOM 文件' }}</span>
        </div>
      </div>
      <div class="flex flex-wrap gap-2">
        <button type="button" class="inline-flex h-10 items-center gap-2 rounded-[8px] border border-line px-3 text-[14px] font-medium text-ink/80 disabled:opacity-50" :disabled="!rows.length || matching" @click="matchAllRows">
          <RefreshCw :size="16" />
          重新匹配
        </button>
        <button type="button" class="inline-flex h-10 items-center gap-2 rounded-[8px] border border-line px-3 text-[14px] font-medium text-ink/80 disabled:opacity-50" :disabled="!hasIncludedUnresolvedRows" @click="excludeUnresolvedRows">
          排除未匹配
        </button>
        <button type="button" class="inline-flex h-10 items-center gap-2 rounded-[8px] border border-line px-3 text-[14px] font-medium text-ink/80 disabled:opacity-50" :disabled="!rows.length" @click="exportRows('xlsx')">
          <FileDown :size="16" />
          导出 XLSX
        </button>
        <button type="button" class="inline-flex h-10 items-center gap-2 rounded-[8px] border border-line px-3 text-[14px] font-medium text-ink/80 disabled:opacity-50" :disabled="!rows.length" @click="exportRows('csv')">
          <Download :size="16" />
          导出 CSV
        </button>
        <button type="button" class="inline-flex h-10 items-center gap-2 rounded-[8px] bg-green px-3 text-[14px] font-medium text-white disabled:opacity-50" :disabled="!canCreatePlan || busy" @click="createPlan">
          <CheckCircle2 :size="16" />
          创建出库计划
        </button>
      </div>
    </div>

    <div v-if="rows.length" class="min-h-[220px] flex-1 overflow-hidden rounded-[8px] border border-line bg-white">
      <div class="thin-scrollbar h-full min-h-0 overflow-auto">
        <table class="min-w-[1180px] border-collapse text-left text-[13px]">
          <thead class="sticky top-0 z-10 bg-slate-50 text-[12px] uppercase text-muted">
            <tr>
              <th class="border-b border-line px-3 py-3">出库</th>
              <th class="border-b border-line px-3 py-3">BOM</th>
              <th class="border-b border-line px-3 py-3">数量</th>
              <th class="border-b border-line px-3 py-3">匹配状态</th>
              <th class="border-b border-line px-3 py-3">库存物品</th>
              <th class="border-b border-line px-3 py-3">位置</th>
              <th class="border-b border-line px-3 py-3">人工指定</th>
              <th class="border-b border-line px-3 py-3">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id" class="border-b border-line/70 align-top last:border-b-0" :class="!row.included ? 'bg-slate-50 text-muted' : ''">
              <td class="px-3 py-3">
                <input type="checkbox" :checked="row.included" class="h-4 w-4 accent-green" @change="toggleIncluded(row)" />
              </td>
              <td class="max-w-[290px] px-3 py-3">
                <div class="font-medium text-ink">{{ row.comment || row.supplierPart || `第 ${row.id} 行` }}</div>
                <div class="mt-1 text-[12px] text-muted">料号：{{ row.supplierPart || '无' }}</div>
                <div class="mt-1 text-[12px] text-muted">封装：{{ row.footprint || '无' }}</div>
              </td>
              <td class="px-3 py-3">
                <span :class="row.quantity ? '' : 'text-clay'">{{ row.quantity || '无效' }}</span>
              </td>
              <td class="px-3 py-3">
                <span class="inline-flex rounded-full px-2 py-1 text-[12px] font-medium" :class="{
                  'bg-green/10 text-green': row.included && row.status === 'matched',
                  'bg-clay/10 text-clay': row.included && row.status === 'conflict',
                  'bg-amber/10 text-amber': row.included && row.status === 'unmatched',
                  'bg-slate-100 text-muted': !row.included || row.status === 'pending',
                }">{{ statusLabel(row) }}</span>
                <div class="mt-2 max-w-[180px] text-[12px] text-muted">{{ row.matchReason }}</div>
              </td>
              <td class="min-w-[230px] px-3 py-3">
                <div v-if="row.selected">
                  <div class="font-medium text-ink">{{ row.selected.code }}</div>
                  <div class="mt-1 text-muted">{{ row.selected.name }}</div>
                  <div class="mt-1 text-[12px] text-muted">库存：{{ row.selected.quantity ?? '未知' }} {{ row.selected.unit || '' }}</div>
                </div>
                <div v-else class="text-muted">未选择</div>
              </td>
              <td class="min-w-[140px] px-3 py-3">{{ row.selected?.location_display || '无' }}</td>
              <td class="min-w-[250px] px-3 py-3">
                <div class="flex gap-2">
                  <input v-model="row.manualQuery" class="h-9 min-w-0 flex-1 rounded-[8px] border border-line px-2 text-[13px] outline-none focus:border-green" placeholder="搜索库存物品" />
                  <button type="button" class="inline-flex h-9 w-9 items-center justify-center rounded-[8px] border border-line" @click="manualSearch(row)">
                    <Search :size="15" />
                  </button>
                </div>
                <select class="mt-2 h-9 w-full rounded-[8px] border border-line px-2 text-[13px] outline-none focus:border-green" :value="row.selected?.code || ''" @change="selectCandidate(row, ($event.target as HTMLSelectElement).value)">
                  <option value="">选择候选</option>
                  <option v-for="candidate in row.candidates" :key="candidate.code" :value="candidate.code">
                    {{ candidate.code }} · {{ candidate.name }} · {{ candidate.score }}
                  </option>
                </select>
              </td>
              <td class="px-3 py-3">
                <button type="button" class="inline-flex h-9 items-center gap-1 rounded-[8px] border border-line px-2 text-[12px] text-ink/70" @click="clearMatch(row)">
                  <Trash2 :size="14" />
                  清除
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div v-else class="grid min-h-0 flex-1 place-items-center rounded-[8px] border border-dashed border-line bg-white/60 text-[14px] text-muted">
      上传 BOM 后会在这里显示可滚动的匹配表
    </div>

    <div v-if="currentPlan" class="shrink-0 rounded-[8px] border border-line bg-white p-3">
      <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div class="min-w-0">
          <h3 class="text-[16px] font-semibold" :class="currentPlan.failures.length ? 'text-clay' : 'text-ink'">
            {{ currentPlan.failures.length ? '无法出库' : outboundDone ? '出库完成' : confirming ? '正在出库' : '出库检查通过' }}
          </h3>
          <p class="mt-1 text-[13px] text-muted">
            {{ currentPlan.failures.length ? `发现 ${currentPlan.failures.length} 个问题，请修正后重新创建计划。` : outboundDone ? `已扣减 ${currentPlan.summary.updates || 0} 项库存。` : confirming ? '正在扣减库存，请稍候。' : `将扣减 ${currentPlan.summary.updates || 0} 项库存。` }}
          </p>
        </div>
        <button v-if="!currentPlan.failures.length && !outboundDone" type="button" class="inline-flex h-10 items-center gap-2 rounded-[8px] bg-green px-4 text-[14px] font-medium text-white disabled:opacity-50" :disabled="!canConfirmPlan || busy" @click="confirmPlan">
          <CheckCircle2 :size="16" />
          {{ confirming ? '正在出库...' : '确认出库' }}
        </button>
        <span v-else-if="outboundDone" class="inline-flex h-10 items-center gap-2 rounded-[8px] border border-green/20 bg-green/5 px-4 text-[14px] font-medium text-green">
          <CheckCircle2 :size="16" />
          已完成
        </span>
      </div>

      <div v-if="confirmError" class="mt-3 rounded-[8px] border border-clay/20 bg-clay/5 px-3 py-2 text-[13px] text-clay">
        {{ confirmError }}
      </div>
      <div v-else-if="outboundDone" class="mt-3 rounded-[8px] border border-green/20 bg-green/5 px-3 py-2 text-[13px] text-green">
        库存已扣减完成。
      </div>
      <div v-else-if="confirming" class="mt-3 rounded-[8px] border border-green/20 bg-green/5 px-3 py-2 text-[13px] text-green">
        正在提交出库，请不要重复点击。
      </div>

      <div v-if="currentPlan.failures.length || currentPlan.risks.length" class="mt-3 grid gap-2">
        <div v-if="currentPlan.failures.length" class="rounded-[8px] border border-clay/20 bg-clay/5 px-3 py-2">
          <h4 class="inline-flex items-center gap-2 text-[14px] font-semibold text-clay"><AlertTriangle :size="16" />原因</h4>
          <ul class="mt-2 grid gap-1 text-[13px] text-ink/75">
            <li v-for="reason in planFailureMessages" :key="reason">{{ reason }}</li>
          </ul>
        </div>
        <div v-if="currentPlan.risks.length" class="rounded-[8px] border border-amber/20 bg-amber/5 px-3 py-2">
          <h4 class="text-[14px] font-semibold text-amber">提示</h4>
          <ul class="mt-2 grid gap-1 text-[13px] text-ink/75">
            <li v-for="risk in currentPlan.risks" :key="risk">{{ risk }}</li>
          </ul>
        </div>
      </div>

      <div v-if="taskStatus && !outboundDone" class="mt-3 rounded-[8px] border border-green/20 bg-green/5 px-3 py-2 text-[13px] text-green">
        出库任务：{{ taskStatus.status }}
      </div>
    </div>
  </section>
</template>
