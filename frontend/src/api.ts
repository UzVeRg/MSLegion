interface SessionResponse {
  access_token: string
  expires_at: string
}

export interface Profile {
  id: string
  telegram_id: number | null
  display_name: string
  telegram_notifications_enabled: boolean
}

export class ApiError extends Error {
  constructor(readonly status: number) {
    super(`Ошибка API (HTTP ${status})`)
  }
}

async function request(path: string, options: RequestInit): Promise<Response> {
  const response = await fetch(`/api/v1/auth${path}`, {
    ...options,
    credentials: 'omit',
    redirect: 'error',
  })
  if (!response.ok) throw new ApiError(response.status)
  return response
}

export async function exchangeTelegramData(initData: string, signal: AbortSignal): Promise<SessionResponse> {
  const response = await request('/telegram', {
    method: 'POST',
    body: JSON.stringify({ init_data: initData }),
    headers: { 'Content-Type': 'application/json' },
    signal,
  })
  return response.json()
}

export async function fetchProfile(token: string, signal: AbortSignal): Promise<Profile> {
  const response = await request('/me', {
    headers: { Authorization: `Bearer ${token}` },
    signal,
  })
  return response.json()
}

export async function revokeSession(token: string, signal: AbortSignal): Promise<void> {
  await request('/logout', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    signal,
  })
}

export async function setTelegramNotifications(
  token: string, enabled: boolean, signal: AbortSignal,
): Promise<{ enabled: boolean }> {
  const response = await request('/me/telegram-notifications', {
    method: 'PUT',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled }),
    signal,
  })
  return response.json()
}
