import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [],
  build: {
    lib: {
      entry: 'main.js',
      formats: ['es']
    },
    rollupOptions: {
      output: {
        manualChunks: true
      }
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/chat': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
});
