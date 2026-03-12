# Sportway AI Shift Scheduler 🚀

Un'applicazione professionale per la generazione e l'ottimizzazione automatica dei turni di lavoro, guidata dall'Intelligenza Artificiale (Google OR-Tools CP-SAT).

## 🌟 Caratteristiche Principali

- **Motore AI Avanzato**: Utilizza il solver CP-SAT di Google per risolvere vincoli complessi e ottimizzare la distribuzione delle ore.
- **Riconoscimento Pattern**: L'IA impara dai turni passati contenuti nei file CSV per suggerire programmazioni familiari e realistiche.
- **Apprendimento Continuo (Memory)**: Database SQLite integrato che accumula conoscenza ad ogni importazione, diventando sempre più preciso nel tempo.
- **Rispetto dei Contratti**: Garantisce al 100% che ogni dipendente faccia le ore esatte previste dal contratto.
- **Copertura Totale**: Algoritmo progettato per eliminare i "buchi" di copertura, garantendo presenza costante in apertura, chiusura e durante tutto l'orario continuato.
- **Rotazione Intelligente**: Bilanciamento automatico tra turni di mattina e pomeriggio per garantire equità tra i dipendenti.
- **Interfaccia Premium**: WebApp moderna in React con design curato, supporto per esportazione PDF/CSV e modifiche manuali in tempo reale.

## 🏗️ Architettura Tecnica

- **Frontend**: React + Vite + Tailwind CSS (UI veloce e responsiva).
- **Backend / AI**: Python con FastAPI e Google OR-Tools (Motore di vincolo logico).
- **Persistence**: SQLite (Per lo storage a lungo termine dei pattern di lavoro).
- **Deployment**: Pronto per Vercel (Frontend + Serverless Functions).

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
- Il database dei pattern si trova in `database/scheduler.db`.
- Puoi controllare le statistiche dell'IA visitando `http://localhost:8000/stats`.
- Per le istruzioni di caricamento online su GitHub/Vercel, consulta il file `DEPOLOYMENT_GUIDE_IT.md`.

---
*Sviluppato con dedizione per ottimizzare il lavoro e il tempo del team.*
