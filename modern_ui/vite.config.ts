import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'url'

export default defineConfig({
  plugins: [vue()],
  root: '.',
  base: '/modern/',
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/files': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: fileURLToPath(new URL('index.html', import.meta.url)),
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/vue/')) {
            return 'vendor-vue';
          }
          if (id.includes('node_modules/element-plus') || id.includes('node_modules/@element-plus')) {
            return 'vendor-element-plus';
          }
        },
      },
      onwarn(warning, warn) {
        // 抑制 @vueuse/core 中 /* #__PURE__ */ 注释位置的警告（上游依赖问题，无法直接修复）
        if (warning.code === 'INVALID_ANNOTATION' || warning.message?.includes('#__PURE__')) return;
        warn(warning);
      },
    },
    chunkSizeWarningLimit: 1000,
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('src', import.meta.url)),
    },
  },
})
