<template>
  <div class="login-wrapper">
    <div class="login-card">
      <div class="login-header">
        <div class="login-logo">🎬</div>
        <h2>ZuoSuo AI</h2>
        <p class="login-subtitle">{{ isRegister ? '创建新账号' : '登录到您的账号' }}</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        size="large"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" :prefix-icon="User" />
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

        <el-form-item v-if="isRegister" label="确认密码" prop="confirmPassword">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            show-password
            placeholder="请再次输入密码"
            :prefix-icon="Lock"
          />
        </el-form-item>

        <el-form-item v-if="isRegister" label="邮箱（可选）" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" :prefix-icon="Message" />
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
          {{ isRegister ? '注册' : '登录' }}
        </el-button>
      </el-form>

      <div class="login-footer">
        <span>{{ isRegister ? '已有账号？' : '没有账号？' }}</span>
        <el-button link type="primary" @click="toggleMode">
          {{ isRegister ? '去登录' : '立即注册' }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { User, Lock, Message } from '@element-plus/icons-vue'
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
const loading = ref(false)
const errorMsg = ref('')
const formRef = ref<any>(null)

const form = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  email: '',
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度在 3-50 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 128, message: '密码长度至少 6 个字符', trigger: 'blur' },
  ],
  confirmPassword: [
    {
      validator: (_rule: any, value: string, callback: Function) => {
        if (isRegister.value && value !== form.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
  email: [
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' },
  ],
}

function toggleMode() {
  isRegister.value = !isRegister.value
  errorMsg.value = ''
}

async function handleSubmit() {
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
    if (isRegister.value) {
      await auth.register(form.username, form.password, form.email || undefined)
      ElMessage.success('注册成功！')
    } else {
      await auth.login(form.username, form.password)
      ElMessage.success('登录成功！')
    }
    emit('login-success')
  } catch (e: any) {
    errorMsg.value = e.message || '操作失败，请重试'
  } finally {
    loading.value = false
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
</style>
