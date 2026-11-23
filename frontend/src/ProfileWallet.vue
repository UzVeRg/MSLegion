<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ApiError, getWallet, claimDailyReward, type Wallet } from './api'
import lcCoin from './assets/lc-coin.png'
import type { Language } from './locale'

const props = defineProps<{ token: string; language: Language }>()
const emit = defineEmits<{ expired: [] }>()

const labels = {
  ru: {
    balance: 'Баланс', checkIn: 'Ежедневная отметка', streak: 'Серия входов',
    day: 'День', claim: 'Отметиться', claimedToday: 'Сегодня отмечено', claimed: 'Получено',
    loading: 'Загружаем баланс', saving: 'Сохраняем отметку',
    error: 'Не удалось обновить баланс', retry: 'Повторить',
  },
  en: {
    balance: 'Balance', checkIn: 'Daily check-in', streak: 'Login streak',
    day: 'Day', claim: 'Check in', claimedToday: 'Checked in today', claimed: 'Claimed',
    loading: 'Loading balance', saving: 'Saving check-in',
    error: 'Could not update the balance', retry: 'Try again',
  },
}
const copy = computed(() => labels[props.language])
const wallet = ref<Wallet | null>(null)
const loading = ref(false)
const failed = ref(false)
const abort = new AbortController()
let resetTimer: ReturnType<typeof setTimeout> | undefined

const amount = computed(() => wallet.value
  ? new Intl.NumberFormat(props.language).format(BigInt(wallet.value.balance))
  : '',
)
const rewardToday = computed(() => wallet.value?.rewards.find((reward) => reward.day === wallet.value?.day))

async function syncWallet(date?: string) {
  if (loading.value) return
  clearTimeout(resetTimer)
  loading.value = true
  failed.value = false
  try {
    let result: Wallet
    if (date) {
      try {
        result = await claimDailyReward(props.token, date, abort.signal)
      } catch (error) {
        if (!(error instanceof ApiError && error.status === 409)) throw error
        result = await getWallet(props.token, abort.signal)
      }
    } else {
      result = await getWallet(props.token, abort.signal)
    }
    if (abort.signal.aborted) return
    wallet.value = result
    resetTimer = setTimeout(() => void syncWallet(), result.seconds_until_reset * 1000 + 250)
  } catch (error) {
    if (abort.signal.aborted) return
    if (error instanceof ApiError && error.status === 401) emit('expired')
    else failed.value = true
  } finally {
    loading.value = false
  }
}

onMounted(() => void syncWallet())
onUnmounted(() => {
  abort.abort()
  clearTimeout(resetTimer)
})
</script>

<template>
  <section class="panel lc-balance" aria-labelledby="lc-balance-title" :aria-busy="loading">
    <img :src="lcCoin" width="56" height="56" alt="">
    <div class="lc-balance-main">
      <h2 id="lc-balance-title">{{ copy.balance }}</h2>
      <p v-if="wallet" class="lc-value" aria-live="polite">
        <strong class="lc-amount">{{ amount }}</strong><span>LC</span>
      </p>
      <p v-else-if="loading" class="muted" role="status">{{ copy.loading }}</p>
    </div>
    <div v-if="failed" class="lc-error">
      <p class="muted" role="alert">{{ copy.error }}</p>
      <button type="button" class="secondary" @click="syncWallet()">{{ copy.retry }}</button>
    </div>
  </section>

  <section v-if="wallet" class="panel lc-checkins" aria-labelledby="lc-checkins-title" :aria-busy="loading">
    <h2 id="lc-checkins-title">{{ copy.checkIn }}</h2>
    <p class="lc-streak muted">{{ copy.streak }}: <strong>{{ wallet.streak }}</strong></p>
    <ol class="lc-days" role="list">
      <li v-for="reward in wallet.rewards" :key="reward.day"
        :aria-current="reward.day === wallet.day ? 'date' : undefined"
        :class="{ 'lc-day--claimed': reward.day <= wallet.streak }">
        <span>{{ copy.day }} {{ reward.day }}</span>
        <strong>+{{ reward.amount }} <span>LC</span></strong>
        <span v-if="reward.day <= wallet.streak" class="visually-hidden"> · {{ copy.claimed }}</span>
      </li>
    </ol>
    <p v-if="wallet.claimed_today" class="lc-claimed" role="status">
      <span aria-hidden="true">✓</span> {{ copy.claimedToday }}
    </p>
    <button v-else-if="!failed && rewardToday" type="button" class="primary lc-claim"
      :disabled="loading" @click="syncWallet(wallet.date)">
      {{ loading ? copy.saving : copy.claim + ' · +' + rewardToday.amount + ' LC' }}
    </button>
  </section>
</template>

<style scoped>
.lc-balance {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: .85rem;
  border-color: var(--rim);
}

.lc-balance img {
  width: clamp(2.75rem, 12vw, 3.5rem);
  height: auto;
  border-radius: 50%;
}

.lc-balance h2, .lc-checkins h2 {
  margin: 0;
  font-size: 1.12rem;
  line-height: 1.3;
}

.lc-balance h2 {
  color: var(--muted);
  font-size: .9rem;
}

.lc-value {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 0 .4rem;
  color: #f3da91;
  font-size: .95rem;
  font-weight: 750;
}

.lc-amount {
  overflow-wrap: anywhere;
  font-size: clamp(1.95rem, 8vw, 2.8rem);
  font-weight: 850;
  font-variant-numeric: tabular-nums;
  line-height: 1.14;
}

@supports (background-clip: text) {
  .lc-amount {
    background: linear-gradient(180deg, #fff1c1 12%, #eac275 49%, #ba8750 53%, #ffe1a4 88%);
    background-clip: text;
    color: transparent;
  }
}

@media (forced-colors: active) {
  .lc-amount {
    background: none;
    color: CanvasText;
  }
}

.lc-error {
  grid-column: 1 / -1;
  display: grid;
  justify-items: start;
  gap: .5rem;
}

.lc-streak { margin-block: .25rem .8rem; }
.lc-streak strong { color: var(--accent); }

.lc-days {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: clamp(.2rem, 1.5vw, .5rem);
  margin: 0;
  padding: 0;
  list-style: none;
}

.lc-days li {
  display: grid;
  align-content: center;
  gap: .25rem;
  min-height: 4rem;
  padding: .35rem .15rem;
  border: 1px solid var(--border);
  border-radius: min(var(--radius), .65rem);
  background: var(--panel);
  text-align: center;
  overflow-wrap: anywhere;
}

.lc-days li[aria-current] {
  border-color: var(--accent);
  background: var(--selection);
}

.lc-days .lc-day--claimed { background: var(--panel-raised); }
.lc-days li > span { color: var(--muted); font-size: .72rem; }
.lc-days strong { font-size: clamp(.8rem, 3.5vw, 1.05rem); }
.lc-days strong span { font-size: .72rem; }
.lc-days li[aria-current] strong { color: var(--accent); }

.lc-claim { width: 100%; text-align: center; }
.lc-claimed {
  margin-block-start: 1rem;
  color: var(--accent);
  font-weight: 650;
}
</style>
