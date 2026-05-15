import { api, postData, requestData } from '@/api/client'
import type { Backup } from '@/types'

export function fetchBackups() {
  return requestData<{ backups: Backup[] }>('/api/backups')
}

export function createBackup(payload: { include_uploads: boolean; note?: string | null }) {
  return postData<Backup>('/api/backups', payload)
}

export function restoreBackup(backupId: string) {
  return postData<Backup>(`/api/backups/${backupId}/restore`)
}

export async function downloadBackupFile(backupId: string) {
  const response = await api.get(`/api/backups/${backupId}/download`, { responseType: 'blob' })
  return response.data as Blob
}
