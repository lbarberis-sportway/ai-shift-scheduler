
import React, { useState, useEffect } from 'react';
import { UploadSection } from './components/UploadSection';
import { ScheduleTable } from './components/ScheduleTable';
import { Login } from './components/Login';
import { supabase } from './lib/supabase';
import { BrainCircuit, LogOut, User } from 'lucide-react';
import { SpeedInsights } from "@vercel/speed-insights/react"

function App() {
  const [session, setSession] = useState(null);
  const [schedule, setSchedule] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentSettings, setCurrentSettings] = useState(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    setSchedule(null);
  };

  const handleDataLoaded = async (data, settings) => {
    setIsGenerating(true);
    setCurrentSettings(settings);
    
    // Usa il backend su Render se definito nelle variabili d'ambiente, altrimenti usa localhost
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const apiUrl = `${baseUrl.replace(/\/$/, '')}/optimize`;
    
    try {
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session?.access_token}`
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
        assignedHours: calculateTotalHours(emp.shifts)
      }));

      setSchedule(formattedSchedule);
    } catch (error) {
      console.error("Optimization failed:", error);
      alert("Errore nell'ottimizzazione: " + error.message + "\nAssicurati che il server Python sia avviato e di aver effettuato il login correttamente.");
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
          
          {session ? (
            <div className="flex items-center gap-4">
              <div className="hidden sm:flex items-center gap-2 text-xs font-medium text-slate-500 bg-slate-50 px-3 py-1.5 rounded-full border border-slate-100">
                <User className="w-3.5 h-3.5" />
                {session.user.email}
              </div>
              <button 
                onClick={handleLogout}
                className="flex items-center gap-2 text-xs font-semibold text-slate-600 hover:text-red-600 transition-colors p-2 hover:bg-red-50 rounded-lg"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden xs:inline">Esci</span>
              </button>
            </div>
          ) : (
            <div className="text-xs text-slate-500 hidden sm:block">
              Area Protetta
            </div>
          )}
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 pt-6 sm:pt-10">
        {!session ? (
          <Login />
        ) : (
          <>
            {!schedule && !isGenerating && (
              <div className="text-center space-y-4 mb-10">
                <h2 className="text-2xl sm:text-4xl font-extrabold text-slate-800 tracking-tight leading-tight">
                  Bentornato su <span className="text-red-600">AI Scheduler</span>
                </h2>
                <p className="text-slate-600 max-w-2xl mx-auto text-base sm:text-lg leading-relaxed">
                  Carica il file CSV dei dipendenti per generare la settimana ottimizzata.
                </p>
                <UploadSection onDataLoaded={handleDataLoaded} />

                <div className="mt-8 sm:mt-12 text-left bg-white p-4 sm:p-6 rounded-xl border border-slate-200 shadow-sm max-w-2xl mx-auto">
                  <h4 className="font-semibold text-slate-900 mb-2">Formato CSV Richiesto:</h4>
                  <code className="block bg-slate-100 p-3 rounded text-xs text-slate-700 font-mono overflow-x-auto whitespace-pre sm:whitespace-normal">
                    ID; Nome Cognome; Ore Contratto; Esigenze/Preferenze; Lun; Mar; ...; Dom; Lun_W1; Mar_W1; ...; Dom_W3
                  </code>
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
          </>
        )}
      </main>
      <SpeedInsights />
    </div>
  );
}

export default App;
