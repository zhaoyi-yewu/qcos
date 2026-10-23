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

import { createApp } from 'vue'

import 'normalize.css/normalize.css' // A modern alternative to CSS resets

import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
// dark mode CSS variables: activates when <html> has the `dark` class.
// element-plus remaps all --el-* variables under html.dark, so toggling
// the class is enough to switch the whole UI between light and dark.
import 'element-plus/theme-chalk/dark/css-vars.css'
import locale from 'element-plus/es/locale/lang/zh-cn' // lang i18n

import '@/styles/index.scss' // global css
import '@/styles/font.css'

import App from './App'
import router from './router'
import { createPinia } from 'pinia'

import icons from '@/icons' // icon
import '@/permission' // permission control
import { useSettingsStore } from '@/store/modules/settings'
import { useConfigStore } from '@/store/modules/config'
import { useUserStore } from '@/store/modules/user'

async function bootstrap() {
  const app = createApp(App)

  app.use(icons)

  // set ElementPlus lang to EN
  app.use(ElementPlus, { locale })

  const pinia = createPinia()
  app.use(pinia)

  // apply the user's persisted Element Plus theme before mount so the very
  // first paint already uses the chosen primary color (avoids a visible
  // flash of the default blue when a non-default theme was saved)
  const settingsStore = useSettingsStore(pinia)
  settingsStore.initTheme()

  // load runtime config (endpoints, debug, etc.) before mounting so all
  // API requests can resolve the active endpoint URL
  const cfg = useConfigStore(pinia)
  await cfg.load()

  // restore session for the active endpoint from localStorage
  const userStore = useUserStore(pinia)
  userStore.loadSessionForActiveEndpoint()

  // probe all endpoints in the background; results are written to healthMap
  // and consumed by the login page / sidebar dropdowns
  cfg.probeAll()

  // NOTE: install the router ONLY AFTER cfg.load() and the session restore.
  // app.use(router) triggers the initial navigation immediately, which runs
  // the global beforeEach guard in permission.js. If the router is installed
  // earlier, the guard would see cfg.activeEndpointName === '' and conclude
  // "no session" -> redirect to /login, even though a valid session exists.
  app.use(router)

  app.mount('#app')
}

bootstrap()
