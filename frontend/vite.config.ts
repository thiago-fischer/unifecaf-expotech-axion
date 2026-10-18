import react from '@vitejs/plugin-react';
import { loadEnv } from 'vite';
import { defineConfig } from 'vitest/config';

export default defineConfig(({ mode }) => {
  const env = { ...loadEnv(mode, process.cwd(), ''), ...process.env };
  const proxy = {
    '/api': {
      target: env.AXION_API_TARGET || 'http://127.0.0.1:8000',
      changeOrigin: true,
      rewrite: (path: string) => path.replace(/^\/api/, ''),
      timeout: 60_000,
      proxyTimeout: 60_000,
    },
  };
  return {
    plugins: [react()],
    server: { port: 5173, strictPort: true, proxy },
    preview: { port: 4173, strictPort: true, proxy },
    test: {
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
      include: ['src/**/*.test.{ts,tsx}'],
    },
  };
});
