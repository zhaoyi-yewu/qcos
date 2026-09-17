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

import { login, logout, getInfo } from '@/api/user'
import { getToken, setToken, removeToken } from '@/utils/auth'
import { resetRouter } from '@/router'
import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: getToken(),
    name: '',
    avatar: ''
  }),
  actions: {
    // user login
    login(userInfo) {
      const { username, password } = userInfo
      return new Promise((resolve, reject) => {
        login({ username: username.trim(), password: password })
          .then(response => {
            const { data } = response
            this.token = data.token
            setToken(data.token)
            resolve()
          })
          .catch(error => {
            reject(error)
          })
      })
    },

    // get user info
    getInfo() {
      return new Promise((resolve, reject) => {
        getInfo(this.token)
          .then(response => {
            const { data } = response

            if (!data) {
              return reject('Verification failed, please Login again.')
            }

            const { name, avatar } = data

            this.name = name
            this.avatar = avatar
            resolve(data)
          })
          .catch(error => {
            reject(error)
          })
      })
    },

    // user logout
    logout() {
      return new Promise((resolve, reject) => {
        logout(this.token)
          .then(() => {
            removeToken() // must remove token first
            resetRouter()
            this.token = ''
            this.name = ''
            this.avatar = ''
            resolve()
          })
          .catch(error => {
            reject(error)
          })
      })
    },

    // remove token
    resetToken() {
      return new Promise(resolve => {
        removeToken() // must remove token first
        this.token = ''
        this.name = ''
        this.avatar = ''
        resolve()
      })
    }
  }
})
