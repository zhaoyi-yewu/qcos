<!--
  Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.

  qcos is licensed under Mulan PSL v2.
  You can use this software according to the terms and conditions
  of the Mulan PSL v2.
  You may obtain a copy of Mulan PSL v2 at:
          http://license.coscl.org.cn/MulanPSL2
  THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
      WITHOUT WARRANTIES OF ANY KIND,
  EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
  MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
  See the Mulan PSL v2 for more details.
-->

<template>
  <div class="login-container">
    <div v-if="checkingMode" class="loading-text">正在检查系统认证模式...</div>
    <el-form v-else ref="loginFormRef" :model="loginForm" :rules="loginRules" class="login-form" label-position="left" label-width="130px">

      <div class="title-container">
        <h3 class="title">WUYUEQbit量子计算操作系统 (QCOS)</h3>
        <p class="subtitle">请登录您的账户</p>
      </div>

      <!-- endpoint selector: label + dropdown with version/health status -->
      <el-form-item>
        <div class="endpoint-form-item">
          <div class="endpoint-label">
            <el-icon class="endpoint-label-icon"><Cpu /></el-icon>
            <span>量子计算操作系统</span>
          </div>
          <el-select
            v-model="selectedEndpoint"
            class="endpoint-select"
            :loading="probing"
            @change="onEndpointChange"
          >
            <template v-if="selectedEndpointStatus" #prefix>
              <span
                class="endpoint-state-dot"
                :class="'state-' + selectedEndpointStatus"
                :title="selectedEndpointStatus"
              />
            </template>
            <el-option
              v-for="ep in endpointOptions"
              :key="ep.name"
              :value="ep.name"
              :label="ep.alias || ep.name"
              :disabled="ep.usable === false"
              :title="ep.status === 'ok' ? `平台版本: ${ep.platformVersion}\n版本: ${ep.version}\n系统状态: 正常` : ep.status === 'fail' ? `错误: ${ep.error}` : '探测中…'"
              class="endpoint-option-item"
            >
              <div class="endpoint-option">
                <span
                  class="endpoint-state-dot"
                  :class="'state-' + (ep.status || 'probing')"
                  :title="ep.status || 'probing'"
                />
                <span class="endpoint-option-alias">{{ ep.alias || ep.name }}</span>
                <span class="endpoint-option-meta">
                  <template v-if="ep.status === 'probing'">
                    <el-icon class="is-loading"><Loading /></el-icon>
                  </template>
                  <template v-else-if="ep.status === 'ok'">
                    <span class="endpoint-option-version">v{{ ep.version }}</span>
                  </template>
                </span>
              </div>
            </el-option>
          </el-select>
        </div>
      </el-form-item>

      <el-form-item prop="username">
        <template #label>
          <span class="form-label-with-icon">
            <svg-icon icon-class="user" class="label-icon" />
            <span>用户名</span>
          </span>
        </template>
        <el-input
          ref="usernameRef"
          v-model="loginForm.username"
          :placeholder="authMode === 'no' ? 'anonymous' : '用户名'"
          name="username"
          type="text"
          tabindex="1"
          auto-complete="on"
          :disabled="authMode === 'no'"
        />
      </el-form-item>

      <el-form-item prop="password">
        <template #label>
          <span class="form-label-with-icon">
            <svg-icon icon-class="password" class="label-icon" />
            <span>密码</span>
          </span>
        </template>
        <el-input
          :key="passwordType"
          ref="passwordRef"
          v-model="loginForm.password"
          :type="passwordType"
          :placeholder="authMode === 'no' ? '无需密码' : '密码'"
          name="password"
          tabindex="2"
          auto-complete="on"
          :disabled="authMode === 'no'"
          @keyup.enter="handleLogin"
        />
        <span v-if="authMode !== 'no'" class="show-pwd" @click="showPwd">
          <svg-icon :icon-class="passwordType === 'password' ? 'eye' : 'eye-open'" />
        </span>
      </el-form-item>

      <el-button :loading="loading" type="primary" class="login-btn" :disabled="!endpointUsable" @click.prevent="handleLogin">
        {{ authMode === 'no' ? '直接登录' : '登 录' }}
      </el-button>

      <div class="tips">
        <span>认证模式: {{ authMode === 'no' ? '未开启认证' : authMode }}</span>
      </div>

      <div class="login-version-footer">QCOS管理界面版本: v{{ webuiVersion }}</div>
    </el-form>
  </div>
</template>

<script>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/store/modules/user'
import { useConfigStore } from '@/store/modules/config'
import { validUsername } from '@/utils/validate'
import { Loading, Cpu } from '@element-plus/icons-vue'
import { WEBUI_VERSION } from '@/version'

export default {
  name: 'LoginPage',
  components: { Loading, Cpu },
  setup() {
    const route = useRoute()
    const router = useRouter()
    const userStore = useUserStore()
    const cfg = useConfigStore()
    const loginFormRef = ref(null)
    const passwordRef = ref(null)
    const authMode = ref('jwt')
    const checkingMode = ref(true)
    const probing = ref(false)

    const validateUsername = (rule, value, callback) => {
      if (!validUsername(value)) {
        callback(new Error('请输入正确的用户名'))
      } else {
        callback()
      }
    }
    const validatePassword = (rule, value, callback) => {
      if (value.length < 6) {
        callback(new Error('密码不能少于6位'))
      } else {
        callback()
      }
    }

    const loginForm = reactive({
      username: '',
      password: ''
    })
    const loginRules = reactive({
      username: [{ required: true, trigger: 'blur', validator: validateUsername }],
      password: [{ required: true, trigger: 'blur', validator: validatePassword }]
    })
    const loading = ref(false)
    const passwordType = ref('password')
    const redirect = ref(undefined)

    // endpoint selection: defaults to active endpoint from config store,
    // or the value from ?endpoint=<name> query param when present
    const selectedEndpoint = ref(cfg.activeEndpointName)

    const endpointOptions = computed(() => cfg.endpoints.map(ep => {
      const h = cfg.healthMap[ep.name] || {}
      return {
        ...ep,
        status: h.status || 'probing',
        version: h.version || '',
        platformVersion: h.platformVersion || '',
        error: h.error || '',
        usable: h.status === 'ok'
      }
    }))

    const endpointUsable = computed(() => {
      return cfg.isEndpointUsable(selectedEndpoint.value)
    })

    // status of the currently selected endpoint, used to render the leading
    // status dot inside the select input (prefix slot); empty string when
    // nothing is selected or the endpoint has not been probed yet
    const selectedEndpointStatus = computed(() => {
      const h = cfg.healthMap[selectedEndpoint.value]
      return (h && h.status) || ''
    })

    watch(() => route, (newRoute) => {
      redirect.value = newRoute.query && newRoute.query.redirect
    }, { immediate: true })

    // apply ?endpoint=<name> from URL when present
    onMounted(() => {
      const epFromUrl = route.query.endpoint
      if (epFromUrl && cfg.endpoints.some(e => e.name === epFromUrl)) {
        cfg.setActive(epFromUrl)
        selectedEndpoint.value = epFromUrl
      }
      // probe all endpoints and then check auth mode for the active one
      probing.value = true
      cfg.probeAll().finally(() => {
        probing.value = false
      })
      checkAuthModeForActiveEndpoint()
    })

    function checkAuthModeForActiveEndpoint() {
      checkingMode.value = true
      userStore.checkAuthMode().then((mode) => {
        authMode.value = mode
        checkingMode.value = false
        if (mode === 'no') {
          loginForm.username = 'anonymous'
        } else {
          loginForm.username = 'admin'
        }
      }).catch(() => {
        checkingMode.value = false
        authMode.value = 'jwt'
        loginForm.username = 'admin'
      })
    }

    function onEndpointChange(name) {
      if (!cfg.isEndpointUsable(name)) {
        return
      }
      cfg.setActive(name)
      selectedEndpoint.value = name
      // clear credentials so the user does not mix accounts across endpoints
      loginForm.username = ''
      loginForm.password = ''
      checkAuthModeForActiveEndpoint()
    }

    function showPwd() {
      if (passwordType.value === 'password') {
        passwordType.value = 'text'
      } else {
        passwordType.value = 'password'
      }
    }

    function handleLogin() {
      if (!endpointUsable.value) {
        return
      }
      // In no-auth mode, skip form validation and login directly
      if (authMode.value === 'no') {
        loading.value = true
        userStore.noAuthLogin().then(() => {
          router.push({ path: redirect.value || '/' })
          loading.value = false
        }).catch(() => {
          loading.value = false
        })
        return
      }
      // In jwt mode, validate form then login
      loginFormRef.value.validate((valid) => {
        if (valid) {
          loading.value = true
          userStore.login(loginForm).then(() => {
            router.push({ path: redirect.value || '/' })
            loading.value = false
          }).catch(() => {
            loading.value = false
          })
        } else {
          console.log('error submit!!')
          return false
        }
      })
    }

    return {
      loginFormRef,
      passwordRef,
      loginForm,
      loginRules,
      loading,
      passwordType,
      redirect,
      authMode,
      checkingMode,
      probing,
      selectedEndpoint,
      endpointOptions,
      endpointUsable,
      selectedEndpointStatus,
      showPwd,
      onEndpointChange,
      handleLogin,
      webuiVersion: WEBUI_VERSION
    }
  }
}
</script>

<style lang="scss">
/* element-ui input overrides for login form */
$cursor: #333;

.loading-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: #fff;
  font-size: 1.2rem;
}

.login-container .el-input input {
  color: $cursor;
}

.login-container {
  .el-input {
    flex: 1;
    height: 47px;
    width: 100%;

    .el-input__wrapper {
      width: 100%;
      box-shadow: none !important;
      background: transparent !important;
    }

    input {
      background: transparent;
      border: 0px;
      -webkit-appearance: none;
      border-radius: 0px;
      padding: 12px 4px;
      color: $cursor;
      height: 47px;
      caret-color: $cursor;

      &:-webkit-autofill {
        box-shadow: 0 0 0px 1000px var(--el-fill-color-light) inset !important;
        -webkit-text-fill-color: $cursor !important;
      }
    }
  }

  .el-form-item {
    border: 1px solid var(--el-border-color);
    background: var(--el-fill-color-light);
    border-radius: 8px;
    color: #454545;
    display: flex;
    align-items: center;
  }

  .el-form-item__label {
    margin-left: 12px;
    padding-left: 0 !important;
    padding-right: 8px !important;
    text-align: left !important;
    justify-content: flex-start !important;
    color: #454545;
    font-weight: 500;
    box-sizing: border-box;
  }

  .el-form-item__content {
    width: 100%;
    display: flex;
    align-items: center;
    margin-left: 0 !important;
  }
}
</style>

<style lang="scss" scoped>
$bg: url('@/assets/background/login-bg.png') no-repeat center center / cover;
$dark_gray: #5a6a7a;
$light_gray: #333;

.login-container {
  min-height: 100%;
  width: 100%;
  background: $bg;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;

  .login-form {
    position: relative;
    width: 480px;
    max-width: 100%;
    padding: 50px 50px 30px;
    margin: 0 auto;
    overflow: hidden;
    background: rgba(255, 255, 255, 0.95);
    border-radius: 16px;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.25);
  }

  .tips {
    font-size: 13px;
    color: #888;
    margin-bottom: 10px;
    text-align: center;
    display: flex;
    justify-content: center;
    gap: 20px;
  }

  .login-version-footer {
    position: absolute;
    right: 14px;
    bottom: 8px;
    font-size: 12px;
    color: #909399;
    opacity: 0.85;
    pointer-events: none;
    user-select: none;
  }

  .form-label-with-icon {
    display: inline-flex;
    align-items: center;
    gap: 10px;

    .label-icon {
      width: 16px;
      height: 16px;
      color: $dark_gray;
    }
  }

  .title-container {
    position: relative;
    text-align: center;
    margin-bottom: 36px;

    .title {
      font-size: 24px;
      color: #1a2a6c;
      margin: 0 auto 8px auto;
      font-weight: bold;
      text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
    }

    .subtitle {
      font-size: 14px;
      color: #888;
      margin: 0;
    }
  }

  .login-btn {
    width: 100%;
    margin-bottom: 24px;
    height: 44px;
    font-size: 16px;
    border-radius: 8px;
  }

  .show-pwd {
    position: absolute;
    right: 10px;
    top: 7px;
    font-size: 16px;
    color: $dark_gray;
    cursor: pointer;
    user-select: none;
  }
}

/* endpoint selector inside the login form */
.endpoint-form-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: 0 !important;
}

.endpoint-label {
  font-size: 14px;
  font-weight: 500;
  color: #454545;
  white-space: nowrap;
  flex-shrink: 0;
  width: 130px;
  margin-left: 12px;
  padding-right: 8px;
  box-sizing: border-box;
  text-align: left;
  display: flex;
  justify-content: flex-start;
  align-items: center;
  gap: 6px;
}

.endpoint-label-icon {
  font-size: 16px;
  color: #454545;
}

.endpoint-select {
  flex: 1;
}

.endpoint-select :deep(.el-select__wrapper) {
  background: var(--el-fill-color-light) !important;
  box-shadow: none !important;
  border: 1px solid var(--el-border-color) !important;
  border-radius: 8px;
  padding-left: 12px;
  color: #454545;
}

.endpoint-select :deep(.el-select__wrapper:hover) {
  background: var(--el-fill-color-light) !important;
}

.endpoint-select :deep(.el-select__selected-item) {
  color: #454545;
}

.endpoint-option {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 8px;
}

.endpoint-option-alias {
  font-weight: 500;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.endpoint-option-meta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  margin-left: auto;
}

.endpoint-option-version {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

/* status dot: color reflects the endpoint health status */
.endpoint-state-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--el-color-info);
}

.endpoint-state-dot.state-ok {
  background: var(--el-color-success);
}

.endpoint-state-dot.state-fail {
  background: var(--el-color-danger);
}

.endpoint-state-dot.state-probing {
  background: var(--el-color-info);
}
</style>
