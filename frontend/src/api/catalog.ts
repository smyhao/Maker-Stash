import { deleteData, patchData, postData, requestData } from '@/api/client'
import type { Category, ContainerBoard, ContainerCreatePayload, ContainerLayoutPayload, Item, LocationNode, SlotAssignment } from '@/types'

export function fetchCategories() {
  return requestData<{ categories: Category[] }>('/api/categories/tree')
}

export function createCategory(payload: {
  name: string
  slug: string
  code_prefix: string
  parent_id?: number | null
  sort_order?: number
  description?: string | null
}) {
  return postData<Category>('/api/categories', payload)
}

export function updateCategory(id: number, payload: {
  name?: string
  parent_id?: number | null
  sort_order?: number
  description?: string | null
}) {
  return patchData<Category>(`/api/categories/${id}`, payload)
}

export function deleteCategory(id: number) {
  return deleteData<{ deleted: boolean }>(`/api/categories/${id}`)
}

export function fetchLocations() {
  return requestData<{ locations: LocationNode[] }>('/api/locations/tree')
}

export function fetchLocationItems(id: number) {
  return requestData<{ items: Item[] }>(`/api/locations/${id}/items`)
}

export function createLocation(payload: {
  name: string
  code: string
  parent_code?: string | null
  type?: string | null
  description?: string | null
  sort_order?: number
}) {
  return postData<LocationNode>('/api/locations', payload)
}

export function updateLocation(id: number, payload: {
  name?: string
  type?: string | null
  description?: string | null
  sort_order?: number
}) {
  return patchData<LocationNode>(`/api/locations/${id}`, payload)
}

export function deleteLocation(id: number) {
  return deleteData<{ deleted: boolean }>(`/api/locations/${id}`)
}

export function createContainer(payload: ContainerCreatePayload) {
  return postData<LocationNode>('/api/locations/containers', payload)
}

export function convertLocationToContainer(id: number, payload: ContainerLayoutPayload & { assignments: SlotAssignment[] }) {
  return postData<LocationNode>(`/api/locations/${id}/container`, payload)
}

export function updateContainer(id: number, payload: ContainerLayoutPayload) {
  return patchData<LocationNode>(`/api/locations/${id}/container`, payload)
}

export function fetchContainerBoard(id: number) {
  return requestData<ContainerBoard>(`/api/locations/${id}/board`)
}

export function swapContainerSlots(id: number, sourceItemCode: string, targetSlotKey: string) {
  return postData<{ items: unknown[] }>(`/api/locations/${id}/swap`, {
    source_item_code: sourceItemCode,
    target_slot_key: targetSlotKey,
    source: 'web',
    module: 'locations',
  })
}
