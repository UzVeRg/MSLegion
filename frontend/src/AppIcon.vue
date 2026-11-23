<script setup lang="ts">
import type { Section } from './locale'

type Icon = Section | 'menu' | 'search' | 'back' | 'next'

defineProps<{ name: Icon }>()

const paths: Record<Exclude<Icon, 'mafia'>, string> = {
  menu: 'M3 6h18M3 12h18M3 18h18',
  search: 'M20.5 20.5 16 16m2-5a7 7 0 1 1-14 0 7 7 0 0 1 14 0Z',
  back: 'm15 5-7 7 7 7',
  next: 'm9 5 7 7-7 7',
  home: 'm3 10 9-7 9 7v10H3V10Zm6 10v-7h6v7',
  games: 'M7 7h10a4 4 0 0 1 4 3l1 5a2.5 2.5 0 0 1-4 2l-2.5-2H8.5L6 17a2.5 2.5 0 0 1-4-2l1-5a4 4 0 0 1 4-3Zm0 3v4m-2-2h4m6 0h.01m3 0h.01',
  events: 'M5 5h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Zm2-2v4m10-4v4M3 10h18M8 14h.01M12 14h.01m4 0h.01M8 17h.01m4 0h.01',
  media: 'M5 5h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Zm5 4 5 3-5 3V9Z',
  communities: 'M8 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm8-6a3 3 0 0 1 0 6M2 19v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2m2-6h2a4 4 0 0 1 4 4v2',
  profile: 'M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 9v-2a5 5 0 0 1 5-5h4a5 5 0 0 1 5 5v2',
  notifications: 'M18 8a6 6 0 1 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9Zm-8 12a2 2 0 0 0 4 0',
  faq: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM9.8 9a2.3 2.3 0 1 1 3.2 2.1c-.8.4-1 1-1 1.9m0 3h.01',
  settings: 'm10 3-.7 2.8-1.8 1L4.7 6l-2 3.5 2.1 2v1L2.7 15l2 3.5 2.8-.8 1.8 1L10 21h4l.7-2.3 1.8-1 2.8.8 2-3.5-2.1-2.5v-1l2.1-2-2-3.5-2.8.8-1.8-1L14 3h-4Zm2 12a3 3 0 1 1 0-6 3 3 0 0 1 0 6Z',
}
</script>

<template>
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65"
    stroke-linejoin="round" stroke-linecap="round" aria-hidden="true">
    <path :d="paths[name === 'mafia' ? 'games' : name]" />
  </svg>
</template>
