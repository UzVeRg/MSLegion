import type { Language } from './locale'

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

export interface SupportContent {
  questions: { question: string; answer: string }[]
  contacts: { channel: 'telegram' | 'discord' | 'email'; label: string; url: string }[]
}

export async function getSupport(language: Language, signal: AbortSignal): Promise<SupportContent> {
  const response = await request(`/support?language=${language}`, { signal })
  return response.json()
}

async function request(path: string, options: RequestInit): Promise<Response> {
  const response = await fetch(`/api/v1${path}`, {
    ...options,
    credentials: 'omit',
    redirect: 'error',
  })
  if (!response.ok) throw new ApiError(response.status)
  return response
}

export async function exchangeTelegramData(initData: string, signal: AbortSignal): Promise<SessionResponse> {
  const response = await request('/auth/telegram', {
    method: 'POST',
    body: JSON.stringify({ init_data: initData }),
    headers: { 'Content-Type': 'application/json' },
    signal,
  })
  return response.json()
}

export async function fetchProfile(token: string, signal: AbortSignal): Promise<Profile> {
  const response = await request('/auth/me', {
    headers: { Authorization: `Bearer ${token}` },
    signal,
  })
  return response.json()
}

export async function revokeSession(token: string, signal: AbortSignal): Promise<void> {
  await request('/auth/logout', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    signal,
  })
}

export async function setTelegramNotifications(
  token: string, enabled: boolean, signal: AbortSignal,
): Promise<{ enabled: boolean }> {
  const response = await request('/auth/me/telegram-notifications', {
    method: 'PUT',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled }),
    signal,
  })
  return response.json()
}

export interface Wallet {
  balance: string
  date: string
  streak: number
  day: number
  claimed_today: boolean
  rewards: { day: number; amount: number }[]
  seconds_until_reset: number
}

export async function getWallet(token: string, signal: AbortSignal): Promise<Wallet> {
  const response = await request('/finance/wallet', {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store',
    signal,
  })
  return response.json()
}

export async function claimDailyReward(token: string, date: string, signal: AbortSignal): Promise<Wallet> {
  const response = await request('/finance/wallet/check-in', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ date }),
    signal,
  })
  return response.json()
}

export interface Community {
  id: string
  name: string
  owner_id: string
}

export async function fetchCommunities(
  token: string, offset: number, limit: number, signal: AbortSignal,
): Promise<Community[]> {
  const response = await request(`/communities?offset=${offset}&limit=${limit}`, {
    headers: { Authorization: `Bearer ${token}` },
    signal,
  })
  return response.json()
}

export type MafiaMode = 'classic' | 'custom'
export type MafiaPhase = 'lobby' | 'night' | 'day' | 'vote' | 'finished'
export type MafiaRole = 'citizen' | 'mafia' | 'doctor' | 'detective'

export interface MafiaSettings {
  mode: MafiaMode
  doctor: boolean
  detective: boolean
  night_seconds: number
  day_seconds: number
  vote_seconds: number
}

export interface MafiaSummary {
  code: string
  mode: MafiaMode
  phase: MafiaPhase
  player_count: number
}

export interface MafiaRoom {
  code: string
  settings: MafiaSettings
  host_id: string
  phase: MafiaPhase
  round: number
  turn: number
  deadline: string | null
  server_time: string
  winner: 'mafia' | 'town' | 'draw' | null
  players: { id: string; name: string; alive: boolean; role: MafiaRole | null }[]
  role: MafiaRole | null
  allies: string[]
  eligible_targets: string[]
  can_target: boolean
  target_locked: boolean
  target_id: string | null
  vote_count: number | null
  history: { round: number; phase: 'night' | 'vote'; player_id: string | null }[]
  investigations: { round: number; player_id: string; mafia: boolean }[]
  messages: { id: string; name: string; text: string }[]
  chat: 'public' | 'mafia' | null
  can_chat: boolean
}

export type MafiaAction =
  | { type: 'join' | 'start' | 'leave' }
  | { type: 'open_vote'; turn: number }
  | { type: 'target'; turn: number; target_id: string | null }
  | { type: 'chat'; turn: number; text: string }

const mafiaRoomPath = '/mafia/rooms'

async function mafiaRequest<T>(
  path: string, token: string, signal: AbortSignal, body?: object,
): Promise<T> {
  const headers: Record<string, string> = { Authorization: `Bearer ${token}` }
  if (body) headers['Content-Type'] = 'application/json'
  const response = await request(mafiaRoomPath + path, {
    headers, signal, cache: 'no-store',
    method: body ? 'POST' : 'GET', body: body ? JSON.stringify(body) : undefined,
  })
  return response.json()
}

export function fetchMafiaRooms(token: string, signal: AbortSignal): Promise<MafiaSummary[]> {
  return mafiaRequest('', token, signal)
}

export function createMafiaRoom(
  token: string, settings: MafiaSettings | { mode: 'classic' }, signal: AbortSignal,
): Promise<MafiaRoom> {
  return mafiaRequest('', token, signal, settings)
}

export function fetchMafiaRoom(
  token: string, code: string, signal: AbortSignal,
): Promise<MafiaRoom> {
  return mafiaRequest(`/${encodeURIComponent(code)}`, token, signal)
}

export function playMafiaAction(
  token: string, code: string, action: MafiaAction, signal: AbortSignal,
): Promise<MafiaRoom | null> {
  return mafiaRequest(`/${encodeURIComponent(code)}/actions`, token, signal, action)
}
