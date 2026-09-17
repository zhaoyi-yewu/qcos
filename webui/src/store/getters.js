/**
 * Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
 *
 * qcos is licensed under Mulan PSL v2.
 * You can use this software according to the terms and conditions
 * of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *         http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
 *     WARRANTIES OF ANY KIND,
 * EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
 * MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
 * See the Mulan PSL v2 for more details.
 */

import { useAppStore } from './modules/app'
import { useUserStore } from './modules/user'

export function getSidebar() {
  const appStore = useAppStore()
  return appStore.sidebar
}

export function getDevice() {
  const appStore = useAppStore()
  return appStore.device
}

export function getToken() {
  const userStore = useUserStore()
  return userStore.token
}

export function getAvatar() {
  const userStore = useUserStore()
  return userStore.avatar
}

export function getName() {
  const userStore = useUserStore()
  return userStore.name
}
