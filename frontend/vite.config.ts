import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

export default defineConfig({
  plugins: [react()],
  envDir: path.resolve(__dirname, '..'),
  resolve: { alias: { '@': path.resolve(__dirname, '.') } },
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api/v1': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  preview: { host: '0.0.0.0', port: 3000 },
});
