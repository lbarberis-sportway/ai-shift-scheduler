import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  console.warn('Supabase credentials missing. Auth will not work properly.')
}

// Check if we have the credentials before creating the client to avoid hard crashes
const isConfigured = !!(supabaseUrl && supabaseAnonKey)

export const supabase = isConfigured 
  ? createClient(supabaseUrl, supabaseAnonKey)
  : { 
      auth: { 
        getSession: async () => ({ data: { session: null }, error: null }), 
        onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => {} } } }),
        signInWithPassword: async () => {
          alert("Configurazione Mancante: Le variabili VITE_SUPABASE_URL o VITE_SUPABASE_ANON_KEY non sono state trovate su Vercel.");
          return { data: {}, error: { message: "Configurazione mancante" } };
        }
      } 
    }
