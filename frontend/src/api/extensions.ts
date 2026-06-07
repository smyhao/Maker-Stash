import { patchData, postData, requestData } from '@/api/client'
import type { ExtensionContribution, ExtensionManifest, ExtensionSettingField } from '@/types'

export const EXTENSIONS_CHANGED_EVENT = 'maker-stash:extensions-changed'

export interface ExtensionListResponse {
  extensions: ExtensionManifest[]
}

export interface ExtensionSettingsResponse {
  extension_id: string
  schema: Record<string, ExtensionSettingField>
  values: Record<string, unknown>
  configured: boolean
}

export interface ExtensionContributionsResponse {
  contributions: ExtensionContribution[]
}

export function fetchExtensions() {
  return requestData<ExtensionListResponse>('/api/extensions')
}

export function setExtensionEnabled(extensionId: string, enabled: boolean) {
  return patchData<ExtensionManifest>(`/api/extensions/${extensionId}`, { enabled })
}

export function notifyExtensionsChanged() {
  window.dispatchEvent(new CustomEvent(EXTENSIONS_CHANGED_EVENT))
}

export function fetchExtensionSettings(extensionId: string) {
  return requestData<ExtensionSettingsResponse>(`/api/extensions/${extensionId}/settings`)
}

export function updateExtensionSettings(extensionId: string, values: Record<string, unknown>) {
  return patchData<ExtensionSettingsResponse>(`/api/extensions/${extensionId}/settings`, { values })
}

export function fetchExtensionContributions(place: string) {
  return requestData<ExtensionContributionsResponse>('/api/extensions/contributions', { place })
}

export function runExtensionAction(extensionId: string, action: string, context: Record<string, unknown>) {
  return postData<Record<string, unknown>>(`/api/extensions/${extensionId}/actions/${action}`, {
    context,
    request_id: `${extensionId}-${action}-${Date.now()}`,
    source: 'web',
    module: extensionId,
    operator: 'web-ui',
  })
}
