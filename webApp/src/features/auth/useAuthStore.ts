import { create } from 'zustand';
import { supabase } from '@/lib/supabaseClient';
import { User, Session } from '@supabase/supabase-js';

export interface AuthState {
  user: User | null;
  session: Session | null;
  loading: boolean;
  error: string | null;
  setUser: (user: User | null) => void;
  setSession: (session: Session | null) => void;
  signInWithProvider: (provider: 'google' | 'apple', includeGmail?: boolean) => Promise<void>;
  signOut: () => Promise<void>;
  getToken: () => string | null;
}

const redirectTo = window.location.origin;

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  session: null,
  loading: false,
  error: null,
  setUser: (user) => set({ user }),
  setSession: (session) => {
    set({ session });
    if (session) {
      localStorage.setItem('sb_session', JSON.stringify(session));
    } else {
      localStorage.removeItem('sb_session');
    }
  },
  signInWithProvider: async (provider, includeGmail = false) => {
    set({ loading: true, error: null });
    
    const options: any = { redirectTo };
    
    // If including Gmail, add Gmail scopes and redirect to Gmail callback
    if (includeGmail && provider === 'google') {
      options.scopes = 'https://www.googleapis.com/auth/gmail.readonly';
      options.queryParams = {
        access_type: 'offline',
        prompt: 'consent',
      };
      options.redirectTo = `${window.location.origin}/auth/callback?service=gmail`;
    }
    
    const { error } = await supabase.auth.signInWithOAuth({ provider, options });
    if (error) set({ error: error.message });
    set({ loading: false });
  },
  signOut: async () => {
    set({ loading: true, error: null });
    const { error } = await supabase.auth.signOut();
    if (error) set({ error: error.message });
    set({ user: null, session: null, loading: false });
    localStorage.removeItem('sb_session');
  },
  getToken: () => {
    const session = get().session;
    return session?.access_token || null;
  },
}));

// Restore session from localStorage on load
const saved = localStorage.getItem('sb_session');
if (saved) {
  const session = JSON.parse(saved);
  useAuthStore.getState().setSession(session);
  useAuthStore.getState().setUser(session.user);
}