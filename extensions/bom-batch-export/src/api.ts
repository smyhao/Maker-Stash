interface ApiEnvelope<T> {
  success: boolean
  data: T
  message?: string
  error?: {
    code: string
    message: string
  }
}

export interface Item {
  id: number
  code: string
  name: string
  category_id: number | null
  location_id: number | null
  location_text: string | null
  location_display?: string | null
  quantity: string | number | null
  unit: string | null
  status: string
  description: string | null
  need_restock: boolean
  is_favorite: boolean
  cover_attachment_id: number | null
  is_archived: boolean
}

export interface CapabilitiesResponse {
  app: string
  version: string
  api_version: string
  features: Record<string, boolean>
  limits: {
    max_upload_bytes: number
    page_size_max: number
  }
  extension_contract: {
    preferred_interface: string
    write_idempotency_required: boolean
    workflow_required_for_bulk_or_agent_writes: boolean
  }
}

export interface SearchItem {
  id: number
  code: string
  name: string
  category_id: number | null
  category_name?: string | null
  location_id: number | null
  location_full_code?: string | null
  quantity: string | null
  unit: string | null
  status: string
  need_restock: boolean
  is_favorite: boolean
  matched_by: string[]
}

export interface WorkflowPlan {
  plan_id: string
  workflow_type: string
  status: string
  summary: Record<string, number>
  creates: Array<Record<string, unknown>>
  updates: Array<Record<string, unknown>>
  skips: Array<Record<string, unknown>>
  failures: Array<Record<string, unknown>>
  risks: string[]
  confirm_token: string
  task_id: string | null
  source: string
  module: string | null
  operator: string | null
  request_id: string | null
  created_at: string
  confirmed_at: string | null
}

export interface TaskStatus {
  task_id: string
  job_type: string
  status: string
  input_summary?: string | null
  result_summary?: string | null
  error_message?: string | null
  error?: {
    code: string
    message: string
  }
}

export interface BatchOutboundRow {
  id_or_code: string
  amount: number
  unit?: string | null
  note?: string | null
}

const API_BASE_URL_KEY = 'maker-stash-api-url'
const API_TOKEN_KEY = 'maker-stash-api-token'

function apiUrl(path: string) {
  const baseUrl = localStorage.getItem(API_BASE_URL_KEY) || ''
  return `${baseUrl}${path}`
}

async function requestData<T>(path: string, params?: Record<string, unknown>): Promise<T> {
  const url = new URL(apiUrl(path), window.location.origin)
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      url.searchParams.set(key, String(value))
    }
  })
  return requestEnvelope<T>(url.toString())
}

async function postData<T>(path: string, payload: object): Promise<T> {
  return requestEnvelope<T>(apiUrl(path), {
    method: 'POST',
    body: JSON.stringify(payload),
    headers: {
      'Content-Type': 'application/json',
    },
  })
}

async function requestEnvelope<T>(url: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  headers.set('X-Maker-Stash-Client', 'web')
  const token = localStorage.getItem(API_TOKEN_KEY)
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  const response = await fetch(url, { ...init, headers })
  const envelope = await response.json() as ApiEnvelope<T>
  if (!response.ok || !envelope.success) {
    throw new Error(envelope.error?.message || envelope.message || '请求失败')
  }
  return envelope.data
}

export function fetchCapabilities() {
  return requestData<CapabilitiesResponse>('/api/system/capabilities')
}

export function fetchItemsByTag(tag: string) {
  return requestData<{ items: Item[]; total: number; page: number; page_size: number }>('/api/items', {
    tag,
    page: 1,
    page_size: 100,
  })
}

export function searchItems(q: string, limit = 20) {
  return requestData<{ items: SearchItem[] }>('/api/search', { q, limit })
}

export function fetchItem(code: string) {
  return requestData<Item>(`/api/items/${code}`)
}

export function createBatchOutboundPlan(payload: {
  operator: string
  request_id: string
  outbound_rows: BatchOutboundRow[]
}) {
  return postData<{ plan: WorkflowPlan }>('/api/workflows/plans', {
    workflow_type: 'batch_outbound',
    source: 'extension',
    module: 'bom-batch-export',
    operator: payload.operator,
    request_id: payload.request_id,
    outbound_rows: payload.outbound_rows,
  })
}

export function confirmWorkflowPlan(plan: WorkflowPlan, operator: string, requestId: string) {
  return postData<{ plan: WorkflowPlan; task: TaskStatus | null; result: Record<string, unknown> | null }>(
    `/api/workflows/plans/${plan.plan_id}/confirm`,
    {
      confirm_token: plan.confirm_token,
      source: 'extension',
      module: 'bom-batch-export',
      operator,
      request_id: requestId,
    },
  )
}

export function fetchTaskStatus(taskId: string) {
  return requestData<{ task: TaskStatus }>(`/api/tasks/${taskId}/status`)
}
