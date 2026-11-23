<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  ApiError, exchangeTelegramData, fetchProfile, revokeSession, setTelegramNotifications, type Profile,
} from './api'
import AppIcon from './AppIcon.vue'
import CommunityList from './CommunityList.vue'
import MafiaGame from './MafiaGame.vue'
import NavRow from './NavRow.vue'
import { messages, sections, type Language, type Message, type Section } from './locale'
import { getTelegramWebApp, requestTelegramWriteAccess, syncTelegramColors } from './telegram'

type Phase = 'outside' | 'loading' | 'profile' | 'expired' | 'reopen' | 'error' | 'signed-out'

const themes = ['graphite', 'neo-gothic', 'network', 'underground'] as const
const languages = ['ru', 'en'] as const
const themeKey = 'mslegion.theme'
const languageKey = 'mslegion.language'
const theme = ref(loadPreference(themeKey, themes))
const language = ref<Language>(loadPreference(languageKey, languages))
const copy = computed(() => messages[language.value])
document.documentElement.dataset.theme = theme.value
document.documentElement.lang = language.value

watch(theme, (value) => {
  document.documentElement.dataset.theme = value
  savePreference(themeKey, value)
  syncTelegramColors()
})
watch(language, (value) => {
  document.documentElement.lang = value
  savePreference(languageKey, value)
})

function loadPreference<T extends string>(key: string, options: readonly [T, ...T[]]): T {
  try {
    const stored = localStorage.getItem(key)
    return options.find((option) => option === stored) ?? options[0]
  } catch {
    return options[0]
  }
}

function savePreference(key: string, value: string) {
  try {
    localStorage.setItem(key, value)
  } catch {
    // При недоступном хранилище выбор действует до закрытия приложения.
  }
}

const discover = ['games', 'events', 'media', 'communities'] as const
const personal = ['notifications', 'settings'] as const
const shortcuts = ['games', 'media', 'communities'] as const
const emptyMessages = { events: 'eventsEmpty', media: 'mediaEmpty' } as const
const page = ref<Section | 'search'>('home')
const menuOpen = ref(false)
const query = ref('')
const menuTrigger = ref<HTMLButtonElement>()
const menuPanel = ref<HTMLElement>()
const searchField = ref<HTMLInputElement>()
const pageHeading = ref<HTMLElement>()
let returnPage: Section = 'home'

const matches = computed(() => {
  const term = query.value.trim().toLocaleLowerCase(language.value)
  return sections.filter((section) => copy.value[section].toLocaleLowerCase(language.value).includes(term))
})

watch(menuOpen, (open) => {
  if (open) menuPanel.value?.focus()
}, { flush: 'post' })

function open(section: Section) {
  menuOpen.value = false
  page.value = section
  if (phase.value !== 'error') errorMessage.value = ''
  void nextTick(() => pageHeading.value?.focus())
}

function closeMenu() {
  menuOpen.value = false
  void nextTick(() => menuTrigger.value?.focus())
}

function toggleSearch() {
  if (page.value === 'search') {
    open(returnPage)
    return
  }
  returnPage = page.value
  page.value = 'search'
  query.value = ''
  void nextTick(() => searchField.value?.focus())
}

function escape() {
  if (menuOpen.value) closeMenu()
  else if (page.value === 'search') toggleSearch()
}

const phase = ref<Phase>('outside')
const profile = ref<Profile | null>(null)
const errorMessage = ref<Message | ''>('')
const signingOut = ref(false)
const savingNotifications = ref(false)
const abort = new AbortController()
const session = ref<{ token: string; expiresAt: number } | null>(null)
let expiryTimer: ReturnType<typeof setTimeout> | undefined
let loginAttempt = 0

const statusText = computed(() => {
  const labels: Record<Phase, Message | ''> = {
    outside: 'outside', loading: 'loading', profile: '', expired: 'expired',
    reopen: 'reopen', error: errorMessage.value, 'signed-out': 'signedOut',
  }
  const label = labels[phase.value]
  return label ? copy.value[label] : ''
})

const profileName = computed(() => {
  const name = profile.value?.display_name.trim()
  return name && /[\p{L}\p{N}\p{S}]/u.test(name) ? name : ''
})

const initials = computed(() =>
  profileName.value.split(/\s+/).slice(0, 2)
    .map((word) => Array.from(word)[0]).join('').toLocaleUpperCase(language.value),
)

function clearSession() {
  clearTimeout(expiryTimer)
  session.value = null
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
    if (!session.value || session.value.expiresAt <= Date.now()) {
      clearSession()
      const response = await exchangeTelegramData(initData, abort.signal)
      if (abort.signal.aborted) return
      const expiresAt = Date.parse(response.expires_at)
      if (!response.access_token || !Number.isFinite(expiresAt) || expiresAt <= Date.now()) {
        throw new Error('Сервер вернул недействительную сессию')
      }
      session.value = { token: response.access_token, expiresAt }
      expiryTimer = setTimeout(expireSession, expiresAt - Date.now())
    }

    const current = session.value
    if (!current) return
    const result = await fetchProfile(current.token, abort.signal)
    if (abort.signal.aborted || session.value !== current) return
    if (current.expiresAt <= Date.now()) {
      expireSession()
      return
    }
    profile.value = result
    phase.value = 'profile'
  } catch (error) {
    if (abort.signal.aborted || attempt !== loginAttempt || phase.value !== 'loading') return
    if (error instanceof ApiError && error.status === 401) {
      if (session.value) expireSession()
      else phase.value = 'reopen'
      return
    }
    errorMessage.value = error instanceof ApiError && error.status === 403
      ? 'signInDenied'
      : 'profileError'
    phase.value = 'error'
  }
}

async function signOut() {
  if (!session.value || signingOut.value) return
  const current = session.value
  signingOut.value = true
  errorMessage.value = ''
  try {
    await revokeSession(current.token, abort.signal)
  } catch (error) {
    if (abort.signal.aborted || session.value !== current) return
    if (!(error instanceof ApiError && error.status === 401)) {
      errorMessage.value = 'signOutError'
      return
    }
  } finally {
    if (session.value === current) signingOut.value = false
  }
  if (abort.signal.aborted || session.value !== current) return
  clearSession()
  phase.value = 'signed-out'
}

async function toggleNotifications() {
  if (!session.value || !profile.value || savingNotifications.value) return
  const current = session.value
  const enabled = !profile.value.telegram_notifications_enabled
  savingNotifications.value = true
  errorMessage.value = ''
  try {
    if (enabled && !await requestTelegramWriteAccess()) {
      if (session.value === current) errorMessage.value = 'grantNotifications'
      return
    }
    if (session.value !== current || abort.signal.aborted) return
    const saved = await setTelegramNotifications(current.token, enabled, abort.signal)
    if (session.value === current && profile.value) {
      profile.value.telegram_notifications_enabled = saved.enabled
    }
  } catch (error) {
    if (session.value !== current || abort.signal.aborted) return
    if (error instanceof ApiError && error.status === 401) expireSession()
    else errorMessage.value = 'notificationsError'
  } finally {
    if (session.value === current) savingNotifications.value = false
  }
}

onMounted(() => {
  const telegram = getTelegramWebApp()
  syncTelegramColors()
  telegram?.ready()
  if (telegram?.initData) void signIn()
})

onUnmounted(() => {
  abort.abort()
  clearSession()
})
</script>

<template>
  <div class="shell" @keydown.esc="escape">
    <nav v-if="menuOpen" ref="menuPanel" class="context-menu" :aria-label="copy.menu" tabindex="-1">
      <div class="menu-top">
        <button type="button" class="icon-button menu-back" :aria-label="copy.closeMenu" @click="closeMenu">
          <AppIcon name="back" />
        </button>
        <button type="button" class="menu-profile" :aria-label="copy.profile" @click="open('profile')">
          <span class="menu-crest" aria-hidden="true"></span>
          <span class="identity-text">
            <strong v-if="profileName">{{ profileName }}</strong>
            <strong v-else>{{ copy.profile }}</strong>
            <span v-if="profileName" class="menu-caption">{{ copy.profile }}</span>
          </span>
        </button>
      </div>
      <div class="menu-group">
        <NavRow v-for="section in discover" :key="section" :section="section"
          :label="copy[section]" :current="page === section || (section === 'games' && page === 'mafia')"
          :featured="page === 'home' && section === 'events'"
          @click="open(section)" />
      </div>
      <div class="menu-group">
        <NavRow v-for="section in personal" :key="section" :section="section"
          :label="copy[section]" :current="page === section" @click="open(section)" />
      </div>
    </nav>

    <template v-else>
      <header class="top-bar">
        <button ref="menuTrigger" type="button" class="icon-button" :aria-label="copy.menu" @click="menuOpen = true">
          <AppIcon name="menu" />
        </button>
        <select id="language-select" v-model="language" class="language-switch" :aria-label="copy.language">
          <option value="ru" lang="ru" aria-label="Русский">RU</option>
          <option value="en" lang="en" aria-label="English">EN</option>
        </select>
        <button type="button" class="wordmark" @click="open('home')">
          <span class="visually-hidden">MSLegion</span>
          <span class="wordmark-art" aria-hidden="true"></span>
        </button>
        <button type="button" class="icon-button search-trigger" :aria-label="page === 'search' ? copy.back : copy.search"
          @click="toggleSearch">
          <AppIcon :name="page === 'search' ? 'back' : 'search'" />
        </button>
      </header>

      <main class="content" aria-labelledby="page-title">
        <h1 id="page-title" ref="pageHeading" tabindex="-1">{{ copy[page] }}</h1>
        <button v-if="page === 'mafia'" type="button" class="secondary mafia-back" @click="open('games')">
          <AppIcon name="back" /> {{ copy.allGames }}
        </button>

        <template v-if="page === 'home'">
          <button type="button" class="hero" @click="open('events')">
            <span class="hero-content">
              <span class="hero-tag">{{ copy.events }}</span>
              <strong>{{ copy.quiz }}</strong>
              <span class="hero-status">{{ copy.comingSoon }}</span>
            </span>
          </button>
          <div class="home-links">
            <NavRow v-for="section in shortcuts" :key="section" :section="section"
              :label="copy[section]" @click="open(section)" />
          </div>
        </template>

        <template v-else-if="page === 'search'">
          <label class="search-field">
            <AppIcon name="search" />
            <input ref="searchField" v-model="query" type="search"
              :aria-label="copy.searchHint" :placeholder="copy.searchHint" />
          </label>
          <div v-if="matches.length" class="menu-group">
            <NavRow v-for="section in matches" :key="section" :section="section"
              :label="copy[section]" @click="open(section)" />
          </div>
          <p v-else class="panel muted" role="status">{{ copy.noMatches }}</p>
        </template>

        <section v-else-if="page === 'settings'" class="panel">
          <label class="theme-setting" for="theme-select">
            <span>{{ copy.theme }}</span>
            <select id="theme-select" v-model="theme">
              <option v-for="id in themes" :key="id" :value="id">{{ copy[id] }}</option>
            </select>
          </label>
        </section>

        <div v-else-if="page === 'games'" class="menu-group">
          <NavRow section="mafia" :label="copy.mafia" @click="open('mafia')" />
        </div>

        <section v-else-if="page === 'events' || page === 'media'" class="panel empty-section">
          <AppIcon :name="page" class="empty-icon" />
          <p class="muted">{{ copy[emptyMessages[page]] }}</p>
        </section>

        <template v-else-if="profile && session">
          <MafiaGame v-if="page === 'mafia'" :key="session.token" :token="session.token"
            :user-id="profile.id" :language="language" @expired="expireSession" />

          <section v-else-if="page === 'profile'" class="panel">
            <div class="identity">
              <span class="avatar" aria-hidden="true">{{ initials || '–' }}</span>
              <div class="identity-text">
                <p class="name">{{ profileName || copy.profile }}</p>
                <p v-if="profile.telegram_id !== null" class="muted">Telegram ID {{ profile.telegram_id }}</p>
              </div>
            </div>
            <div class="actions">
              <p v-if="errorMessage" class="muted" role="alert">{{ copy[errorMessage] }}</p>
              <button type="button" class="secondary" :disabled="signingOut" @click="signOut">
                {{ copy[signingOut ? 'signingOut' : 'signOut'] }}
              </button>
            </div>
          </section>

          <section v-else-if="page === 'notifications'" class="panel">
            <p class="muted">{{ copy.notificationsHint }}</p>
            <div class="actions">
              <p v-if="errorMessage" class="muted" role="alert">{{ copy[errorMessage] }}</p>
              <button type="button" class="secondary" data-notification-toggle
                :disabled="signingOut || savingNotifications" @click="toggleNotifications">
                {{ copy[profile.telegram_notifications_enabled ? 'disableNotifications' : 'enableNotifications'] }}
              </button>
            </div>
          </section>

          <CommunityList v-else-if="page === 'communities'" :token="session.token"
            :user-id="profile.id" :language="language" @expired="expireSession" />
        </template>

        <section v-else class="panel" :aria-busy="phase === 'loading'">
          <div class="status" role="status">
            <span v-if="phase === 'loading'" class="spinner" aria-hidden="true"></span>
            <strong>{{ statusText }}</strong>
            <p v-if="phase === 'outside'" class="muted">{{ copy.outsideHint }}</p>
            <p v-else-if="phase === 'reopen'" class="muted">{{ copy.reopenHint }}</p>
          </div>
          <button v-if="phase === 'expired' || phase === 'error' || phase === 'signed-out'"
            type="button" class="primary" @click="signIn">
            {{ copy[phase === 'error' ? 'retry' : 'signIn'] }}
          </button>
        </section>
      </main>
    </template>
  </div>
</template>
