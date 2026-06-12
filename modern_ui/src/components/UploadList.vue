<template>
  <div class="upload-list">
    <div v-for="item in uploads" :key="item.path" class="upload-item">
      <span>{{ item.filename }} · {{ item.category }}</span>
      <el-button size="small" @click="preview(item.url)">预览</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ uploads: any[] }>()

const preview = (url: string) => {
  window.open(url, '_blank')
}
</script>
