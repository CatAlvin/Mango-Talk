<template>
  <div class="login-page">
    <div class="bg-orb bg-orb--orange"></div>
    <div class="bg-orb bg-orb--cyan"></div>
    <div class="bg-orb bg-orb--peach"></div>

    <div class="login-card">
      <div class="brand">
        <div class="brand-icon">
          <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="48" height="48" rx="14" fill="url(#brand-grad)" />
            <path d="M14 20c0-4.418 4.477-8 10-8s10 3.582 10 8-4.477 8-10 8c-1.29 0-2.527-.18-3.672-.51L16 30l1.176-3.53C15.42 24.87 14 22.56 14 20z" fill="#fff" fill-opacity=".92"/>
            <circle cx="20" cy="20" r="1.5" fill="#f97316"/>
            <circle cx="24" cy="20" r="1.5" fill="#06b6d4"/>
            <circle cx="28" cy="20" r="1.5" fill="#f97316"/>
            <defs>
              <linearGradient id="brand-grad" x1="0" y1="0" x2="48" y2="48">
                <stop stop-color="#fb923c"/>
                <stop offset="1" stop-color="#f97316"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <h1>Mango Talk</h1>
        <p class="brand-sub">让每一次交流，更轻松</p>
      </div>

      <form class="login-form" @submit.prevent="handleSubmit">
        <div class="form-item">
          <label for="identifier">{{ registering ? '用户名' : '用户名或手机号' }}</label>
          <div class="input-wrap">
            <svg class="input-icon" viewBox="0 0 20 20" fill="currentColor"><path d="M10 10a4 4 0 100-8 4 4 0 000 8zm-7 8a7 7 0 0114 0H3z"/></svg>
            <input
              id="identifier"
              v-model.trim="form.identifier"
              type="text"
              :placeholder="registering ? '3–32 个字符，不含空格' : '请输入用户名或手机号'"
              autocomplete="username"
              maxlength="32"
              required
            />
          </div>
        </div>

        <div class="form-item">
          <label for="password">密码</label>
          <div class="input-wrap">
            <svg class="input-icon" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd"/></svg>
            <input
              id="password"
              v-model="form.password"
              type="password"
              :placeholder="registering ? '设置密码，至少 6 个字符' : '请输入密码'"
              :autocomplete="registering ? 'new-password' : 'current-password'"
              maxlength="128"
              required
            />
          </div>
        </div>

        <div v-if="registering" class="form-item">
          <label for="confirm-password">确认密码</label>
          <div class="input-wrap">
            <input id="confirm-password" v-model="form.confirmPassword" class="plain-input" type="password" placeholder="再次输入密码" autocomplete="new-password" maxlength="128" required />
          </div>
        </div>

        <p v-if="errorMessage" class="error-text" role="alert">
          {{ errorMessage }}
        </p>

        <button class="submit-btn" type="submit" :disabled="authStore.loading || submitting">
          <span class="btn-text">{{ submitting || authStore.loading ? '请稍候…' : (registering ? '创建账号' : '登录') }}</span>
          <svg v-if="!authStore.loading" class="btn-arrow" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clip-rule="evenodd"/></svg>
        </button>
      </form>

      <p class="account-switch">{{ registering ? '已有账号？' : '第一次来？' }} <button type="button" :disabled="submitting || authStore.loading" @click="toggleRegister">{{ registering ? '登录' : '创建账号' }}</button></p>

      <div class="footer-tip">
        <button class="demo-entry" type="button" :disabled="submitting || authStore.loading" @click="handleDemo">进入演示空间 <span aria-hidden="true">↗</span></button>
        <p>从一段对话开始，认识 Mango Talk</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useRoomStore } from '../stores/room'
import { useMessageStore } from '../stores/message'
import http from '../lib/http'
import { errorText } from '../lib/api'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive({
  identifier: '',
  password: '',
  confirmPassword: '',
})

const errorMessage = ref('')
const registering = ref(false)
const submitting = ref(false)

function toggleRegister() { registering.value = !registering.value; errorMessage.value = ''; form.password = ''; form.confirmPassword = '' }
function handleDemo() {
  authStore.enterDemo()
  router.push('/demo')
}

async function handleSubmit() {
  if (submitting.value || authStore.loading) return
  if (!registering.value) return handleLogin()
  errorMessage.value = ''
  if (form.identifier.length < 3 || /\s/.test(form.identifier)) { errorMessage.value = '用户名至少需要 3 个字符，不能包含空格'; return }
  if (form.password.length < 6) { errorMessage.value = '密码至少需要 6 个字符'; return }
  if (form.password !== form.confirmPassword) { errorMessage.value = '两次输入的密码不一致'; return }
  submitting.value = true
  try {
    await http.post('/auth/register', { username: form.identifier, password: form.password })
    await authStore.login(form.identifier, form.password)
    useRoomStore().clearRooms(); useMessageStore().clearMessages()
    router.push('/chat')
  } catch (error) { errorMessage.value = errorText(error, '创建账号失败，请稍后重试') }
  finally { submitting.value = false }
}

async function handleLogin() {
  errorMessage.value = ''

  if (!form.identifier) {
    errorMessage.value = '请输入用户名或手机号'
    return
  }

  if (!form.password) {
    errorMessage.value = '请输入密码'
    return
  }

  try {
    await authStore.login(form.identifier, form.password)
    useRoomStore().clearRooms(); useMessageStore().clearMessages()
    router.push('/chat')
  } catch (error) {
    errorMessage.value =
      errorText(error, '登录失败，请稍后重试')
  }
}
</script>

<style scoped lang="scss">

.login-page {
  --c-orange: #f97316;
  --c-orange-light: #fed7aa;
  --c-cyan: #06b6d4;
  --c-cyan-light: #a5f3fc;
  --c-slate-900: #0f172a;
  --c-slate-700: #334155;
  --c-slate-500: #64748b;
  --c-slate-300: #cbd5e1;
  --c-slate-100: #f1f5f9;
  --c-danger: #ef4444;

  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0f172a;
  padding: 24px;
  position: relative;
  overflow: hidden;
  font-family: 'DM Sans', system-ui, sans-serif;
}

/* ---------- animated background orbs ---------- */
.bg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  opacity: 0.5;
  pointer-events: none;
  animation: float 18s ease-in-out infinite;

  &--orange {
    width: 520px;
    height: 520px;
    background: var(--c-orange);
    top: -10%;
    right: -5%;
    animation-delay: 0s;
  }

  &--cyan {
    width: 440px;
    height: 440px;
    background: var(--c-cyan);
    bottom: -12%;
    left: -8%;
    animation-delay: -6s;
  }

  &--peach {
    width: 300px;
    height: 300px;
    background: #fbbf24;
    top: 50%;
    left: 55%;
    opacity: 0.25;
    animation-delay: -12s;
  }
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -20px) scale(1.05); }
  66% { transform: translate(-20px, 15px) scale(0.95); }
}

/* ---------- card ---------- */
.login-card {
  position: relative;
  width: 100%;
  max-width: 430px;
  padding: 40px 36px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(40px) saturate(1.4);
  -webkit-backdrop-filter: blur(40px) saturate(1.4);
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow:
    0 24px 80px rgba(0, 0, 0, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
  animation: card-in 0.7s cubic-bezier(0.16, 1, 0.3, 1) both;
}

@keyframes card-in {
  from {
    opacity: 0;
    transform: translateY(32px) scale(0.96);
  }
}

/* ---------- brand ---------- */
.brand {
  text-align: center;
  margin-bottom: 32px;
}

.brand-icon {
  width: 56px;
  height: 56px;
  margin: 0 auto 16px;
  animation: icon-pop 0.6s 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) both;

  svg {
    width: 100%;
    height: 100%;
    filter: drop-shadow(0 4px 12px rgba(249, 115, 22, 0.35));
  }
}

@keyframes icon-pop {
  from {
    opacity: 0;
    transform: scale(0.5) rotate(-12deg);
  }
}

.brand h1 {
  margin: 0 0 6px;
  font-family: 'Outfit', sans-serif;
  font-size: 32px;
  font-weight: 800;
  background: linear-gradient(135deg, var(--c-orange) 30%, var(--c-cyan) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 0.02em;
}

.brand-sub {
  margin: 0;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.75);
  letter-spacing: 0.04em;
}

/* ---------- form ---------- */
.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 8px;

  label {
    font-size: 13px;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.8);
    letter-spacing: 0.03em;
    text-transform: uppercase;
  }
}

.input-wrap {
  position: relative;

  .input-icon {
    position: absolute;
    left: 14px;
    top: 50%;
    transform: translateY(-50%);
    width: 18px;
    height: 18px;
    color: rgba(255, 255, 255, 0.25);
    pointer-events: none;
    transition: color 0.25s;
  }

  input {
    width: 100%;
    height: 50px;
    padding: 0 16px 0 42px;
    border: 1.5px solid rgba(255, 255, 255, 0.1);
    border-radius: 14px;
    outline: none;
    font-family: inherit;
    font-size: 15px;
    color: #fff;
    background: rgba(255, 255, 255, 0.05);
    transition: border-color 0.25s, box-shadow 0.25s, background 0.25s;
    box-sizing: border-box;

    &::placeholder {
      color: rgba(255, 255, 255, 0.55);
    }

    &:focus {
      border-color: var(--c-orange);
      background: rgba(255, 255, 255, 0.08);
      box-shadow: 0 0 0 4px rgba(249, 115, 22, 0.15);
    }

    &:focus ~ .input-icon,
    &:focus + .input-icon {
      color: var(--c-orange);
    }
  }

  &:focus-within .input-icon {
    color: var(--c-orange);
  }
}

.error-text {
  margin: -4px 0 0;
  font-size: 13px;
  color: var(--c-danger);
  display: flex;
  align-items: center;
  gap: 6px;

  &::before {
    content: '⚠';
    font-size: 14px;
  }
}

/* ---------- submit button ---------- */
.submit-btn {
  height: 50px;
  border: none;
  border-radius: 14px;
  background: linear-gradient(135deg, var(--c-orange) 0%, #ea580c 100%);
  color: #fff;
  font-family: inherit;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: transform 0.2s, box-shadow 0.2s, opacity 0.2s;
  box-shadow: 0 4px 20px rgba(249, 115, 22, 0.3);

  &:hover:enabled {
    transform: translateY(-2px);
    box-shadow: 0 8px 28px rgba(249, 115, 22, 0.4);
  }

  &:active:enabled {
    transform: translateY(0);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.btn-arrow {
  width: 18px;
  height: 18px;
  transition: transform 0.25s;
}

.submit-btn:hover:enabled .btn-arrow {
  transform: translateX(4px);
}

/* ---------- footer ---------- */
.footer-tip {
  margin-top: 28px;
  text-align: center;
  padding-top: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);

  p {
    margin: 4px 0;
    font-size: 12px;
    color: rgba(255, 255, 255, 0.65);
    letter-spacing: 0.02em;
  }
}

/* ---------- responsive ---------- */
@media (max-width: 480px) {
  .login-page {
    padding: 16px;
  }

  .login-card {
    padding: 32px 24px;
    border-radius: 22px;
  }

  .brand h1 {
    font-size: 28px;
  }

  .brand-icon {
    width: 48px;
    height: 48px;
  }
}

@media (max-height: 640px) {
  .login-card {
    padding: 28px 28px;
  }

  .brand {
    margin-bottom: 20px;
  }

  .footer-tip {
    margin-top: 18px;
  }
}
</style>

<style scoped>
.account-switch { text-align: center; color: #cbd5e1; font-size: 13px; margin: 22px 0 0; }
.account-switch button { border: 0; background: transparent; color: #fdba74; cursor: pointer; padding: 5px; }
.demo-entry { color: #fff; border: 1px solid rgba(255,255,255,.25); width: 100%; border-radius: 12px; padding: 12px; background: rgba(255,255,255,.06); cursor: pointer; margin-bottom: 10px; }
.demo-entry:hover { background: rgba(255,255,255,.12); border-color: #22d3ee; }
.plain-input { padding-left: 16px !important; }
.brand h1 { background: none; color: #fff; -webkit-text-fill-color: #fff; }
.bg-orb { animation: none; opacity: .2; }
.login-page { overflow: clip; }
</style>
