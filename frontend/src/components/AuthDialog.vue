<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-card card">
      <div class="modal-head">
        <span class="modal-title">{{ mode === 'signin' ? '🌸 登录' : '🌸 注册' }}</span>
        <button class="modal-close" @click="$emit('close')">✕</button>
      </div>

      <div class="modal-body">
        <p class="intro">
          {{ mode === 'signin'
            ? '用邮箱 + 密码登录，发布到「像素画廊」并管理自己的作品。'
            : '注册一个账号，发布的作品会跟你绑定，换设备登录还能继续管理。' }}
        </p>

        <div class="tabs">
          <button class="tab" :class="{ on: mode === 'signin' }"
                  @click="mode = 'signin'">登录</button>
          <button class="tab" :class="{ on: mode === 'signup' }"
                  @click="mode = 'signup'">注册</button>
        </div>

        <label class="row">
          <span class="lbl">邮箱</span>
          <input type="email" v-model="email" class="input"
                 autocomplete="email"
                 placeholder="you@example.com"
                 @keydown.enter="onSubmit" />
        </label>
        <label class="row">
          <span class="lbl">密码</span>
          <input type="password" v-model="password" class="input"
                 :autocomplete="mode === 'signup' ? 'new-password' : 'current-password'"
                 placeholder="至少 6 位"
                 @keydown.enter="onSubmit" />
        </label>

        <div v-if="info" class="info-bar">{{ info }}</div>
        <div v-if="errorMsg" class="error-bar">⚠ {{ errorMsg }}</div>

        <button class="btn btn-primary submit-btn" :disabled="busy" @click="onSubmit">
          {{ busy ? '处理中…' : (mode === 'signin' ? '登录' : '注册') }}
        </button>

        <div v-if="mode === 'signin'" class="forgot">
          <a href="#" @click.prevent="onForgot">忘记密码？</a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuth } from '../composables/useAuth'

const emit = defineEmits<{ close: [] }>()
const { signIn, signUp, resetPassword } = useAuth()

const mode = ref<'signin' | 'signup'>('signin')
const email = ref('')
const password = ref('')
const busy = ref(false)
const info = ref('')
const errorMsg = ref('')

async function onSubmit() {
  if (busy.value) return
  errorMsg.value = ''
  info.value = ''
  if (!email.value.includes('@')) { errorMsg.value = '请填写有效的邮箱'; return }
  if (password.value.length < 6) { errorMsg.value = '密码至少 6 位'; return }
  busy.value = true
  try {
    if (mode.value === 'signin') {
      await signIn(email.value.trim(), password.value)
      emit('close')
    } else {
      const r = await signUp(email.value.trim(), password.value)
      if (r.needsEmailConfirmation) {
        info.value = '注册成功！请到你的邮箱里点确认链接，确认后回来登录。'
      } else {
        emit('close')
      }
    }
  } catch (e: any) {
    errorMsg.value = mapAuthError(e?.message || String(e))
  } finally {
    busy.value = false
  }
}

async function onForgot() {
  if (!email.value.includes('@')) {
    errorMsg.value = '先在上面填上要重设密码的邮箱'
    return
  }
  busy.value = true
  errorMsg.value = ''
  try {
    await resetPassword(email.value.trim())
    info.value = '重设密码的邮件已发送，去邮箱看一下。'
  } catch (e: any) {
    errorMsg.value = e?.message || String(e)
  } finally {
    busy.value = false
  }
}

function mapAuthError(msg: string): string {
  const m = msg.toLowerCase()
  if (m.includes('invalid login')) return '邮箱或密码不对'
  if (m.includes('email not confirmed')) return '邮箱还没确认，去收件箱点链接'
  if (m.includes('already registered')) return '这个邮箱已经注册过了，换登录吧'
  if (m.includes('rate limit')) return '请求太频繁，等一分钟再试'
  return msg
}
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; background: rgba(74,54,69,0.4);
  display: flex; align-items: center; justify-content: center;
  z-index: 200; backdrop-filter: blur(4px);
}
.modal-card {
  width: min(420px, 92vw);
  padding: 1.1rem 1.4rem 0.9rem;
  animation: pop-in 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}
.modal-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 0.45rem;
}
.modal-title { font-family: var(--font-display); font-size: 1.1rem; color: var(--plum-1); }
.modal-close { background: none; border: none; font-size: 1.2rem; cursor: pointer; color: var(--plum-3); }
.modal-close:hover { color: var(--plum-1); }

.modal-body { display: flex; flex-direction: column; gap: 0.6rem; }
.intro { font-size: 0.78rem; color: var(--plum-3); margin: 0; line-height: 1.5; }

.tabs { display: flex; gap: 0.4rem; }
.tab {
  flex: 1; padding: 0.35rem 0.7rem;
  border: 1.5px solid var(--cream-4); background: #fff;
  border-radius: var(--radius-pill);
  font-weight: 700; font-size: 0.82rem; color: var(--plum-2);
  cursor: pointer; transition: all var(--transition-fast);
}
.tab.on {
  background: var(--sakura); border-color: var(--sakura-deep);
  color: #fff; box-shadow: 0 2px 0 var(--sakura-deep);
}

.row { display: flex; flex-direction: column; gap: 0.25rem; }
.lbl { font-size: 0.74rem; font-weight: 700; color: var(--plum-2); }
.input {
  padding: 0.4rem 0.7rem;
  border: 1.5px solid var(--cream-4); border-radius: var(--radius-sm);
  background: #fff; font-size: 0.9rem; color: var(--plum-1);
  outline: none;
}
.input:focus { border-color: var(--sakura); }

.info-bar {
  padding: 0.5rem 0.7rem; font-size: 0.78rem; color: #0a6e4b;
  background: var(--ok-glow); border: 1.5px solid var(--ok); border-radius: var(--radius-sm);
}
.error-bar {
  padding: 0.5rem 0.7rem; font-size: 0.78rem; color: #b22e3c;
  background: var(--bad-glow); border: 1.5px solid var(--bad); border-radius: var(--radius-sm);
}

.submit-btn {
  margin-top: 0.4rem; padding: 0.5rem 1rem; font-weight: 800;
}
.submit-btn:disabled { opacity: 0.55; cursor: not-allowed; }

.forgot { text-align: center; font-size: 0.74rem; }
.forgot a { color: var(--sakura-deep); text-decoration: none; }
.forgot a:hover { text-decoration: underline; }
</style>
