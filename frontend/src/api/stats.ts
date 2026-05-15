import { requestData } from '@/api/client'
import type { StatsOverview } from '@/types'

export function fetchStatsOverview() {
  return requestData<StatsOverview>('/api/stats/overview')
}
