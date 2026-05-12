import type { LoginResponse, MeResponse, User } from '~/types/api'

export function useAuth() {
  const currentUser = useState<User | null>('current-user', () => null)
  const authLoaded = useState<boolean>('auth-loaded', () => false)
  const { apiFetch } = useApi()

  async function loadMe() {
    try {
      const response = await apiFetch<MeResponse>('/auth/me')
      currentUser.value = response.user
    } catch {
      currentUser.value = null
    } finally {
      authLoaded.value = true
    }
  }

  async function login(username: string, password: string) {
    const response = await apiFetch<LoginResponse>('/auth/login', {
      method: 'POST',
      body: { username, password },
    })
    currentUser.value = response.user
    authLoaded.value = true
    return response.user
  }

  async function logout() {
    await apiFetch('/auth/logout', { method: 'POST' })
    currentUser.value = null
    authLoaded.value = true
    await navigateTo('/login')
  }

  return {
    currentUser,
    authLoaded,
    loadMe,
    login,
    logout,
  }
}
