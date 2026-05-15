import { api, deleteData, patchData, postData, requestData, uploadData } from '@/api/client'
import type { Attachment, Item, ItemAttribute, ItemFormPayload, Note, Tag } from '@/types'

export interface ItemListResponse {
  items: Item[]
  total: number
  page: number
  page_size: number
}

export function fetchItems(params?: Record<string, unknown>) {
  return requestData<ItemListResponse>('/api/items', params)
}

export function fetchItem(code: string) {
  return requestData<Item>(`/api/items/${code}`)
}

export function fetchItemAttributes(code: string) {
  return requestData<{ attributes: ItemAttribute[] }>(`/api/items/${code}/attributes`)
}

export function fetchItemTags(code: string) {
  return requestData<{ tags: Tag[] }>(`/api/items/${code}/tags`)
}

export function addItemTags(code: string, tags: string[]) {
  return postData<{ tags: Tag[] }>(`/api/items/${code}/tags`, { tags })
}

export function removeItemTag(code: string, tag: string) {
  return deleteData<{ deleted: boolean }>(`/api/items/${code}/tags/${encodeURIComponent(tag)}`)
}

export function fetchItemNotes(code: string) {
  return requestData<{ notes: Note[] }>(`/api/items/${code}/notes`)
}

export function fetchItemAttachments(code: string) {
  return requestData<{ attachments: Attachment[] }>(`/api/items/${code}/attachments`)
}

export function createItemAttribute(code: string, payload: {
  name: string
  key: string
  value?: string | null
  value_type?: string | null
  unit?: string | null
}) {
  return postData<ItemAttribute>(`/api/items/${code}/attributes`, payload)
}

export function updateItemAttribute(id: number, payload: {
  name?: string
  value?: string | null
  value_type?: string | null
  unit?: string | null
}) {
  return patchData<ItemAttribute>(`/api/item-attributes/${id}`, payload)
}

export function deleteItemAttribute(id: number) {
  return deleteData<{ deleted: boolean }>(`/api/item-attributes/${id}`)
}

export function createItem(payload: ItemFormPayload) {
  return postData<Item>('/api/items', payload)
}

export function updateItem(code: string, payload: ItemFormPayload) {
  return patchData<Item>(`/api/items/${code}`, payload)
}

export function deleteItem(code: string, deleteAttachments: boolean) {
  return deleteData<{ archived: boolean; attachments_deleted: boolean }>(`/api/items/${code}`, {
    delete_attachments: deleteAttachments,
  })
}

export function toggleFavorite(code: string, favorite: boolean) {
  return postData<Item>(`/api/items/${code}/${favorite ? 'favorite' : 'unfavorite'}`)
}

export function toggleRestock(code: string, needRestock: boolean) {
  return postData<Item>(`/api/items/${code}/${needRestock ? 'mark-restock' : 'unmark-restock'}`)
}

export function uploadItemAttachment(code: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return uploadData<Attachment>(`/api/items/${code}/attachments`, formData)
}

export function uploadItemImage(code: string, file: File, isCover = true) {
  const formData = new FormData()
  formData.append('file', file)
  return uploadData<Attachment>(`/api/items/${code}/images?is_cover=${isCover}`, formData)
}

export function deleteAttachment(id: number) {
  return deleteData<{ deleted: boolean }>(`/api/attachments/${id}`)
}

export async function downloadAttachmentFile(id: number) {
  const response = await api.get(`/api/attachments/${id}/download`, { responseType: 'blob' })
  return response.data as Blob
}

export function addItemQuantity(code: string, amount: number, unit?: string, note?: string) {
  return postData<Item>(`/api/items/${code}/add`, {
    amount,
    unit,
    note,
    source: 'web',
  })
}

export function useItem(code: string, amount: number, unit?: string, note?: string) {
  return postData<Item>(`/api/items/${code}/use`, {
    amount,
    unit,
    note,
    source: 'web',
  })
}

export function adjustItem(code: string, quantity: number, unit?: string, note?: string) {
  return postData<Item>(`/api/items/${code}/adjust`, {
    quantity,
    unit,
    note,
    source: 'web',
  })
}

export function moveItem(code: string, locationCode?: string | null, locationText?: string | null, note?: string) {
  return postData<Item>(`/api/items/${code}/move`, {
    location_code: locationCode || null,
    location_text: locationText || null,
    note,
    source: 'web',
  })
}
