import { deleteData, patchData, postData, requestData } from '@/api/client'

export interface ApiTokenRead {
  id: number
  name: string
  enabled: boolean
  description: string | null
  last_used_at: string | null
  created_at: string
  updated_at: string
  is_current: boolean
}

export interface ApiTokenCreated extends ApiTokenRead {
  token: string
}

export function fetchTokens(currentToken?: string) {
  const params = currentToken ? `?current_token=${encodeURIComponent(currentToken)}` : ''
  return requestData<{ tokens: ApiTokenRead[] }>(`/api/tokens${params}`)
}

export function createToken(payload: { name: string; description?: string | null }) {
  return postData<ApiTokenCreated>('/api/tokens', payload)
}

export function updateToken(id: number, payload: { name?: string; enabled?: boolean; description?: string | null }) {
  return patchData<ApiTokenRead>(`/api/tokens/${id}`, payload)
}

export function deleteToken(id: number) {
  return deleteData<{ deleted: boolean }>(`/api/tokens/${id}`)
}
