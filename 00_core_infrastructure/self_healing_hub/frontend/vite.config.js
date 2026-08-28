import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'


// https://vite.dev/config/
export default defineConfig({
  plugins: [react(),
    VitePWA({
      registerType: 'autoUpdate',
      devOptions: {
        enabled: true
      },
      includeAssets: ['assets/lauburu_symbol.png'],
      workbox: { maximumFileSizeToCacheInBytes: 5242880 },
      manifest: {
        name: 'Lauburu Swarm Mesh',
        short_name: 'Lauburu',
        description: 'Tri-Orchestrator AI Network & Custom IDE',
        theme_color: '#0f172a',
        background_color: '#0f172a',
        display: 'standalone',
        icons: [
          {
            src: '/assets/lauburu_symbol.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: '/assets/lauburu_symbol.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable'
          }
        ]
      }
    })],
  build: {
    sourcemap: true,
    minify: false
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    strictPort: true
  },
  preview: {
    host: '0.0.0.0',
    port: 3000,
    strictPort: true
  }
})
