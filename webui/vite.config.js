/**
 * Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
 *
 * qcos is licensed under Mulan PSL v2.
 * You can use this software according to the terms and conditions
 * of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *         http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
 *     WITHOUT WARRANTIES OF ANY KIND,
 * EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
 * MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
 * See the Mulan PSL v2 for more details.
 */

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import fs from 'fs'
import http from 'http'
import https from 'https'
import { createSvgIconsPlugin } from 'vite-plugin-svg-icons'

/**
 * Dev-server middleware: serve /webui-config.json and /api/<name>/ proxies
 * from the same qcos-webui.toml used in production.
 *
 * Default TOML path: /etc/qcos/qcos-webui.toml (override with WEBUI_TOML).
 * If the file is missing the dev server exits with a clear error so the
 * developer knows to create it first.
 */
function webuiConfigPlugin() {
  const tomlPath = process.env.WEBUI_TOML || '/etc/qcos/qcos-webui.toml'

  if (!fs.existsSync(tomlPath)) {
    console.error(`\n[vite] ERROR: qcos-webui.toml not found at: ${tomlPath}`)
    console.error('[vite] Please create it first, e.g.:')
    console.error('  sudo mkdir -p /etc/qcos')
    console.error('  sudo cp etc/qcos/qcos-webui.toml /etc/qcos/qcos-webui.toml')
    console.error('  sudo vim /etc/qcos/qcos-webui.toml\n')
    process.exit(1)
  }

  // lazy-load tomllib (Node 18+ has no built-in TOML parser; we use a
  // lightweight regex-based extraction for the fields we need)
  function parseToml() {
    const content = fs.readFileSync(tomlPath, 'utf-8')
    const getValue = (key) => {
      const m = content.match(new RegExp(`^${key}\\s*=\\s*(.+)$`, 'm'))
      return m ? m[1].trim() : null
    }
    const debug = getValue('DEBUG') === 'true'
    const defaultEndpoint = (getValue('DEFAULT_ENDPOINT') || '').replace(/"/g, '') || ''
    const probeTimeout = parseInt((getValue('ENDPOINT_PROBE_TIMEOUT_MS') || '3000'), 10)

    // parse QCOS_API_ENDPOINTS array
    // Strip TOML comments first so commented-out examples are not matched
    const stripped = content.replace(/^#.*$/gm, '')
    const endpoints = []
    const epRegex = /\{\s*name\s*=\s*"([^"]+)"[^}]*\}/g
    let match
    while ((match = epRegex.exec(stripped)) !== null) {
      const block = match[0]
      const name = match[1]
      const alias = (block.match(/alias\s*=\s*"([^"]*)"/) || [null, name])[1]
      const url = (block.match(/url\s*=\s*"([^"]*)"/) || [null, ''])[1]
      const useSsl = /use_ssl\s*=\s*true/i.test(block)
      const prometheusUrl = (block.match(/prometheus_url\s*=\s*"([^"]*)"/) || [null, ''])[1]
      const alertmanagerUrl = (block.match(/alertmanager_url\s*=\s*"([^"]*)"/) || [null, ''])[1]
      const ep = { name, alias, url, use_ssl: useSsl }
      if (prometheusUrl) ep.prometheus_url = prometheusUrl.replace(/\/$/, '')
      if (alertmanagerUrl) ep.alertmanager_url = alertmanagerUrl.replace(/\/$/, '')
      endpoints.push(ep)
    }

    return { debug, defaultEndpoint, endpointProbeTimeoutMs: probeTimeout, endpoints }
  }

  return {
    name: 'webui-config',

    // The `config` hook runs BEFORE the dev server is created, which
    // lets us register per-endpoint proxy entries in `server.proxy`
    // (powered by http-proxy-middleware). Doing it here ensures vite's
    // built-in proxy middleware is initialised with our rules; mutating
    // `server.config.server.proxy` later inside `configureServer` would
    // be too late and the proxies would not take effect.
    //
    // Each endpoint produces a `/api/<name>` proxy entry. The `rewrite`
    // strips the `/api/<name>` prefix so the upstream receives the bare
    // path (e.g. `/v1/proxy/prometheus/...`), matching what nginx's
    // `proxy_pass <url>/` does in production.
    config() {
      const cfg = parseToml()
      const proxy = {}
      for (const ep of cfg.endpoints) {
        const targetUrl = ep.url.replace(/\/$/, '')
        proxy[`/api/${ep.name}`] = {
          target: targetUrl,
          changeOrigin: true,
          // forward WebSocket upgrades (e.g. /api/<name>/v1/terminal/ws)
          // so the dev-mode terminal works the same as behind nginx
          ws: true,
          rewrite: (p) => p.replace(new RegExp(`^/api/${ep.name}`), '')
        }
      }
      return {
        server: { proxy }
      }
    },

    configureServer(server) {
      // serve /webui-config.json
      server.middlewares.use('/webui-config.json', (req, res) => {
        try {
          const cfg = parseToml()
          const payload = {
            debug: cfg.debug,
            defaultEndpoint: cfg.defaultEndpoint,
            endpointProbeTimeoutMs: cfg.endpointProbeTimeoutMs,
            endpoints: cfg.endpoints.map(ep => {
              const entry = {
                name: ep.name,
                alias: ep.alias,
                url: `/api/${ep.name}`,
                use_ssl: ep.use_ssl
              }
              if (ep.prometheus_url) entry.prometheus_url = ep.prometheus_url
              if (ep.alertmanager_url) entry.alertmanager_url = ep.alertmanager_url
              return entry
            })
          }
          res.setHeader('Content-Type', 'application/json')
          res.setHeader('Cache-Control', 'no-store')
          res.end(JSON.stringify(payload))
        } catch (err) {
          res.statusCode = 500
          res.end(JSON.stringify({ error: err.message }))
        }
      })
    }
  }
}

export default defineConfig(({ mode, command }) => {
  const env = loadEnv(mode, process.cwd(), '')

  // webuiConfigPlugin reads /etc/qcos/qcos-webui.toml and exposes
  // /webui-config.json + /api/<name>/ proxies via the dev-server middleware.
  // It must NOT run during `vite build` (e.g. inside a Docker builder where
  // /etc/qcos does not exist); only enable it for the dev server.
  const isDev = command === 'serve'

  return {
    plugins: [
      vue(),
      createSvgIconsPlugin({
        iconDirs: [path.resolve(process.cwd(), 'src/icons/svg')],
        symbolId: 'icon-[name]'
      }),
      ...(isDev ? [webuiConfigPlugin()] : [])
    ],
    resolve: {
      extensions: ['.mjs', '.js', '.mts', '.ts', '.jsx', '.tsx', '.json', '.vue'],
      alias: {
        '@': path.resolve(__dirname, 'src'),
        // Patch findSectionHeaders.js to remove RegExp 'd' (hasIndices) flag
        // not supported by older MS Edge browsers
        'monaco-editor/esm/vs/editor/common/services/findSectionHeaders': path.resolve(__dirname, 'patches/findSectionHeaders.js')
      }
    },
    optimizeDeps: {
      esbuildOptions: {
        // Patch findSectionHeaders.js in pre-bundled deps as well
        alias: {
          'monaco-editor/esm/vs/editor/common/services/findSectionHeaders': path.resolve(__dirname, 'patches/findSectionHeaders.js')
        }
      }
    },
    server: {
      port: process.env.WEBUI_LISTEN_PORT || 18401,
      host: process.env.WEBUI_LISTEN_IP || 'localhost',
      open: process.env.WEBUI_OPEN_BROWSER === 'true',
      proxy: {
        '/dev-api': {
          target: 'http://127.0.0.1:18400',
          changeOrigin: true,
          pathRewrite: { '^/dev-api': '' }
        }
      }
    },
    build: {
      outDir: 'dist',
      assetsDir: 'static',
      sourcemap: false,
      chunkSizeWarningLimit: 5000,
      rollupOptions: {
        output: {
          manualChunks: {
            'element-plus': ['element-plus', '@element-plus/icons-vue'],
            echarts: ['echarts'],
            'monaco-editor': ['monaco-editor/esm/vs/editor/editor.api']
          }
        }
      }
    },
    css: {
      preprocessorOptions: {
        scss: {
          // Global SCSS variables are imported per-file via @use,
          // see src/styles/variables.scss for variable definitions
        }
      }
    }
  }
})
