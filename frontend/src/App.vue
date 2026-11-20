<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import {
  ApiError, exchangeTelegramData, fetchProfile, revokeSession, setTelegramNotifications, type Profile,
} from './api'
import { getTelegramWebApp, requestTelegramWriteAccess } from './telegram'

type Phase = 'outside' | 'loading' | 'profile' | 'expired' | 'reopen' | 'error' | 'signed-out'

const phase = ref<Phase>('outside')
const profile = ref<Profile | null>(null)
const errorMessage = ref('')
const signingOut = ref(false)
const savingNotifications = ref(false)
const abort = new AbortController()
let session: { token: string; expiresAt: number } | null = null
let expiryTimer: ReturnType<typeof setTimeout> | undefined
let loginAttempt = 0

const statusText = computed(() => ({
  outside: 'Откройте MSLegion в Telegram',
  loading: 'Входим через Telegram…',
  profile: '',
  expired: 'Сессия завершилась',
  reopen: 'Откройте приложение заново в Telegram',
  error: errorMessage.value,
  'signed-out': 'Вы вышли из профиля',
})[phase.value])

const initials = computed(() =>
  profile.value?.display_name.trim().split(/\s+/).slice(0, 2)
    .map((word) => Array.from(word)[0]).join('').toLocaleUpperCase('ru'),
)
const retryLabel = computed(() => phase.value === 'error' ? 'Повторить' : 'Войти через Telegram')

function clearSession() {
  clearTimeout(expiryTimer)
  session = null
  profile.value = null
  signingOut.value = false
  savingNotifications.value = false
}

function expireSession() {
  clearSession()
  phase.value = 'expired'
}

async function signIn() {
  if (phase.value === 'loading') return
  const initData = getTelegramWebApp()?.initData
  if (!initData) {
    phase.value = 'outside'
    return
  }

  phase.value = 'loading'
  const attempt = ++loginAttempt
  errorMessage.value = ''
  try {
    if (!session || session.expiresAt <= Date.now()) {
      clearSession()
      const response = await exchangeTelegramData(initData, abort.signal)
      if (abort.signal.aborted) return
      const expiresAt = Date.parse(response.expires_at)
      if (!response.access_token || !Number.isFinite(expiresAt) || expiresAt <= Date.now()) {
        throw new Error('Сервер вернул недействительную сессию')
      }
      session = { token: response.access_token, expiresAt }
      expiryTimer = setTimeout(expireSession, expiresAt - Date.now())
    }

    const current = session
    const result = await fetchProfile(current.token, abort.signal)
    if (abort.signal.aborted || session !== current) return
    if (current.expiresAt <= Date.now()) {
      expireSession()
      return
    }
    profile.value = result
    phase.value = 'profile'
  } catch (error) {
    if (abort.signal.aborted || attempt !== loginAttempt || phase.value !== 'loading') return
    if (error instanceof ApiError && error.status === 401) {
      if (session) expireSession()
      else phase.value = 'reopen'
      return
    }
    errorMessage.value = error instanceof ApiError && error.status === 403
      ? 'Вход недоступен. Обратитесь к администратору.'
      : 'Не удалось загрузить профиль. Попробуйте ещё раз.'
    phase.value = 'error'
  }
}

async function signOut() {
  if (!session || signingOut.value) return
  const current = session
  signingOut.value = true
  errorMessage.value = ''
  try {
    await revokeSession(current.token, abort.signal)
  } catch (error) {
    if (abort.signal.aborted || session !== current) return
    if (!(error instanceof ApiError && error.status === 401)) {
      errorMessage.value = 'Не удалось завершить сессию. Попробуйте ещё раз.'
      return
    }
  } finally {
    if (session === current) signingOut.value = false
  }
  if (abort.signal.aborted || session !== current) return
  clearSession()
  phase.value = 'signed-out'
}

async function toggleNotifications() {
  if (!session || !profile.value || savingNotifications.value) return
  const current = session
  const enabled = !profile.value.telegram_notifications_enabled
  savingNotifications.value = true
  errorMessage.value = ''
  try {
    if (enabled && !await requestTelegramWriteAccess()) {
      if (session === current) errorMessage.value = 'Разрешите боту отправлять личные сообщения.'
      return
    }
    if (session !== current || abort.signal.aborted) return
    const saved = await setTelegramNotifications(current.token, enabled, abort.signal)
    if (session === current && profile.value) {
      profile.value.telegram_notifications_enabled = saved.enabled
    }
  } catch (error) {
    if (session !== current || abort.signal.aborted) return
    if (error instanceof ApiError && error.status === 401) expireSession()
    else errorMessage.value = 'Не удалось сохранить настройку уведомлений.'
  } finally {
    if (session === current) savingNotifications.value = false
  }
}

onMounted(() => {
  const telegram = getTelegramWebApp()
  telegram?.ready()
  if (telegram?.initData) void signIn()
})

onUnmounted(() => {
  abort.abort()
  clearSession()
})
</script>

<template>
  <main class="shell">
    <header class="brand">
      <span class="brand-mark" aria-hidden="true">M</span>
      <span>MSLegion</span>
    </header>

    <section v-if="phase === 'profile' && profile" class="panel" aria-labelledby="profile-title">
      <h1 id="profile-title" class="section-label">Ваш профиль</h1>
      <div class="identity">
        <span class="avatar" aria-hidden="true">{{ initials }}</span>
        <div class="identity-text">
          <p class="name">{{ profile.display_name }}</p>
          <p v-if="profile.telegram_id !== null" class="muted">Telegram ID {{ profile.telegram_id }}</p>
        </div>
      </div>
      <div class="actions">
        <p v-if="errorMessage" class="muted" role="alert">{{ errorMessage }}</p>
        <button type="button" class="secondary" :disabled="signingOut" @click="signOut">
          {{ signingOut ? 'Выходим…' : 'Выйти' }}
        </button>
        <button
          type="button"
          class="secondary"
          data-notification-toggle
          :disabled="signingOut || savingNotifications"
          @click="toggleNotifications"
        >
          {{ profile.telegram_notifications_enabled ? 'Отключить уведомления' : 'Включить уведомления' }}
        </button>
        <p class="muted">Бот сообщает, когда сервер вашего сообщества становится доступен или недоступен.</p>
      </div>
    </section>

    <section v-else class="panel" :aria-busy="phase === 'loading'">
      <div class="status" role="status">
        <span v-if="phase === 'loading'" class="spinner" aria-hidden="true"></span>
        <h1>{{ statusText }}</h1>
        <p v-if="phase === 'outside'" class="muted">Запустите Mini App из чата с ботом, чтобы увидеть свой профиль.</p>
        <p v-else-if="phase === 'reopen'" class="muted">Данные входа устарели или не прошли проверку.</p>
      </div>
      <button
        v-if="phase === 'expired' || phase === 'error' || phase === 'signed-out'"
        type="button"
        class="primary"
        @click="signIn"
      >
        {{ retryLabel }}
      </button>
    </section>
  </main>
</template>
