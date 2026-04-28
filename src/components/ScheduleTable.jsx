
import React from 'react';
import Papa from 'papaparse';
import { Download, RotateCcw, CheckCircle, AlertCircle, FileDown, CloudUpload } from 'lucide-react';
import { DAYS } from '../utils/constants';
import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';

export function ScheduleTable({ schedule, onReset, onShiftUpdate, settings, startDate }) {

    const getFormattedDate = (baseDate, dayIdx) => {
        if (!baseDate) return '';
        const d = new Date(baseDate);
        d.setDate(d.getDate() + dayIdx);
        return d.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit' });
    };

    const getFullDate = (baseDate, dayIdx) => {
        if (!baseDate) return '';
        const d = new Date(baseDate);
        d.setDate(d.getDate() + dayIdx);
        return d.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric' });
    };

    const exportCSV = () => {
        // Flatten for export with EXACT columns requested
        const exportData = schedule.map(emp => {
            return {
                'ID': emp.ID,
                'Nome Cognome': emp.Nome,
                'Ore Contratto': emp['Ore Contratto'] || 0,
                'Ore Assegnate': emp.assignedHours || 0,
                'Esigenze/Preferenze': emp['Esigenze/Preferenze'],
                'Lun': emp.shifts.Lun,
                'Mar': emp.shifts.Mar,
                'Mer': emp.shifts.Mer,
                'Gio': emp.shifts.Gio,
                'Ven': emp.shifts.Ven,
                'Sab': emp.shifts.Sab,
                'Dom': emp.shifts.Dom
            };
        });

        const csv = Papa.unparse(exportData, {
            delimiter: ";", // Force semi-colon for Excel compatibility in EU
        });

        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', 'turni_generati.csv');
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const exportFluidaCSV = () => {
        const DAY_MAP = {
            Lun: 'LUNEDI',
            Mar: 'MARTEDI',
            Mer: 'MERCOLEDI',
            Gio: 'GIOVEDI',
            Ven: 'VENERDI',
            Sab: 'SABATO',
            Dom: 'DOMENICA',
        };

        const normalizeShift = (value) => {
            if (!value || value.trim() === '' || value.trim() === '-') return '';
            if (value.trim().toUpperCase() === 'RI') return 'RI';
            // Converte separatore " / " nel formato richiesto da Fluida "||"
            return value.replace(/\s*\/\s*/g, '||');
        };

        const exportData = schedule.map(emp => {
            const row = {
                'ID': emp.ID,
                'DIPENDENTE': (emp.Nome || '').toUpperCase(),
            };
            Object.entries(DAY_MAP).forEach(([short, long]) => {
                row[long] = normalizeShift(emp.shifts[short] || '');
            });
            return row;
        });

        const csv = Papa.unparse(exportData, {
            delimiter: ";",
            columns: ['ID', 'DIPENDENTE', 'LUNEDI', 'MARTEDI', 'MERCOLEDI', 'GIOVEDI', 'VENERDI', 'SABATO', 'DOMENICA'],
        });

        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', 'turni_fluida.csv');
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const exportPDF = () => {
        const doc = new jsPDF('l', 'mm', 'a4');
        const pageWidth = doc.internal.pageSize.getWidth();

        // Header
        doc.setFontSize(20);
        doc.setTextColor(220, 38, 38); // Red-600
        doc.text('SPORTWAY - Programmazione Turni', 14, 20);

        doc.setFontSize(12);
        doc.setTextColor(71, 85, 105); // Slate-600
        const departments = settings?.departments?.join(', ') || 'Nessun reparto specificato';
        doc.text(`Reparto: ${departments}`, 14, 28);

        const generationDate = new Date().toLocaleDateString('it-IT');
        doc.setFontSize(10);
        doc.text(`Generato il: ${generationDate}`, pageWidth - 14, 20, { align: 'right' });

        if (startDate) {
            const endD = new Date(startDate);
            endD.setDate(endD.getDate() + 6);
            const rangeStr = `Settimana dal ${getFullDate(startDate, 0)} al ${getFullDate(startDate, 6)}`;
            doc.setFontSize(11);
            doc.setTextColor(51, 65, 85); // Slate-700
            doc.text(rangeStr, 14, 34);
        }

        // Splits "HH:MM-HH:MM / HH:MM-HH:MM" or "HH:MM-HH:MM||HH:MM-HH:MM"
        // into [mattina, pomeriggio]
        const splitShift = (value) => {
            if (!value || value.trim() === '' || value.trim() === '-') return ['', ''];
            const v = value.trim();
            if (v.toUpperCase() === 'RI') return ['RI', ''];
            const parts = v.split(/\s*\/\s*|\|\|/);
            return [parts[0]?.trim() || '', parts[1]?.trim() || ''];
        };

        // Build body: Nome + [mattina, pomeriggio] × 7 days = 15 cells per row
        const dayKeys = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom'];
        const body = schedule.map(emp => {
            const row = [emp.Nome];
            dayKeys.forEach(day => {
                const [m, p] = splitShift(emp.shifts[day]);
                row.push(m, p);
            });
            return row;
        });

        const dayLabels = ['LUNEDÌ', 'MARTEDÌ', 'MERCOLEDÌ', 'GIOVEDÌ', 'VENERDÌ', 'SABATO', 'DOMENICA'];

        autoTable(doc, {
            startY: 40,
            head: [
                // Row 1: day names spanning 2 cols each, Nome spanning 2 rows
                [
                    { content: 'DIPENDENTE', rowSpan: 2, styles: { valign: 'middle', halign: 'center', fontStyle: 'bold' } },
                    ...dayLabels.map((d, i) => ({ 
                        content: startDate ? `${d} ${getFormattedDate(startDate, i)}` : d, 
                        colSpan: 2, 
                        styles: { halign: 'center' } 
                    })),
                ],
                // Row 2: Mattina | Pomeriggio repeated for each day
                [
                    ...Array(7).fill(null).flatMap(() => [
                        { content: 'Mattina', styles: { halign: 'center', fontSize: 6 } },
                        { content: 'Pomeriggio', styles: { halign: 'center', fontSize: 6 } },
                    ]),
                ],
            ],
            body: body,
            headStyles: {
                fillColor: [220, 38, 38], // Red-600
                textColor: [255, 255, 255],
                fontSize: 8,
                fontStyle: 'bold',
                halign: 'center',
            },
            columnStyles: {
                0: { fontStyle: 'bold', cellWidth: 30 }, // Nome
                // Shift cols 1-14: 2 per day × 7 days
                ...Object.fromEntries(
                    Array.from({ length: 14 }, (_, i) => [i + 1, { halign: 'center', cellWidth: 17 }])
                ),
            },
            styles: {
                fontSize: 7,
                cellPadding: 1.5,
                valign: 'middle',
                overflow: 'hidden',
            },
            didParseCell: function (data) {
                if (data.section === 'body' && data.column.index >= 1) {
                    // Smaller font + tight padding so "09:30-12:00" fits on one line
                    data.cell.styles.fontSize = 6.5;
                    data.cell.styles.cellPadding = 1;
                    const isMattina = (data.column.index - 1) % 2 === 0;
                    if (isMattina) {
                        data.cell.styles.fillColor = [238, 242, 255]; // Indigo-50
                        data.cell.styles.textColor = [67, 56, 202];   // Indigo-700
                    } else {
                        data.cell.styles.fillColor = [255, 251, 235]; // Amber-50
                        data.cell.styles.textColor = [180, 83, 9];    // Amber-700
                    }
                }
            },
            didDrawCell: function (data) {
                // Draw a thicker vertical line at the start of each day block (indexes 1, 3, 5, etc.)
                if (data.column.index >= 1 && (data.column.index - 1) % 2 === 0) {
                    doc.setDrawColor(148, 163, 184); // Slate-400
                    doc.setLineWidth(0.4);
                    doc.line(data.cell.x, data.cell.y, data.cell.x, data.cell.y + data.cell.height);
                    // Reset for other borders
                    doc.setLineWidth(0.1);
                }
            },
            alternateRowStyles: {
                fillColor: [255, 255, 255],
            },
            margin: { top: 35 },
        });

        const dateSuffix = startDate ? `_${getFormattedDate(startDate, 0).replace('/', '-')}_${getFormattedDate(startDate, 6).replace('/', '-')}` : '';
        doc.save(`turni_${departments.replace(/, /g, '_')}${dateSuffix}.pdf`);
    };

    return (
        <div className="w-full max-w-7xl mx-auto mt-6 sm:mt-8 bg-white rounded-xl shadow-xl overflow-hidden animate-in fade-in duration-500">
            <div className="p-4 sm:p-6 border-b border-slate-100 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-50/50">
                <div>
                    <h2 className="text-xl sm:text-2xl font-bold text-slate-800">Turni Generati</h2>
                    <p className="text-slate-500 text-sm">Controlla e scarica la programmazione settimanale</p>
                </div>
                <div className="flex flex-wrap sm:flex-nowrap gap-2 sm:gap-3 w-full sm:w-auto">
                    <button
                        onClick={onReset}
                        className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-3 sm:px-4 py-2 text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors shadow-sm font-medium text-sm"
                    >
                        <RotateCcw className="w-4 h-4" />
                        Carica nuovo
                    </button>
                    <button
                        onClick={exportCSV}
                        className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-3 sm:px-4 py-2 text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors shadow-sm font-medium text-sm"
                    >
                        <Download className="w-4 h-4" />
                        Esporta CSV
                    </button>
                    <button
                        onClick={exportFluidaCSV}
                        className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-3 sm:px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors shadow-md shadow-indigo-200 font-medium text-sm"
                    >
                        <CloudUpload className="w-4 h-4" />
                        Esporta Fluida
                    </button>
                    <button
                        onClick={exportPDF}
                        className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-3 sm:px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors shadow-md shadow-red-200 font-medium text-sm"
                    >
                        <FileDown className="w-4 h-4" />
                        Esporta PDF
                    </button>
                </div>
            </div>

            <div className="overflow-x-auto scrollbar-thin scrollbar-thumb-slate-200 scrollbar-track-transparent">
                <table className="w-full text-left border-collapse">
                    <thead>
                        {/* Row 1: fixed cols + day names (colSpan=2 each) */}
                        <tr className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider">
                            <th rowSpan={2} className="p-3 font-semibold border-b border-r border-slate-200 align-middle whitespace-nowrap">Dipendente</th>
                            <th rowSpan={2} className="p-3 font-semibold border-b border-r border-slate-200 align-middle text-center whitespace-nowrap">Contratto</th>
                            <th rowSpan={2} className="p-3 font-semibold border-b border-r border-slate-200 align-middle text-center whitespace-nowrap">Ore</th>
                            {DAYS.map((day, i) => (
                                <th key={day} colSpan={2} className="p-2 font-semibold border-b border-l-2 border-slate-300 text-center">
                                    <div className="flex flex-col items-center">
                                        <span>{day}</span>
                                        {startDate && <span className="text-[10px] font-normal text-slate-400">{getFormattedDate(startDate, i)}</span>}
                                    </div>
                                </th>
                            ))}
                        </tr>
                        {/* Row 2: Mattina / Pomeriggio sub-headers */}
                        <tr className="bg-slate-50 text-xs">
                            {DAYS.map(day => (
                                <React.Fragment key={day}>
                                    <th className="px-1 py-1 font-semibold border-b border-l-2 border-slate-300 text-center bg-indigo-50 text-indigo-500 whitespace-nowrap">Mat.</th>
                                    <th className="px-1 py-1 font-semibold border-b border-slate-200 text-center bg-amber-50 text-amber-500 whitespace-nowrap">Pom.</th>
                                </React.Fragment>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                        {schedule.map((emp, idx) => {
                            const contract = parseInt(emp['Ore Contratto']) || 0;
                            const assigned = emp.assignedHours;
                            const isMet = assigned >= contract;
                            const isOver = assigned > contract;

                            return (
                                <tr key={idx} className="hover:bg-slate-50/50 transition-colors">
                                    <td className="p-3 font-medium text-slate-800 whitespace-nowrap border-r border-slate-100">
                                        {emp.Nome}
                                        <div className="text-xs text-slate-400 font-normal mt-0.5 max-w-[130px] truncate" title={emp['Esigenze/Preferenze']}>
                                            {emp['Esigenze/Preferenze']}
                                        </div>
                                    </td>
                                    <td className="p-3 text-slate-600 text-center whitespace-nowrap border-r border-slate-100">{contract}h</td>
                                    <td className="p-3 text-center border-r border-slate-100">
                                        <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold ${isMet && !isOver ? 'bg-green-100 text-green-700' :
                                            isOver ? 'bg-amber-100 text-amber-700' :
                                                'bg-red-100 text-red-700'
                                            }`}>
                                            {isMet ? <CheckCircle className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
                                            {assigned}h
                                        </div>
                                    </td>
                                    {DAYS.map(day => {
                                        const raw = emp.shifts[day] || '';
                                        const parts = raw.split(/\s*\/\s*/);
                                        const mattina = parts[0]?.trim() || '';
                                        const pomeriggio = parts[1]?.trim() || '';

                                        const handleChange = (slot, val) => {
                                            const m = slot === 'mat' ? val : mattina;
                                            const p = slot === 'pom' ? val : pomeriggio;
                                            const combined = p ? `${m} / ${p}` : m;
                                            onShiftUpdate(idx, day, combined);
                                        };

                                        return (
                                            <React.Fragment key={day}>
                                                <td className="p-1 border-l-2 border-slate-200">
                                                    <input
                                                        type="text"
                                                        className="w-full text-xs font-medium px-1.5 py-1.5 bg-indigo-50 text-indigo-700 rounded border border-indigo-100 focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 outline-none transition-all text-center placeholder-indigo-200 min-w-[96px] whitespace-nowrap"
                                                        value={mattina}
                                                        placeholder="-"
                                                        onChange={(e) => handleChange('mat', e.target.value)}
                                                    />
                                                </td>
                                                <td className="p-1">
                                                    <input
                                                        type="text"
                                                        className="w-full text-xs font-medium px-1.5 py-1.5 bg-amber-50 text-amber-700 rounded border border-amber-100 focus:border-amber-400 focus:ring-1 focus:ring-amber-400 outline-none transition-all text-center placeholder-amber-200 min-w-[96px] whitespace-nowrap"
                                                        value={pomeriggio}
                                                        placeholder="-"
                                                        onChange={(e) => handleChange('pom', e.target.value)}
                                                    />
                                                </td>
                                            </React.Fragment>
                                        );
                                    })}
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
