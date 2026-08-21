import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // 加载 .env 文件（从项目根目录，即本文件的上级上级）
  const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
  const env = loadEnv(mode, projectRoot, '')

  const apiPort = env.API_PORT || '8000'
  // 代理目标主机可配置（API_HOST），不再写死 localhost——后端部署在其它机器时开发代理也能指过去
  const apiHost = env.API_HOST || 'localhost'
  const apiTarget = `http://${apiHost}:${apiPort}`

  return {
    plugins: [react()],
    // 将后端 API_TOKEN 注入前端（__API_TOKEN__ 供 main.jsx 统一加 Authorization 头）
    define: {
      __API_TOKEN__: JSON.stringify(env.API_TOKEN || ''),
    },
    server: {
      port: parseInt(env.FRONTEND_PORT || '15173', 10),
      // proxy 仅开发模式生效。生产环境由 FastAPI 同源托管 dist/（见 start.sh），
      // 前端统一用相对路径（/chat、/stats 等）请求，无需代理也不会 404。
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
        '/report': { target: apiTarget, changeOrigin: true },
        '/import': { target: apiTarget, changeOrigin: true },
      }
    }
  }
})
