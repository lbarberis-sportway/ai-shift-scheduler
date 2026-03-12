# Guida al Deploy su Vercel (React + Python Backend)

Il progetto è ora configurato per essere hostato gratuitamente su **Vercel** usando Serverless Functions per far girare il "cervello" in Python.

## 1. Caricare il progetto su GitHub
1. Vai su [GitHub](https://github.com/) e accedi (crea un account se non lo hai).
2. Clicca su **New Repository**.
3. Dai un nome (es: `shift-scheduler`), metti **Private** e clicca **Create repository**.
4. Nel terminale del tuo PC (nella cartella del progetto), esegui questi comandi:
   ```bash
   git init
   git add .
   git commit -m "Prima versione con AI Python"
   git branch -M main
   # Sostituisci il link qui sotto con quello che ti dà GitHub:
   git remote add origin https://github.com/tuo-utente/shift-scheduler.git
   git push -u origin main
   ```

> [!NOTE]
> **La cartella `.venv` NON va caricata su GitHub.** È normale che non riesca a caricarla o che venga saltata: è una cartella locale "pesante" che non serve online.
> Vercel leggerà il file `requirements.txt` che ho creato per te e installerà automaticamente tutto quello che serve nei suoi server. Funziona perfettamente così!

## 2. Collegare Vercel
1. Vai su [Vercel](https://vercel.com/) e accedi col tuo account GitHub.
2. Clicca su **Add New... > Project**.
3. Seleziona il repository `shift-scheduler` che hai appena creato su GitHub.
4. Lascia tutte le impostazioni predefinite (Vercel capirà da solo che è un progetto Vite/React).
5. Clicca su **Deploy**.

## Come funziona il nuovo sistema in Cloud?
Ho creato un file `vercel.json` e una cartella `api`. 
Quando sarai online, Vercel farà due cose:
- Mostrerà il tuo sito all'indirizzo `https://nome-sito.vercel.app`
- Trasformerà il tuo file Python in una API Serverless all'indirizzo `https://nome-sito.vercel.app/api/optimize`

**Non dovrai più tenere i terminali aperti sul tuo PC!** Il database SQLite in cloud è un po' particolare (si resetta a ogni deploy), ma per iniziare andrà benissimo, potremo passare a un DB cloud esterno in futuro se vorrai mantenere la "memoria" intatta tra un aggiornamento e l'altro dell'app!
