
import React, { useState } from 'react';
import { UploadSection } from './components/UploadSection';
import { ScheduleTable } from './components/ScheduleTable';
import { BrainCircuit } from 'lucide-react';
import { SpeedInsights } from "@vercel/speed-insights/react"
import { Analytics } from "@vercel/analytics/react"

function App() {
  const [schedule, setSchedule] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentSettings, setCurrentSettings] = useState(null);

  const handleDataLoaded = async (data, settings) => {
    setIsGenerating(true);
    setCurrentSettings(settings);
    
    // In produzione su Vercel, faremo chiamate alla stessa origine (creando un proxy/rewrite in vercel.json)
    // In dev locale, usiamo il server Python locale
    const isDev = import.meta.env.DEV;
    const apiUrl = isDev ? 'http://localhost:8000/optimize' : '/api/optimize';
    
    try {
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          employees: data,
          settings: settings
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Errore durante l\'ottimizzazione');
      }

      const result = await response.json();
      
      // Transform incoming data to match the expected format in the UI
      // The solver returns { Nome, shifts: { Lun, ... }, assignedHours }
      // We need to ensure it matches what the UI components expect.
      // Helper function to calculate exact hours from a shift strings object
      const calculateTotalHours = (shifts) => {
        let totalHours = 0;
        Object.values(shifts).forEach(shift => {
          if (!shift) return;
          try {
            const segments = shift.split('/').map(s => s.trim());
            segments.forEach(segment => {
              if (segment.includes('-')) {
                const cleaned = segment.replace(/\s/g, '');
                const [s, e] = cleaned.split('-');
                const startHour = parseInt(s.split(':')[0] || s);
                const startMin = s.includes(':') ? parseInt(s.split(':')[1]) : 0;
                const endHour = parseInt(e.split(':')[0] || e);
                const endMin = e.includes(':') ? parseInt(e.split(':')[1]) : 0;
                
                if (!isNaN(startHour) && !isNaN(endHour)) {
                  let startTotalMin = startHour * 60 + startMin;
                  let endTotalMin = endHour * 60 + endMin;
                  totalHours += (endTotalMin - startTotalMin) / 60;
                }
              }
            });
          } catch (e) { }
        });
        return totalHours;
      };

      const formattedSchedule = result.schedule.map(emp => ({
        ...emp,
        ID: emp.ID,
        Nome: emp.Nome,
        shifts: emp.shifts,
        assignedHours: calculateTotalHours(emp.shifts) // Override server value to guarantee UI consistency
      }));

      setSchedule(formattedSchedule);
    } catch (error) {
      console.error("Optimization failed:", error);
      alert("Errore nell'ottimizzazione: " + error.message + "\nAssicurati che il server Python sia avviato.");
      setSchedule(null);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleReset = () => {
    setSchedule(null);
  };

  const handleShiftUpdate = (empIndex, day, newShift) => {
    setSchedule(prevSchedule => {
      const newSchedule = [...prevSchedule];
      const emp = { ...newSchedule[empIndex] };
      emp.shifts = { ...emp.shifts, [day]: newShift };

      // Recalculate total hours using same exact logic
      let totalHours = 0;
      Object.values(emp.shifts).forEach(shift => {
        if (!shift) return;
        try {
          const segments = shift.split('/').map(s => s.trim());
          segments.forEach(segment => {
            if (segment.includes('-')) {
              const cleaned = segment.replace(/\s/g, '');
              const [s, e] = cleaned.split('-');
              const startHour = parseInt(s.split(':')[0] || s);
              const startMin = s.includes(':') ? parseInt(s.split(':')[1]) : 0;
              const endHour = parseInt(e.split(':')[0] || e);
              const endMin = e.includes(':') ? parseInt(e.split(':')[1]) : 0;
              
              if (!isNaN(startHour) && !isNaN(endHour)) {
                let startTotalMin = startHour * 60 + startMin;
                let endTotalMin = endHour * 60 + endMin;
                totalHours += (endTotalMin - startTotalMin) / 60;
              }
            }
          });
        } catch (e) { }
      });

      emp.assignedHours = totalHours;
      newSchedule[empIndex] = emp;
      return newSchedule;
    });
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 pb-20">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="bg-white p-1 rounded-lg border border-slate-100 shadow-sm">
              <img src="/logo.png" alt="Sportway Logo" className="w-8 h-8 object-contain" />
            </div>
            <h1 className="text-lg sm:text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-red-600 to-rose-600 truncate">
              AI Scheduler
            </h1>
          </div>
          <div className="text-xs text-slate-500 hidden sm:block">
            Gestione Turni Intelligente
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 pt-6 sm:pt-10">
        {!schedule && !isGenerating && (
          <div className="text-center space-y-4 mb-10">
            <h2 className="text-2xl sm:text-4xl font-extrabold text-slate-800 tracking-tight leading-tight">
              Ottimizza i turni con <span className="text-red-600">l'AI</span>
            </h2>
            <p className="text-slate-600 max-w-2xl mx-auto text-base sm:text-lg leading-relaxed">
              Carica il file CSV con i dati dei dipendenti. Il nostro sistema analizzerà contratti e preferenze per generare la settimana lavorativa perfetta.
            </p>
            <UploadSection onDataLoaded={handleDataLoaded} />

            <div className="mt-8 sm:mt-12 text-left bg-white p-4 sm:p-6 rounded-xl border border-slate-200 shadow-sm max-w-2xl mx-auto">
              <h4 className="font-semibold text-slate-900 mb-2">Formato CSV Richiesto:</h4>
              <code className="block bg-slate-100 p-3 rounded text-xs text-slate-700 font-mono overflow-x-auto whitespace-pre sm:whitespace-normal">
                ID; Nome Cognome; Ore Contratto; Esigenze/Preferenze; Lun; Mar; ...; Dom; Lun_W1; Mar_W1; ...; Dom_W3
              </code>
              <p className="text-xs text-slate-500 mt-2">
                Le colonne dei giorni (Lun...Dom) sono per la settimana da generare. Le colonne _W1, _W2, _W3 contengono lo storico.
              </p>
            </div>
          </div>
        )}

        {isGenerating && (
          <div className="flex flex-col items-center justify-center py-20 animate-in fade-in duration-700">
            <div className="relative w-20 h-20 mb-8">
              <div className="absolute inset-0 border-4 border-red-100 rounded-full"></div>
              <div className="absolute inset-0 border-4 border-red-600 border-t-transparent rounded-full animate-spin"></div>
              <BrainCircuit className="absolute inset-0 m-auto w-8 h-8 text-red-600 animate-pulse" />
            </div>
            <h3 className="text-2xl font-bold text-slate-800 mb-2">Analisi in corso...</h3>
            <p className="text-slate-500">Sto calcolando le combinazioni migliori per i turni.</p>
          </div>
        )}

        {schedule && (
          <ScheduleTable 
            schedule={schedule} 
            onReset={handleReset} 
            onShiftUpdate={handleShiftUpdate}
            settings={currentSettings}
          />
        )}
      </main>
      <SpeedInsights />
      <Analytics />
    </div>
  );
}

export default App;
