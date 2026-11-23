<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { ApiError, fetchCommunities, type Community } from './api'
import AppIcon from './AppIcon.vue'
import { messages, type Language } from './locale'

const props = defineProps<{ token: string; userId: string; language: Language }>()
const emit = defineEmits<{ expired: [] }>()
const communities = ref<Community[]>([])
const busy = ref(false)
const failed = ref(false)
const hasMore = ref(false)
const abort = new AbortController()
const pageSize = 50

async function load() {
  if (busy.value) return
  busy.value = true
  failed.value = false
  try {
    const rows = await fetchCommunities(props.token, communities.value.length, pageSize, abort.signal)
    if (abort.signal.aborted) return
    communities.value.push(...rows)
    hasMore.value = rows.length === pageSize
  } catch (error) {
    if (abort.signal.aborted) return
    if (error instanceof ApiError && error.status === 401) emit('expired')
    else failed.value = true
  } finally {
    busy.value = false
  }
}

onMounted(load)
onUnmounted(() => abort.abort())
</script>

<template>
  <section class="panel" :aria-busy="busy">
    <ul v-if="communities.length" class="community-list">
      <li v-for="community in communities" :key="community.id">
        <AppIcon name="communities" class="nav-icon" />
        <div>
          <strong>{{ community.name }}</strong>
          <p class="muted">{{ messages[language][community.owner_id === userId ? 'owner' : 'member'] }}</p>
        </div>
      </li>
    </ul>
    <p v-if="busy" class="muted" role="status">{{ messages[language].communitiesLoading }}</p>
    <p v-else-if="failed" class="muted" role="alert">{{ messages[language].communitiesError }}</p>
    <p v-else-if="!communities.length" class="muted">{{ messages[language].communitiesEmpty }}</p>
    <button v-if="failed || hasMore" type="button" class="secondary list-action" :disabled="busy" @click="load">
      {{ messages[language][failed ? 'retry' : 'loadMore'] }}
    </button>
  </section>
</template>
