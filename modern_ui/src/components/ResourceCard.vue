<template>
  <div class="card">
    <div class="card-header"><h3 class="card-title">{{ title }}</h3></div>
    <div class="card-body">
      <div v-if="!items.length" class="empty-preview">暂无资源</div>
      <div v-for="item in items" :key="item.key || item.path || item.name" class="upload-item">
        <span>{{ item[labelKey] || (fallbackLabelKey ? item[fallbackLabelKey] : '') || item.key || item.name }}</span>
        <el-tag>{{ item[tagKey] || '-' }}</el-tag>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  items: any[]
  labelKey: string
  fallbackLabelKey?: string
  tagKey: string
}>()
</script>