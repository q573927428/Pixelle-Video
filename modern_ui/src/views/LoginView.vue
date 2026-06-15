<template>
  <div class="login-wrapper">
    <div class="login-card">
      <div class="login-header">
        <div class="login-logo">🎬</div>
        <h2>ZuoSuo AI</h2>
        <p class="login-subtitle">{{ isRegister ? '手机号快速注册' : '登录到您的账号' }}</p>
      </div>

      <!-- ====== 登录表单 ====== -->
      <el-form
        v-if="!isRegister"
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        size="large"
        @submit.prevent="handleLogin"
      >
        <el-form-item label="账号 / 手机号" prop="account">
          <el-input v-model="form.account" placeholder="请输入用户名或手机号" :prefix-icon="User" />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="请输入密码"
            :prefix-icon="Lock"
          />
        </el-form-item>

        <el-alert
          v-if="errorMsg"
          :title="errorMsg"
          type="error"
          show-icon
          :closable="true"
          @close="errorMsg = ''"
          style="margin-bottom: 16px;"
        />

        <el-button
          type="primary"
          native-type="submit"
          :loading="loading"
          style="width: 100%; height: 48px; font-size: 16px;"
        >
          登录
        </el-button>
      </el-form>

      <!-- ====== 手机号注册表单 ====== -->
      <el-form
        v-if="isRegister"
        ref="phoneFormRef"
        :model="phoneForm"
        :rules="phoneRules"
        label-position="top"
        size="large"
        @submit.prevent="handlePhoneRegister"
      >
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="phoneForm.phone" placeholder="请输入手机号" :prefix-icon="Iphone" maxlength="11" />
        </el-form-item>

        <el-form-item label="验证码" prop="code">
          <div class="sms-code-row">
            <el-input v-model="phoneForm.code" placeholder="请输入验证码" maxlength="6" style="flex: 1;" />
            <el-button
              :disabled="countdown > 0 || !phoneForm.phone"
              :loading="sendingCode"
              @click="handleSendCode"
              style="width: 140px; margin-left: 12px; flex-shrink: 0;"
            >
              {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
            </el-button>
          </div>
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="phoneForm.password"
            type="password"
            show-password
            placeholder="请设置密码（至少6位）"
            :prefix-icon="Lock"
          />
        </el-form-item>

        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="phoneForm.confirmPassword"
            type="password"
            show-password
            placeholder="请再次输入密码"
            :prefix-icon="Lock"
          />
        </el-form-item>

        <el-alert
          v-if="phoneErrorMsg"
          :title="phoneErrorMsg"
          type="error"
          show-icon
          :closable="true"
          @close="phoneErrorMsg = ''"
          style="margin-bottom: 16px;"
        />

        <el-button
          type="primary"
          native-type="submit"
          :loading="phoneLoading"
          style="width: 100%; height: 48px; font-size: 16px;"
        >
          注册
        </el-button>
      </el-form>

      <div class="login-footer">
        <span>{{ isRegister ? '已有账号？' : '没有账号？' }}</span>
        <el-button link type="primary" @click="toggleMode">
          {{ isRegister ? '去登录' : '手机号注册' }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { User, Lock, Iphone } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getAuth } from '../composables/useAuth'

const props = withDefaults(defineProps<{
  startRegister?: boolean
}>(), {
  startRegister: false,
})

const emit = defineEmits<{
  (e: 'login-success'): void
}>()

const isRegister = ref(props.startRegister)

// 登录表单
const loading = ref(false)
const errorMsg = ref('')
const formRef = ref<any>(null)

const form = reactive({
  account: '',
  password: '',
})

const rules = {
  account: [
    { required: true, message: '请输入用户名或手机号', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
  ],
}

// 手机号注册表单
const phoneLoading = ref(false)
const sendingCode = ref(false)
const phoneErrorMsg = ref('')
const countdown = ref(0)
let countdownTimer: ReturnType<typeof setInterval> | null = null
const phoneFormRef = ref<any>(null)

const phoneForm = reactive({
  phone: '',
  code: '',
  password: '',
  confirmPassword: '',
})

const phoneRules = {
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号格式', trigger: 'blur' },
  ],
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { min: 6, max: 6, message: '验证码为6位数字', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 128, message: '密码长度至少 6 个字符', trigger: 'blur' },
  ],
  confirmPassword: [
    {
      validator: (_rule: any, value: string, callback: Function) => {
        if (value !== phoneForm.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}

function toggleMode() {
  isRegister.value = !isRegister.value
  errorMsg.value = ''
  phoneErrorMsg.value = ''
}

async function handleLogin() {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
  } catch {
    return
  }

  loading.value = true
  errorMsg.value = ''

  try {
    const auth = getAuth()
    const account = form.account.trim()

    // 判断输入的是手机号还是用户名
    if (/^1[3-9]\d{9}$/.test(account)) {
      // 手机号登录
      await auth.loginByPhone(account, form.password)
    } else {
      // 用户名登录
      await auth.login(account, form.password)
    }

    ElMessage.success('登录成功！')
    emit('login-success')
  } catch (e: any) {
    errorMsg.value = e.message || '登录失败，请重试'
  } finally {
    loading.value = false
  }
}

async function handleSendCode() {
  const phone = phoneForm.phone
  if (!/^1[3-9]\d{9}$/.test(phone)) {
    phoneErrorMsg.value = '请输入正确的手机号'
    return
  }

  sendingCode.value = true
  phoneErrorMsg.value = ''
  try {
    const auth = getAuth()
    await auth.sendSmsCode(phone)
    ElMessage.success('验证码已发送')
    // 开始 60 秒倒计时
    countdown.value = 60
    if (countdownTimer) clearInterval(countdownTimer)
    countdownTimer = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) {
        if (countdownTimer) clearInterval(countdownTimer)
        countdownTimer = null
      }
    }, 1000)
  } catch (e: any) {
    phoneErrorMsg.value = e.message || '发送失败，请重试'
  } finally {
    sendingCode.value = false
  }
}

async function handlePhoneRegister() {
  if (!phoneFormRef.value) return

  try {
    await phoneFormRef.value.validate()
  } catch {
    return
  }

  phoneLoading.value = true
  phoneErrorMsg.value = ''

  try {
    const auth = getAuth()
    await auth.registerByPhone(phoneForm.phone, phoneForm.code, phoneForm.password)
    ElMessage.success('注册成功！')
    emit('login-success')
  } catch (e: any) {
    phoneErrorMsg.value = e.message || '注册失败，请重试'
  } finally {
    phoneLoading.value = false
  }
}
</script>

<style scoped>
.login-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
}

.login-card {
  width: 420px;
  padding: 40px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  backdrop-filter: blur(20px);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-logo {
  font-size: 48px;
  margin-bottom: 12px;
}

.login-header h2 {
  color: #fff;
  font-size: 24px;
  margin: 0 0 8px;
}

.login-subtitle {
  color: rgba(255, 255, 255, 0.6);
  font-size: 14px;
  margin: 0;
}

.login-footer {
  text-align: center;
  margin-top: 24px;
  color: rgba(255, 255, 255, 0.5);
  font-size: 14px;
}

.sms-code-row {
  display: flex;
  align-items: center;
  width: 100%;
}
</style>