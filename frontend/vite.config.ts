import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { loadEnv } from 'vite'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const projectRoot = resolve(frontendRoot, '..')

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, projectRoot, '')
  const frontendPort = Number(env.FRONTEND_PORT || '5173')
  const backendPort = Number(env.BACKEND_PORT || '8000')

  return {
    plugins: [react()],
    server: {
      port: frontendPort,
      proxy: {
        '/api': `http://localhost:${backendPort}`,
      },
    },
  }
})
