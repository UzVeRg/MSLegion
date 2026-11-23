<script setup lang="ts">
import AppIcon from './AppIcon.vue'
import type { Section } from './locale'

defineProps<{ section: Section; label: string; current?: boolean; featured?: boolean }>()
</script>

<template>
  <button type="button" class="nav-row" :class="{ 'nav-row--featured': featured }" :aria-current="current ? 'page' : undefined">
    <AppIcon :name="section" class="nav-icon" />
    <span>{{ label }}</span>
    <AppIcon name="next" class="nav-next" />
  </button>
</template>
