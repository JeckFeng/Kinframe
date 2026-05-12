import type { ApiErrorBody } from '~/types/api'

export function getApiErrorMessage(error: unknown): string {
  if (typeof error === 'object' && error !== null && 'data' in error) {
    const body = (error as { data?: ApiErrorBody }).data
    if (typeof body?.detail === 'string') {
      return body.detail
    }
  }
  if (error instanceof Error && error.message) {
    return error.message
  }
  return 'Request failed'
}

export function useApi() {
  const config = useRuntimeConfig()

  async function apiFetch<T>(path: string, options: Parameters<typeof $fetch<T>>[1] = {}) {
    const requestHeaders = import.meta.server ? useRequestHeaders(['cookie']) : undefined
    const optionHeaders = (options.headers || {}) as Record<string, string>
    try {
      return await $fetch<T>(path, {
        baseURL: config.public.apiBase,
        credentials: 'include',
        ...options,
        headers: {
          ...(requestHeaders || {}),
          ...optionHeaders,
        },
      })
    } catch (error: unknown) {
      const statusCode = typeof error === 'object' && error !== null && 'statusCode' in error
        ? Number((error as { statusCode?: number }).statusCode)
        : undefined
      if (statusCode === 401 && import.meta.client && useRoute().path !== '/login') {
        await navigateTo('/login')
      }
      throw error
    }
  }

  return {
    apiFetch,
  }
}
