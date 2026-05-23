/**
 * useAuth — Supabase email/password authentication wrapper.
 *
 * Module-singleton state: user / session are kept in sync with Supabase's
 * built-in session storage and onAuthStateChange. Other modules import this
 * to read the current user or trigger sign-in/sign-out.
 *
 * When Supabase isn't configured (no env vars) we expose a no-op shape so
 * the gallery's local-only fallback path keeps working.
 */
import { ref } from 'vue'
import type { User, Session } from '@supabase/supabase-js'
import { supabase, REMOTE_ENABLED } from '../lib/supabase'

const user = ref<User | null>(null)
const session = ref<Session | null>(null)
const loading = ref<boolean>(REMOTE_ENABLED)
const isAdmin = ref<boolean>(false)

/** Username (no '@') logins are mapped to this fake-domain so Supabase still
 *  sees a valid email. e.g. "root" → "root@pindou.local". */
const USERNAME_DOMAIN = 'pindou.local'

async function refreshAdminFlag() {
  if (!supabase || !user.value) { isAdmin.value = false; return }
  try {
    const { data, error: e } = await supabase
      .from('gallery_admins')
      .select('user_id')
      .eq('user_id', user.value.id)
      .maybeSingle()
    if (e) throw e
    isAdmin.value = !!data
  } catch {
    isAdmin.value = false
  }
}

if (REMOTE_ENABLED && supabase) {
  // hydrate from any persisted session
  supabase.auth.getSession().then(({ data }) => {
    session.value = data.session
    user.value = data.session?.user ?? null
    loading.value = false
    refreshAdminFlag()
  }).catch(() => { loading.value = false })

  // stay in sync with sign-in / sign-out / token refresh events
  supabase.auth.onAuthStateChange((_event, newSession) => {
    session.value = newSession
    user.value = newSession?.user ?? null
    refreshAdminFlag()
  })
}

/** Convert a login input to an email: bare usernames get mapped to the
 *  pindou.local domain so users can type "root" instead of the fake email. */
export function resolveLoginEmail(input: string): string {
  const v = input.trim()
  return v.includes('@') ? v : `${v}@${USERNAME_DOMAIN}`
}

export interface SignUpResult {
  needsEmailConfirmation: boolean
  user: User | null
}

export function useAuth() {
  /**
   * Create a new account. If the project has email confirmation enabled
   * (default), the user will receive a verification link and won't get a
   * session until they click it; we return needsEmailConfirmation = true so
   * the UI can show a "check your inbox" message.
   */
  async function signUp(email: string, password: string): Promise<SignUpResult> {
    if (!supabase) throw new Error('Supabase 未配置')
    const { data, error } = await supabase.auth.signUp({ email, password })
    if (error) throw error
    return {
      needsEmailConfirmation: !data.session,
      user: data.user,
    }
  }

  async function signIn(email: string, password: string): Promise<void> {
    if (!supabase) throw new Error('Supabase 未配置')
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) throw error
  }

  async function signOut(): Promise<void> {
    if (!supabase) return
    await supabase.auth.signOut()
  }

  /**
   * Send a password-reset email. The user clicks the link and is brought
   * back to the site to set a new password.
   */
  async function resetPassword(email: string): Promise<void> {
    if (!supabase) throw new Error('Supabase 未配置')
    const { error } = await supabase.auth.resetPasswordForEmail(email)
    if (error) throw error
  }

  return {
    user, session, loading, isAdmin,
    signUp, signIn, signOut, resetPassword,
    REMOTE_ENABLED,
  }
}
