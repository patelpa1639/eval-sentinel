import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Build output -> web/ui/dist (relative to this config = ui/dist).
// Dev proxy: /api/* -> http://localhost:8000 (the backend, same-origin in prod).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
});
