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

import axios from 'axios'
import { ElMessageBox as MessageBox, ElMessage as Message } from 'element-plus'
import { useUserStore } from '@/store/modules/user'
import { useConfigStore } from '@/store/modules/config'
import { getSession, removeSession } from '@/utils/session'

// create an axios instance
const service = axios.create({
  // baseURL is intentionally left empty; the full URL is constructed
  // by jsonrpc.js / httpRequest using the active endpoint's url.
  baseURL: '',
  // withCredentials: true, // send cookies when cross-domain requests
  timeout: 5000 // request timeout
})

// request interceptor
service.interceptors.request.use(
  config => {
    // do something before request is sent

    const cfg = useConfigStore()
    const sess = cfg.activeEndpointName ? getSession(cfg.activeEndpointName) : null
    if (sess && sess.token) {
      // attach JWT token in Authorization header
      // (QCOS backend uses Bearer token auth)
      config.headers['Authorization'] = `Bearer ${sess.token}`
    }
    return config
  },
  error => {
    // do something with request error
    console.log(error) // for debug
    return Promise.reject(error)
  }
)

// response interceptor
service.interceptors.response.use(
  /**
   * If you want to get http information such as headers or status
   * Please return  response => response
   */

  /**
   * Determine the request status by custom code
   * Here is just an example
   * You can also judge the status by HTTP Status Code
   */
  response => {
    const status = response.status
    if (status !== 200) {
      return Promise.reject(new Error('Error: http status != 200'))
    }
    const res = response.data
    // if the custom code is not 20000, it is judged as an error.
    if (res.error) {
      // build a human-readable error message; JSON-RPC errors may omit
      // `data` or `data.details` entirely (e.g. validation errors), so
      // fall back to just the message field instead of throwing
      // TypeError when accessing a property of undefined
      const baseMsg = (res.error && res.error.message) || 'Error'
      const detailMsg = res.error && res.error.data && res.error.data.details
      const err_msg = detailMsg ? `${baseMsg}: ${detailMsg}` : baseMsg
      Message({
        message: err_msg || 'Error',
        type: 'error',
        duration: 5 * 1000
      })

      // 50008: Illegal token; 50012: Other clients logged in; 50014: Token expired;
      if (res.code === 50008 || res.code === 50012 || res.code === 50014) {
        // to re-login
        MessageBox.confirm('You have been logged out, you can cancel to stay on this page, or log in again', 'Confirm logout', {
          confirmButtonText: 'Re-Login',
          cancelButtonText: 'Cancel',
          type: 'warning'
        }).then(() => {
          const cfg = useConfigStore()
          removeSession(cfg.activeEndpointName)
          const userStore = useUserStore()
          userStore.resetToken().then(() => {
            location.reload()
          })
        })
      }
      return Promise.reject(new Error(err_msg || 'Error'))
    } else {
      return res
    }
  },
  error => {
    console.log('err' + error) // for debug
    Message({
      message: error.message,
      type: 'error',
      duration: 5 * 1000
    })
    return Promise.reject(error)
  }
)

export default service
