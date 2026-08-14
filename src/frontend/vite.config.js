import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // 加载 .env 文件（从项目根目录）
  const env = loadEnv(mode, process.cwd(), '')

  const apiPort = env.API_PORT || '8000'
  const apiTarget = `http://localhost:${apiPort}`

  return {
    plugins: [react()],
    server: {
      port: parseInt(env.FRONTEND_PORT || '15173', 10),
      proxy: {
        '/chat': { target: apiTarget, changeOrigin: true },
        '/chat/stream': { target: apiTarget, changeOrigin: true },
        '/models': { target: apiTarget, changeOrigin: true },
        '/stats': { target: apiTarget, changeOrigin: true },
        '/entities': { target: apiTarget, changeOrigin: true },
        '/entity': { target: apiTarget, changeOrigin: true },
        '/path': { target: apiTarget, changeOrigin: true },
        '/search': { target: apiTarget, changeOrigin: true },
        '/vector_search': { target: apiTarget, changeOrigin: true },
        '/graph': { target: apiTarget, changeOrigin: true },
        '/eval': { target: apiTarget, changeOrigin: true },
        '/health': { target: apiTarget, changeOrigin: true },
        '/reference': { target: apiTarget, changeOrigin: true },
        '/sql': { target: apiTarget, changeOrigin: true },
      }
    }
  }
})
