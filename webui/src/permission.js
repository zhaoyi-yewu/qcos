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

import router from './router'
import { useUserStore } from './store/modules/user'
import { useConfigStore } from './store/modules/config'
import { ElMessage } from 'element-plus'
import NProgress from 'nprogress' // progress bar
import 'nprogress/nprogress.css' // progress bar style
import { getSession } from '@/utils/session'
import getPageTitle from '@/utils/get-page-title'

NProgress.configure({ showSpinner: false }) // NProgress Configuration

const whiteList = ['/login'] // no redirect whitelist

router.beforeEach(async(to, from, next) => {
  // start progress bar
  NProgress.start()

  // set page title
  document.title = getPageTitle(to.meta.title)

  // determine whether the user has logged in
  const cfg = useConfigStore()
  const sess = cfg.activeEndpointName ? getSession(cfg.activeEndpointName) : null
  const hasToken = !!(sess && sess.token)

  if (hasToken) {
    if (to.path === '/login') {
      // if is logged in, redirect to the home page
      next({ path: '/' })
      NProgress.done()
    } else {
      const userStore = useUserStore()
      // no-auth sessions (authMode === 'no' or token === 'no-auth') carry
      // a synthetic token that the backend does not recognize on /v1/auth/me,
      // so we must skip the getInfo round-trip and trust the locally stored
      // session payload (name/roles are already restored at app startup).
      const isNoAuthSession = sess.authMode === 'no' || sess.token === 'no-auth'
      if (isNoAuthSession) {
        next()
        return
      }
      const hasGetUserInfo = userStore.name
      if (hasGetUserInfo) {
        next()
      } else {
        try {
          // get user info
          await userStore.getInfo()

          next()
        } catch (error) {
          // remove token and go to login page to re-login
          await userStore.resetToken()
          ElMessage.error(error || 'Has Error')
          next(`/login?redirect=${to.path}`)
          NProgress.done()
        }
      }
    }
  } else {
    if (whiteList.indexOf(to.path) !== -1) {
      next()
    } else {
      next(`/login?redirect=${to.path}`)
      NProgress.done()
    }
  }
})

router.afterEach(() => {
  // finish progress bar
  NProgress.done()
})
