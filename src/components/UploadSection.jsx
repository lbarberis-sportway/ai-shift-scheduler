
import React, { useCallback } from 'react';
import Papa from 'papaparse';
import { UploadCloud, FileSpreadsheet, ChevronDown, Check } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

// MultiSelect Helper Component
function MultiSelect({ label, options, selected, onChange, placeholder = "Seleziona..." }) {
    const [isOpen, setIsOpen] = React.useState(false);
    const containerRef = React.useRef(null);

    React.useEffect(() => {
        const handleClickOutside = (event) => {
            if (containerRef.current && !containerRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const toggleOption = (option) => {
        const newSelected = selected.includes(option)
            ? selected.filter(item => item !== option)
            : [...selected, option];
        onChange(newSelected);
    };

    return (
        <div className="relative" ref={containerRef}>
            <label className="block text-sm font-medium text-slate-600 mb-1">{label}</label>
            <button
                type="button"
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex items-center justify-between p-2 border border-slate-300 rounded-lg text-sm bg-slate-50 focus:ring-2 focus:ring-red-500 focus:border-red-500 min-h-[40px]"
            >
                <span className="truncate text-slate-700 text-left">
                    {selected.length > 0 ? selected.join(', ') : placeholder}
                </span>
                <ChevronDown className={twMerge("w-4 h-4 text-slate-400 transition-transform shrink-0", isOpen && "rotate-180")} />
            </button>

            {isOpen && (
                <div className="absolute z-50 w-full mt-1 bg-white border border-slate-200 rounded-lg shadow-xl max-h-60 overflow-y-auto animate-in fade-in zoom-in-95 duration-200">
                    <div className="p-1">
                        {options.map((option) => (
                            <button
                                key={option}
                                type="button"
                                onClick={() => toggleOption(option)}
                                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 rounded-md transition-colors"
                            >
                                <div className={twMerge(
                                    "w-4 h-4 border rounded flex items-center justify-center transition-colors shrink-0",
                                    selected.includes(option) ? "bg-red-600 border-red-600" : "border-slate-300"
                                )}>
                                    {selected.includes(option) && <Check className="w-3 h-3 text-white" />}
                                </div>
                                <span>{option}</span>
                            </button>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

export function UploadSection({ onDataLoaded }) {
    const [settings, setSettings] = React.useState({
        closedDays: [],
        openTime: '09:30',
        closeTime: '19:30',
        departments: ['Cassa']
    });
    const [parsedData, setParsedData] = React.useState(null);
    const [fileName, setFileName] = React.useState('');

    const allDepartments = [
        'Cassa', 'Montagna', 'Fitness', 'Scarpe', 'Bike',
        'Abbigliamento', 'Young', 'RDK', 'Bar', 'Cucina'
    ];

    const daysList = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom'];

    const handleFile = useCallback((file) => {
        if (file) {
            setFileName(file.name);
            Papa.parse(file, {
                header: true,
                skipEmptyLines: true,
                complete: (results) => {
                    // Basic validation
                    if (results.data && results.data.length > 0) {
                        // Check if columns exist
                        const firstRow = results.data[0];
                        if ('ID' in firstRow && 'Nome Cognome' in firstRow && 'Ore Contratto' in firstRow) {
                            setParsedData(results.data);
                        } else {
                            alert("CSV non valido. Assicurati che ci siano le colonne 'ID', 'Nome Cognome' e 'Ore Contratto'.");
                            setParsedData(null);
                            setFileName('');
                        }
                    }
                },
                error: (err) => {
                    console.error("Error parsing CSV:", err);
                    alert("Errore durante la lettura del CSV.");
                    setParsedData(null);
                    setFileName('');
                }
            });
        }
    }, []);

    const handleOptimize = () => {
        if (parsedData) {
            onDataLoaded(parsedData, settings);
        }
    };

    const onDrop = (e) => {
        e.preventDefault();
        const file = e.dataTransfer.files[0];
        handleFile(file);
    };

    const onDragOver = (e) => {
        e.preventDefault();
    };

    const onChange = (e) => {
        const file = e.target.files[0];
        handleFile(file);
    };

    return (
        <div className="max-w-xl mx-auto mt-6 sm:mt-10 space-y-4 sm:space-y-6">
            <div className="bg-white p-4 sm:p-6 rounded-xl shadow-sm border border-slate-200 text-left">
                <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
                    ⚙️ Impostazioni Negozio
                </h3>
                <div className="space-y-4">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <MultiSelect
                            label="Reparti"
                            options={allDepartments}
                            selected={settings.departments}
                            onChange={(val) => setSettings({ ...settings, departments: val })}
                            placeholder="Seleziona Reparti"
                        />
                        <MultiSelect
                            label="Giorni di Chiusura"
                            options={daysList}
                            selected={settings.closedDays}
                            onChange={(val) => setSettings({ ...settings, closedDays: val })}
                            placeholder="Nessuno (7/7)"
                        />
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="grid grid-cols-2 gap-2">
                            <div>
                                <label className="block text-sm font-medium text-slate-600 mb-1">Apertura</label>
                                <input
                                    type="time"
                                    value={settings.openTime}
                                    onChange={(e) => setSettings({ ...settings, openTime: e.target.value })}
                                    className="w-full p-2 border border-slate-300 rounded-lg text-sm bg-slate-50"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-600 mb-1">Chiusura</label>
                                <input
                                    type="time"
                                    value={settings.closeTime}
                                    onChange={(e) => setSettings({ ...settings, closeTime: e.target.value })}
                                    className="w-full p-2 border border-slate-300 rounded-lg text-sm bg-slate-50"
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div
                className={twMerge(
                    "p-6 sm:p-8 border-2 border-dashed rounded-2xl bg-white/50 backdrop-blur-sm hover:bg-white/80 transition-all cursor-pointer text-center group",
                    parsedData ? "border-green-300 bg-green-50/30" : "border-red-300"
                )}
                onDrop={onDrop}
                onDragOver={onDragOver}
            >
                <input type="file" accept=".csv" onChange={onChange} className="hidden" id="csv-upload" />
                <label htmlFor="csv-upload" className="cursor-pointer flex flex-col items-center">
                    <div className={twMerge(
                        "p-4 rounded-full mb-4 group-hover:scale-110 transition-transform",
                        parsedData ? "bg-green-100" : "bg-red-50"
                    )}>
                        <UploadCloud className={twMerge("w-10 h-10", parsedData ? "text-green-600" : "text-red-600")} />
                    </div>
                    <h3 className="text-xl font-bold text-slate-800 mb-2">
                        {parsedData ? "File Caricato con Successo" : "Importa Dati Dipendenti"}
                    </h3>
                    <p className="text-slate-500 mb-6 font-medium">
                        {fileName ? (
                            <span className="text-red-600">📄 {fileName}</span>
                        ) : (
                            "Trascina qui il tuo file CSV o clicca per cercare"
                        )}
                    </p>

                    <div className="flex items-center gap-2 text-sm text-slate-500 bg-slate-100 px-3 py-1 rounded-full">
                        <FileSpreadsheet className="w-4 h-4" />
                        <span>Formato: ID; Nome Cognome; Ore Contratto; ...; Lun_W1...Dom_W3</span>
                    </div>
                </label>
            </div>

            {parsedData && (
                <div className="animate-in slide-in-from-bottom duration-500">
                    <button
                        onClick={handleOptimize}
                        className="w-full py-4 bg-gradient-to-r from-red-600 to-rose-600 text-white rounded-xl font-bold text-lg shadow-lg shadow-red-200 hover:shadow-xl hover:-translate-y-0.5 transition-all flex items-center justify-center gap-2"
                    >
                        🚀 Ottimizza Turni
                    </button>
                    <p className="text-center text-xs text-slate-400 mt-2">
                        Clicca per calcolare la distribuzione ottimale basata sui parametri sopra.
                    </p>
                </div>
            )}
        </div>
    );
}
