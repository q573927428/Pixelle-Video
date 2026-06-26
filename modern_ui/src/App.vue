<template>
  <template v-if="showAppLayout">
    <AppLayout>
      <router-view />
    </AppLayout>
  </template>
  <template v-else>
    <router-view />
  </template>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { appRoutes } from './router'
import AppLayout from './views/AppLayout.vue'

const route = useRoute()
const showAppLayout = computed(() => appRoutes.includes(route.name as string))
</script>