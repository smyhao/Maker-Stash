import axios from 'axios'

import type { ApiEnvelope } from '@/types'

const API_BASE_URL_KEY = 'maker-stash-api-url'
const API_TOKEN_KEY = 'maker-stash-api-token'

export const api = axios.create({
  baseURL: localStorage.getItem(API_BASE_URL_KEY) || '',
  timeout: 12000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(API_TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export function getApiConfig() {
  return {
    apiUrl: localStorage.getItem(API_BASE_URL_KEY) || '',
    token: localStorage.getItem(API_TOKEN_KEY) || '',
  }
}

export function setApiConfig(apiUrl: string, token: string) {
  localStorage.setItem(API_BASE_URL_KEY, apiUrl)
  localStorage.setItem(API_TOKEN_KEY, token)
  api.defaults.baseURL = apiUrl
}

function apiError(error: unknown): Error {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as ApiEnvelope<unknown> | undefined
    return new Error(data?.error?.message || error.message || '请求失败')
  }
  return error instanceof Error ? error : new Error('请求失败')
}

export async function requestData<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  try {
    const response = await api.get<ApiEnvelope<T>>(url, { params })
    const envelope = response.data
    if (!envelope.success) {
      throw new Error(envelope.error?.message || '请求失败')
    }
    return envelope.data
  } catch (error) {
    throw apiError(error)
  }
}

export async function postData<T>(url: string, payload?: object): Promise<T> {
  try {
    const response = await api.post<ApiEnvelope<T>>(url, payload)
    const envelope = response.data
    if (!envelope.success) {
      throw new Error(envelope.error?.message || '请求失败')
    }
    return envelope.data
  } catch (error) {
    throw apiError(error)
  }
}

export async function patchData<T>(url: string, payload?: object): Promise<T> {
  try {
    const response = await api.patch<ApiEnvelope<T>>(url, payload)
    const envelope = response.data
    if (!envelope.success) {
      throw new Error(envelope.error?.message || '请求失败')
    }
    return envelope.data
  } catch (error) {
    throw apiError(error)
  }
}

export async function deleteData<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  try {
    const response = await api.delete<ApiEnvelope<T>>(url, { params })
    const envelope = response.data
    if (!envelope.success) {
      throw new Error(envelope.error?.message || '请求失败')
    }
    return envelope.data
  } catch (error) {
    throw apiError(error)
  }
}

export async function uploadData<T>(url: string, formData: FormData): Promise<T> {
  try {
    const response = await api.post<ApiEnvelope<T>>(url, formData)
    const envelope = response.data
    if (!envelope.success) {
      throw new Error(envelope.error?.message || '请求失败')
    }
    return envelope.data
  } catch (error) {
    throw apiError(error)
  }
}
