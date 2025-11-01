import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

const API_TARGET = 'http://127.0.0.1:8000';

export default defineConfig({
  plugins: [react()],
  root: '.',
  base: '/',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    proxy: {
      '/status': API_TARGET,
      '/candles': API_TARGET,
      '/equity': API_TARGET,
      '/bot_trades': API_TARGET,
      '/orderbook': API_TARGET,
      '/market_metrics': API_TARGET,
      '/config': {
        target: API_TARGET,
        changeOrigin: true,
      },
    },
  },
});
