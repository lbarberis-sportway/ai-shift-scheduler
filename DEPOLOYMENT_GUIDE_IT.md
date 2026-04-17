# Guida al Deploy Professionale (Vercel + Render + Supabase)

Questa guida spiega come configurare l'architettura moderna e sicura per il tuo Sportway AI Shift Scheduler.

## 🏗️ Architettura del Sistema
- **Frontend (React)**: Hostato su **Vercel** (veloce, globale).
- **Backend AI (Python)**: Hostato su **Render.com** (stabile, supporta calcoli lunghi).
- **Database (PostgreSQL)**: Hostato su **Supabase** (persistente, sicuro).

---

## 1. Configurazione Database (Supabase)
1. Crea un account su [Supabase.com](https://supabase.com/).
2. Crea un nuovo progetto (es: `shift-scheduler-db`).
3. Vai in **Project Settings > API**.
4. Copia i seguenti valori:
   - **Project URL**: Ti servirà come `VITE_SUPABASE_URL`.
   - **anon public**: Ti servirà come `VITE_SUPABASE_ANON_KEY`.
   - **JWT Secret**: Ti servirà come `SUPABASE_JWT_SECRET` (fondamentale per proteggere il backend).

## 2. Configurazione Utenti (Supabase Auth)
1. Vai in **Authentication > Providers** e assicurati che **Email** sia abilitato.
2. Vai in **Authentication > Users** e clicca su **Add User > Create new user**.
3. Inserisci l'email e la password per chi deve accedere al sistema.

## 3. Configurazione Backend (Render.com)
1. Crea un account su [Render.com](https://render.com/) e collegalo a GitHub.
2. Clicca su **New > Web Service**.
3. Seleziona il tuo repository.
4. Configurazioni:
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
5. Vai in **Environment** e aggiungi le variabili:
   - `DATABASE_URL`: La stringa di connessione DB di Supabase.
   - `SUPABASE_JWT_SECRET`: Il codice segreto JWT trovato nelle impostazioni API di Supabase.
   - `FRONTEND_URL`: L'URL del tuo sito su Vercel.
6. Copia l'URL che Render ti assegna (es: `https://shift-scheduler-backend.onrender.com`).

## 4. Configurazione Frontend (Vercel)
1. Vai su [Vercel.com](https://vercel.com/) e importa il progetto da GitHub.
2. Nelle impostazioni del progetto, vai su **Environment Variables**:
   - `VITE_API_URL`: L'URL del backend su Render.
   - `VITE_SUPABASE_URL`: L'URL del progetto Supabase.
   - `VITE_SUPABASE_ANON_KEY`: La chiave anonime di Supabase.
3. Clicca su **Deploy**.

---

## ✅ Vantaggi di questa configurazione
- **Persistenza Totale**: A differenza di Vercel Serverless, il database Supabase non perde mai i dati learned.
- **Calcoli Potenti**: Render permette all'IA di girare per tutto il tempo necessario senza timeout.
- **Sicurezza**: Tutte le connessioni sono protette da SSL e le variabili d'ambiente nascondono le password.
- **Deploy Automatico**: Ogni volta che carichi codice su GitHub, il sito si aggiorna da solo sia sul fronte che sul retro!

---
*Per supporto tecnico o modifiche, consulta la documentazione interna.*
