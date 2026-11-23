<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { getSupport, type SupportContent } from './api'
import { messages, type Language } from './locale'
import { getTelegramWebApp } from './telegram'

const props = defineProps<{ language: Language }>()
const copy = computed(() => messages[props.language])
const content = ref<SupportContent>()
const failed = ref(false)
const attempt = ref(0)

watch([() => props.language, attempt], async ([language], _, onCleanup) => {
  const controller = new AbortController()
  onCleanup(() => controller.abort())
  content.value = undefined
  failed.value = false
  try {
    const result = await getSupport(language, controller.signal)
    if (!controller.signal.aborted) content.value = result
  } catch {
    if (!controller.signal.aborted) failed.value = true
  }
}, { immediate: true })

function followContact(event: MouseEvent, contact: SupportContent['contacts'][number]) {
  const app = getTelegramWebApp()
  if (contact.channel !== 'telegram' || !app?.openTelegramLink) return
  app.openTelegramLink(contact.url)
  event.preventDefault()
}
</script>

<template>
  <template v-if="content">
    <section class="panel support-section" aria-labelledby="support-questions">
      <h2 id="support-questions">{{ copy.supportQuestions }}</h2>
      <p v-if="!content.questions.length" class="muted">{{ copy.supportNoQuestions }}</p>
      <details v-for="(item, index) in content.questions" :key="index" class="support-question" name="support-faq">
        <summary>{{ item.question }}</summary>
        <p class="muted">{{ item.answer }}</p>
      </details>
    </section>
    <section class="panel support-section" aria-labelledby="support-contacts">
      <h2 id="support-contacts">{{ copy.supportContacts }}</h2>
      <p v-if="!content.contacts.length" class="muted">{{ copy.supportNoContacts }}</p>
      <ul v-else class="support-contacts">
        <li v-for="contact in content.contacts" :key="contact.channel">
          <a class="secondary" :href="contact.url" @click="followContact($event, contact)">
            <strong>{{ { telegram: 'Telegram', discord: 'Discord', email: copy.supportEmail }[contact.channel] }}</strong>
            <span class="muted">{{ contact.label }}</span>
          </a>
        </li>
      </ul>
    </section>
  </template>
  <section v-else-if="failed" class="panel support-section">
    <p role="alert">{{ copy.supportError }}</p>
    <button class="secondary" type="button" @click="attempt++">{{ copy.retry }}</button>
  </section>
  <p v-else class="panel muted" role="status">{{ copy.supportLoading }}</p>
</template>

<style scoped>
.support-section { display: grid; gap: .8rem; }
.support-section h2 { margin: 0; font-size: 1.25rem; }
.support-question {
  border: 1px solid var(--control-border);
  border-radius: var(--radius);
  background: var(--panel);
  overflow-wrap: anywhere;
}
.support-question summary { padding: .8rem; cursor: pointer; font-weight: 680; }
.support-question[open] summary { color: var(--accent); }
.support-question p { padding: 0 .8rem .8rem; white-space: pre-wrap; }
.support-contacts { display: grid; gap: .55rem; padding: 0; margin: 0; list-style: none; }
.support-contacts a {
  display: grid;
  gap: .15rem;
  color: var(--text);
  overflow-wrap: anywhere;
  text-decoration: none;
}
.support-section :is(summary, a):focus-visible { outline: 2px solid var(--accent); outline-offset: -3px; }
</style>
