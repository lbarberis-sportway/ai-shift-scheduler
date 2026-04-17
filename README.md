# Sportway AI Shift Scheduler 🚀

Un'applicazione professionale per la generazione e l'ottimizzazione automatica dei turni di lavoro, guidata dall'Intelligenza Artificiale (Google OR-Tools CP-SAT).

## 🌟 Caratteristiche Principali

- **Motore AI Avanzato**: Utilizza il solver CP-SAT di Google per risolvere vincoli complessi e ottimizzare la distribuzione delle ore.
- **Riconoscimento Pattern**: L'IA impara dai turni passati contenuti nei file CSV per suggerire programmazioni familiari e realistiche.
- **Apprendimento Continuo (Memory)**: Database Cloud su **Supabase (PostgreSQL)** che accumula conoscenza ad ogni importazione, diventando sempre più preciso nel tempo senza perdita di dati tra i riavvii.
- **Rispetto dei Contratti**: Garantisce al 100% che ogni dipendente faccia le ore esatte previste dal contratto.
- **Copertura Totale**: Algoritmo progettato per eliminare i "buchi" di copertura, garantendo presenza costante in apertura, chiusura e durante tutto l'orario continuato.
- **Rotazione Intelligente**: Bilanciamento automatico tra turni di mattina e pomeriggio per garantire equità tra i dipendenti.
- **Interfaccia Premium**: WebApp moderna in React (Vite) con design curato, supporto per esportazione PDF/CSV (Fluida) e modifiche manuali in tempo reale.

## 🏗️ Architettura Professionale

- **Frontend**: React + Vite + Tailwind CSS - Hostato su **Vercel** per la massima velocità di caricamento.
- **Backend AI**: Python con FastAPI e Google OR-Tools - Hostato su **Render.com** per calcoli complessi e stabilità superiore.
- **Database Professionale**: **Supabase (PostgreSQL)** - Per una gestione sicura, persistente e veloce della "memoria" dell'IA.
- **Sicurezza & Velocità**: Connessioni cifrate SSL, ottimizzazione delle performance e deployment costante direttamente da GitHub.

## 🚀 Guida Rapida

### 1. Installazione
```bash
# Installa dipendenze React
npm install

# Installa dipendenze Python
pip install ortools fastapi uvicorn pydantic
```

### 2. Avvio (Locale)
```bash
# Terminale 1: Backend AI
python server.py

# Terminale 2: Frontend
npm run dev
```

### 3. Utilizzo
1. Prepara un file CSV con i nomi, le ore di contratto e lo storico degli ultimi turni.
2. Carica il file nella WebApp.
3. Clicca su **"Ottimizza Turni"**.
4. Esporta il risultato in **PDF professionale** o **CSV** per Excel.

## 🔧 Manutenzione e Debug
- **Database Cloud**: La gestione dei pattern avviene su Supabase. Puoi monitorare i dati direttamente dalla dashboard di Supabase.
- **Backend Logs**: I log del motore AI sono visibili nella dashboard di Render.com.
- **Statistiche**: Puoi controllare le statistiche dell'IA visitando `[URL-BACKEND]/stats`.

---
*Sviluppato con dedizione per ottimizzare il lavoro e il tempo del team Sportway.*
