<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  ApiError, createMafiaRoom, fetchMafiaRoom, fetchMafiaRooms, playMafiaAction,
  type MafiaAction, type MafiaRoom, type MafiaSettings, type MafiaSummary,
} from './api'
import AppIcon from './AppIcon.vue'
import type { Language } from './locale'
import { mafiaMessages, type MafiaMessage } from './mafiaLocale'

const props = defineProps<{ token: string; userId: string; language: Language }>()
const emit = defineEmits<{ expired: [] }>()
const copy = computed(() => mafiaMessages[props.language])
const settings = ref<MafiaSettings>({
  mode: 'classic', doctor: true, detective: true, night_seconds: 45, day_seconds: 90, vote_seconds: 35,
})
const durations = [
  { field: 'night_seconds', label: 'nightTime', max: 180 },
  { field: 'day_seconds', label: 'dayTime', max: 300 },
  { field: 'vote_seconds', label: 'voteTime', max: 180 },
] as const
const errorLabels: Record<number, MafiaMessage> = {
  403: 'denied', 404: 'missing', 409: 'conflict', 422: 'invalid', 429: 'rateLimit',
}
const codeInput = ref('')
const rooms = ref<MafiaSummary[]>([])
const room = ref<MafiaRoom | null>(null)
const busy = ref(false)
const listLoading = ref(false)
const listFailed = ref(false)
const pollFailed = ref(false)
const error = ref<MafiaMessage | null>(null)
const picked = ref('')
const message = ref('')
const copied = ref(false)
const listTitle = ref<HTMLElement>()
const roomTitle = ref<HTMLElement>()
const chatList = ref<HTMLElement>()
const time = ref(Date.now())
const serverOffset = ref(0)
const controller = new AbortController()
let pollController: AbortController | undefined
let pollTimer: ReturnType<typeof setInterval>
let clockTimer: ReturnType<typeof setInterval>

const canJoin = computed(() => /^[0-9a-f]{10}$/i.test(codeInput.value.trim()))
const isHost = computed(() => room.value?.host_id === props.userId)
const own = computed(() => room.value?.players.find((player) => player.id === props.userId))
const alive = computed(() => room.value?.players.filter((player) => player.alive).length ?? 0)
const countdown = computed(() => {
  if (!room.value?.deadline || room.value.phase === 'lobby') return ''
  const seconds = Math.max(0, Math.ceil(
    (Date.parse(room.value.deadline) - time.value - serverOffset.value) / 1000,
  ))
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
})
const lastMessage = computed(() => room.value?.messages.at(-1)?.id)
const roleHelp = {
  citizen: 'citizenHelp', mafia: 'mafiaHelp', doctor: 'doctorHelp', detective: 'detectiveHelp',
} as const
const winnerLabel = { mafia: 'mafiaWins', town: 'townWins', draw: 'draw' } as const

function playerName(id: string) {
  return room.value?.players.find((player) => player.id === id)?.name ?? ''
}

function updateRoom(next: MafiaRoom) {
  if (room.value?.turn !== next.turn || room.value?.code !== next.code) {
    picked.value = ''
    if (room.value?.chat !== next.chat) message.value = ''
  }
  room.value = next
  time.value = Date.now()
  serverOffset.value = Date.parse(next.server_time) - time.value
  pollFailed.value = false
}

function showError(cause: unknown) {
  if (controller.signal.aborted) return
  if (cause instanceof ApiError && cause.status === 401) {
    emit('expired')
    return
  }
  error.value = (cause instanceof ApiError ? errorLabels[cause.status] : null) ?? 'unavailable'
}

async function loadRooms() {
  if (listLoading.value) return
  listLoading.value = true
  listFailed.value = false
  try {
    rooms.value = await fetchMafiaRooms(props.token, controller.signal)
  } catch (cause) {
    listFailed.value = true
    if (cause instanceof ApiError && cause.status === 401) showError(cause)
  } finally {
    listLoading.value = false
  }
}

async function refreshRoom() {
  const current = room.value
  if (!current || current.phase === 'finished' || busy.value || pollController || document.hidden) return
  const request = new AbortController()
  pollController = request
  try {
    const next = await fetchMafiaRoom(props.token, current.code, request.signal)
    if (!request.signal.aborted) updateRoom(next)
  } catch (cause) {
    if (request.signal.aborted) return
    if (cause instanceof ApiError && cause.status === 401) showError(cause)
    else if (cause instanceof ApiError && cause.status === 404) {
      await returnToRooms()
      showError(cause)
    } else pollFailed.value = true
  } finally {
    if (pollController === request) pollController = undefined
  }
}

async function returnToRooms() {
  pollController?.abort()
  room.value = null
  message.value = ''
  error.value = null
  copied.value = false
  await nextTick()
  listTitle.value?.focus()
  void loadRooms()
}

async function run(operation: () => Promise<MafiaRoom | null>): Promise<boolean> {
  if (busy.value) return false
  pollController?.abort()
  busy.value = true
  error.value = null
  const wasInRoom = Boolean(room.value)
  try {
    const next = await operation()
    if (controller.signal.aborted) return false
    if (!next) await returnToRooms()
    else {
      updateRoom(next)
      if (!wasInRoom) {
        await nextTick()
        roomTitle.value?.focus()
      }
    }
    return true
  } catch (cause) {
    showError(cause)
    return false
  } finally {
    busy.value = false
  }
}

function create() {
  return run(() => createMafiaRoom(props.token,
    settings.value.mode === 'classic' ? { mode: 'classic' } : settings.value, controller.signal,
  ))
}

function join() {
  if (!canJoin.value) return
  const code = codeInput.value.trim().toUpperCase()
  return run(() => playMafiaAction(props.token, code, { type: 'join' }, controller.signal))
}

function enter(code: string) {
  return run(() => fetchMafiaRoom(props.token, code, controller.signal))
}

function play(action: MafiaAction) {
  const current = room.value
  if (!current) return
  return run(() => playMafiaAction(props.token, current.code, action, controller.signal))
}

async function sendMessage() {
  if (!room.value || !message.value.trim()) return
  const text = message.value.trim()
  if (await play({ type: 'chat', turn: room.value.turn, text })) message.value = ''
}

async function copyCode() {
  if (!room.value) return
  try {
    await navigator.clipboard.writeText(room.value.code)
    copied.value = true
  } catch {
    const code = roomTitle.value?.querySelector('code')
    if (code && window.getSelection()) {
      const range = document.createRange()
      range.selectNodeContents(code)
      window.getSelection()?.removeAllRanges()
      window.getSelection()?.addRange(range)
    }
  }
}

watch(lastMessage, () => {
  const list = chatList.value
  if (!list || list.scrollHeight - list.scrollTop - list.clientHeight <= 80) {
    void nextTick(() => {
      if (chatList.value) chatList.value.scrollTop = chatList.value.scrollHeight
    })
  }
})

onMounted(() => {
  void loadRooms()
  pollTimer = setInterval(() => void refreshRoom(), 2000)
  clockTimer = setInterval(() => { time.value = Date.now() }, 250)
  document.addEventListener('visibilitychange', refreshRoom)
})

onUnmounted(() => {
  controller.abort()
  pollController?.abort()
  clearInterval(pollTimer)
  clearInterval(clockTimer)
  document.removeEventListener('visibilitychange', refreshRoom)
})
</script>

<template>
  <div class="mafia">
    <p v-if="error" class="panel mafia-notice" role="alert">{{ copy[error] }}</p>
    <template v-if="!room">
      <section class="panel mafia-section" aria-labelledby="mafia-rooms-title">
        <h2 id="mafia-rooms-title" ref="listTitle" tabindex="-1">{{ copy.rooms }}</h2>
        <p class="muted">{{ copy.guide }}</p>
        <form class="mafia-form mafia-join" @submit.prevent="join">
          <label for="mafia-code">{{ copy.code }}</label>
          <div class="mafia-inline">
            <input id="mafia-code" v-model="codeInput" autocomplete="off" autocapitalize="characters"
              spellcheck="false" maxlength="10" placeholder="AB12CD34EF" :disabled="busy" />
            <button class="secondary" type="submit" :disabled="busy || !canJoin">{{ copy.join }}</button>
          </div>
        </form>
      </section>

      <section class="panel mafia-section" aria-labelledby="mafia-create-title">
        <h2 id="mafia-create-title">{{ copy.create }}</h2>
        <form class="mafia-form" @submit.prevent="create">
          <label for="mafia-mode">{{ copy.mode }}</label>
          <select id="mafia-mode" v-model="settings.mode" :disabled="busy">
            <option value="classic">{{ copy.classic }}</option>
            <option value="custom">{{ copy.custom }}</option>
          </select>
          <template v-if="settings.mode === 'custom'">
            <div class="mafia-buttons">
              <label class="mafia-check" for="mafia-doctor">
                <input id="mafia-doctor" v-model="settings.doctor" type="checkbox" :disabled="busy" />
                {{ copy.doctor }}
              </label>
              <label class="mafia-check" for="mafia-detective">
                <input id="mafia-detective" v-model="settings.detective" type="checkbox" :disabled="busy" />
                {{ copy.detective }}
              </label>
            </div>
            <div class="mafia-times">
              <label v-for="duration in durations" :key="duration.field">
                {{ copy[duration.label] }}
                <input v-model.number="settings[duration.field]" type="number" min="15" :max="duration.max"
                  required :disabled="busy" />
              </label>
            </div>
          </template>
          <button class="primary" type="submit" :disabled="busy">{{ copy.create }}</button>
        </form>
      </section>

      <section class="panel mafia-section" aria-labelledby="mafia-mine">
        <h2 id="mafia-mine">{{ copy.myRooms }}</h2>
        <p v-if="listLoading" class="muted" role="status">{{ copy.loading }}</p>
        <template v-else-if="listFailed">
          <p class="muted" role="alert">{{ copy.unavailable }}</p>
          <button class="secondary" type="button" @click="loadRooms">{{ copy.retry }}</button>
        </template>
        <ul v-else-if="rooms.length" class="mafia-list">
          <li v-for="item in rooms" :key="item.code">
            <button type="button" class="secondary mafia-room-entry" :disabled="busy" @click="enter(item.code)">
              <code>{{ item.code }}</code>
              <span class="muted">{{ copy[item.mode] }} · {{ copy[item.phase] }} · {{ item.player_count }}/12</span>
              <AppIcon name="next" />
            </button>
          </li>
        </ul>
        <p v-else class="muted">{{ copy.noRooms }}</p>
      </section>
    </template>

    <template v-else>
      <button class="secondary mafia-back" type="button" :disabled="busy" @click="returnToRooms">
        <AppIcon name="back" /> {{ copy.rooms }}
      </button>
      <p v-if="pollFailed" class="panel mafia-notice" role="status">{{ copy.unavailable }}</p>
      <section class="panel mafia-section" aria-labelledby="mafia-room-title">
        <div class="mafia-summary">
          <div>
            <p class="muted">{{ copy[room.settings.mode] }}<span v-if="room.round"> · {{ copy.round }} {{ room.round }}</span></p>
            <h2 id="mafia-room-title" ref="roomTitle" tabindex="-1">{{ copy[room.phase] }} <code>{{ room.code }}</code></h2>
          </div>
          <time v-if="countdown && room.deadline" class="mafia-timer" :datetime="room.deadline">{{ countdown }}</time>
        </div>
        <template v-if="room.phase === 'lobby'">
          <p class="muted">{{ copy.waiting }} {{ copy.lobbyHelp }}</p>
          <p class="muted">{{ copy.shareCode }}</p>
          <div class="mafia-buttons">
            <button class="secondary" type="button" @click="copyCode">{{ copy.copy }}</button>
            <button v-if="isHost" class="primary" type="button" :disabled="busy || room.players.length < 5"
              @click="play({ type: 'start' })">{{ copy.start }}</button>
            <button class="secondary" type="button" :disabled="busy" @click="play({ type: 'leave' })">{{ copy.leave }}</button>
          </div>
          <p v-if="copied" class="muted" role="status">{{ copy.copied }}</p>
        </template>
        <p v-else-if="room.winner" class="mafia-role" role="status">{{ copy[winnerLabel[room.winner]] }}</p>
        <template v-else>
          <p v-if="!own?.alive" class="muted">{{ copy.observing }}</p>
          <div v-if="room.role" class="mafia-role">
            <span class="muted">{{ copy.role }}</span>
            <strong>{{ copy[room.role] }}</strong>
            <p class="muted">{{ copy[roleHelp[room.role]] }}</p>
          </div>
          <p v-if="room.phase === 'night' && own?.alive && !room.can_target" class="muted">{{ copy.sleeping }}</p>
          <p v-if="room.phase === 'vote'" class="muted">{{ copy.votes }} {{ room.vote_count }}/{{ alive }}</p>
          <button v-if="room.phase === 'day' && isHost" class="primary" type="button" :disabled="busy"
            @click="play({ type: 'open_vote', turn: room.turn })">{{ copy.openVote }}</button>
          <p v-if="room.target_locked" class="muted" role="status">
            {{ room.target_id ? `${copy.picked} · ${playerName(room.target_id)}` : copy.skipped }}
          </p>
          <form v-else-if="room.can_target" class="mafia-form"
            @submit.prevent="play({ type: 'target', turn: room.turn, target_id: picked === 'skip' ? null : picked })">
            <label for="mafia-target">{{ copy.target }}</label>
            <div class="mafia-inline">
              <select id="mafia-target" v-model="picked" required :disabled="busy">
                <option disabled value="">{{ copy.target }}</option>
                <option v-for="id in room.eligible_targets" :key="id" :value="id">{{ playerName(id) }}</option>
                <option value="skip">{{ copy.abstain }}</option>
              </select>
              <button class="primary" type="submit" :disabled="busy || !picked">{{ copy.confirm }}</button>
            </div>
          </form>
        </template>
      </section>

      <section class="panel mafia-section" aria-labelledby="mafia-players">
        <h2 id="mafia-players">{{ copy.players }} <span class="muted">{{ room.players.length }}/12</span></h2>
        <ul class="mafia-list mafia-players">
          <li v-for="player in room.players" :key="player.id">
            <strong>{{ player.name }}</strong>
            <span v-if="player.id === room.host_id" class="muted">{{ copy.host }}</span>
            <span v-if="!player.alive" class="muted">{{ copy.eliminated }}</span>
            <span v-if="player.role" class="muted">{{ copy[player.role] }}</span>
            <span v-else-if="room.allies.includes(player.id)" class="muted">{{ copy.ally }}</span>
          </li>
        </ul>
      </section>

      <section v-if="room.chat" class="panel mafia-section" aria-labelledby="mafia-chat">
        <h2 id="mafia-chat">{{ copy[room.chat === 'mafia' ? 'mafiaChat' : 'publicChat'] }}</h2>
        <ul v-if="room.messages.length" :key="room.chat" ref="chatList" class="mafia-list mafia-chat-log" aria-live="polite">
          <li v-for="item in room.messages" :key="item.id">
            <strong>{{ item.name }}</strong>
            <p>{{ item.text }}</p>
          </li>
        </ul>
        <p v-else class="muted">{{ copy.chatEmpty }}</p>
        <form v-if="room.can_chat" class="mafia-inline" @submit.prevent="sendMessage">
          <input v-model="message" :aria-label="copy.message" :placeholder="copy.message" maxlength="300" :disabled="busy" />
          <button class="secondary" type="submit" :disabled="busy || !message.trim()">{{ copy.send }}</button>
        </form>
      </section>

      <section v-if="room.investigations.length" class="panel mafia-section" aria-labelledby="mafia-investigations">
        <h2 id="mafia-investigations">{{ copy.investigations }}</h2>
        <ul class="mafia-list">
          <li v-for="item in room.investigations" :key="item.round">
            {{ playerName(item.player_id) }} · {{ copy[item.mafia ? 'mafia' : 'townResult'] }}
          </li>
        </ul>
      </section>

      <section v-if="room.history.length" class="panel mafia-section" aria-labelledby="mafia-history">
        <h2 id="mafia-history">{{ copy.log }}</h2>
        <ul class="mafia-list">
          <li v-for="item in [...room.history].reverse()" :key="`${item.round}-${item.phase}`">
            <span class="muted">{{ copy.round }} {{ item.round }} · </span>
            <template v-if="item.player_id">{{ copy[item.phase === 'night' ? 'nightOut' : 'voteOut'] }} · {{ playerName(item.player_id) }}</template>
            <template v-else>{{ copy[item.phase === 'night' ? 'noNightOut' : 'noVoteOut'] }}</template>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>
