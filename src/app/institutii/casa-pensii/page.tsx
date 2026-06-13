'use client';

import { useState, useEffect, useMemo } from 'react';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, Legend, Cell, PieChart, Pie
} from 'recharts';

// ─── Tipuri ──────────────────────────────────────────────────────────────────

interface SalariuRow {
  [key: string]: string | number;
}

interface JudetRow {
  [key: string]: string | number;
}

interface Period {
  year: number;
  month: number;
  luna: string;
  period: string;
  salarii: SalariuRow[];
  judete: JudetRow[];
}

interface CNPPData {
  updated_at: string;
  periods: Period[];
}

// ─── Utilitare ────────────────────────────────────────────────────────────────

function fmt(n: number | string, decimals = 0): string {
  const num = typeof n === 'string' ? parseFloat(n) : n;
  if (isNaN(num)) return '-';
  return num.toLocaleString('ro-RO', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function findCol(row: SalariuRow | JudetRow, keywords: string[]): string | number | undefined {
  const keys = Object.keys(row);
  for (const kw of keywords) {
    const found = keys.find(k => k.toLowerCase().includes(kw.toLowerCase()));
    if (found) return row[found];
  }
  return undefined;
}

// ─── Culori grafice ──────────────────────────────────────────────────────────

const BLUE_PALETTE = [
  '#1e40af', '#2563eb', '#3b82f6', '#60a5fa', '#93c5fd',
  '#bfdbfe', '#dbeafe', '#eff6ff'
];

const TRANSA_COLORS: Record<string, string> = {
  'Sub 3.300': '#ef4444',
  '3.300 - 4.000': '#f97316',
  '4.000 - 5.000': '#eab308',
  '5.000 - 6.000': '#84cc16',
  '6.000 - 8.000': '#22c55e',
  '8.000 - 10.000': '#06b6d4',
  '10.000 - 15.000': '#3b82f6',
  'Peste 15.000': '#8b5cf6',
};

// ─── Componente KPI ──────────────────────────────────────────────────────────

function KPICard({ label, value, sub, color = '#2563eb' }: {
  label: string; value: string; sub?: string; color?: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">{label}</p>
      <p className="text-2xl font-bold" style={{ color }}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

// ─── Tab Salarii ─────────────────────────────────────────────────────────────

function TabSalarii({ period, allPeriods }: { period: Period; allPeriods: Period[] }) {
  const [viewMode, setViewMode] = useState<'bar' | 'trend'>('bar');

  // Detectăm coloanele din datele reale
  const salarii = period.salarii;
  if (!salarii || salarii.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400">
        <p className="text-4xl mb-3">📊</p>
        <p>Nu există date pentru această perioadă.</p>
      </div>
    );
  }

  // Identificăm coloanele cheie
  const sampleRow = salarii[0];
  const colTransa = Object.keys(sampleRow).find(k =>
    k.toLowerCase().includes('trans') || k.toLowerCase().includes('interval') ||
    k.toLowerCase().includes('salar') || k.toLowerCase().includes('grupe')
  ) || Object.keys(sampleRow)[0];

  const colNr = Object.keys(sampleRow).find(k =>
    k.toLowerCase().includes('nr') || k.toLowerCase().includes('număr') ||
    k.toLowerCase().includes('numar') || k.toLowerCase().includes('asigur')
  ) || Object.keys(sampleRow)[1];

  const colPondere = Object.keys(sampleRow).find(k =>
    k.toLowerCase().includes('pond') || k.toLowerCase().includes('%') ||
    k.toLowerCase().includes('procent')
  );

  // Date pentru grafice
  const barData = salarii.map(row => ({
    name: String(row[colTransa] || '').replace('Tranșă salarială (RON): ', ''),
    value: Number(row[colNr] || 0),
    pondere: Number(row[colPondere || ''] || 0),
    color: TRANSA_COLORS[String(row[colTransa] || '')] || '#3b82f6',
  }));

  const totalAsigurati = barData.reduce((s, r) => s + r.value, 0);

  // Trend: evoluție pe luni pentru fiecare tranșă
  const trendData = allPeriods
    .filter(p => p.salarii?.length > 0)
    .map(p => {
      const obj: Record<string, number | string> = { period: p.period, luna: `${p.luna} ${p.year}` };
      p.salarii.forEach(row => {
        const name = String(row[Object.keys(row)[0]] || '');
        const val = Number(row[Object.keys(row)[1]] || 0);
        obj[name] = val;
      });
      return obj;
    });

  const trendKeys = barData.map(d => d.name).slice(2, 7); // Top tranșe mijlocii

  return (
    <div className="space-y-6">
      {/* KPI-uri */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard
          label="Total asigurați"
          value={fmt(totalAsigurati)}
          sub={`${period.luna} ${period.year}`}
          color="#1e40af"
        />
        {barData[4] && (
          <KPICard
            label="Tranșa dominantă"
            value={barData[4]?.name || '-'}
            sub={`${fmt(barData[4]?.value)} asigurați`}
            color="#2563eb"
          />
        )}
        {barData[barData.length - 1] && (
          <KPICard
            label="Venituri peste 15.000 RON"
            value={`${barData[barData.length - 1]?.pondere?.toFixed(1) || '-'}%`}
            sub={fmt(barData[barData.length - 1]?.value) + ' persoane'}
            color="#7c3aed"
          />
        )}
        {barData[0] && (
          <KPICard
            label="Sub salariul minim"
            value={`${barData[0]?.pondere?.toFixed(1) || '-'}%`}
            sub={fmt(barData[0]?.value) + ' persoane'}
            color="#dc2626"
          />
        )}
      </div>

      {/* Toggle view */}
      <div className="flex gap-2">
        <button
          onClick={() => setViewMode('bar')}
          className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
            viewMode === 'bar'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          Distribuție tranșe
        </button>
        {allPeriods.length > 1 && (
          <button
            onClick={() => setViewMode('trend')}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              viewMode === 'trend'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Evoluție în timp
          </button>
        )}
      </div>

      {/* Grafic principal */}
      {viewMode === 'bar' && (
        <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">
            Distribuția asiguraților pe tranșe salariale — {period.luna} {period.year}
          </h3>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={barData} margin={{ top: 5, right: 20, left: 20, bottom: 60 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 11, fill: '#6b7280' }}
                angle={-35}
                textAnchor="end"
                height={70}
              />
              <YAxis
                tick={{ fontSize: 11, fill: '#6b7280' }}
                tickFormatter={(v) => (v >= 1000000 ? `${(v/1000000).toFixed(1)}M` : v >= 1000 ? `${(v/1000).toFixed(0)}K` : v)}
              />
              <Tooltip
                formatter={(val: number) => [fmt(val), 'Asigurați']}
                labelFormatter={(l) => `Tranșă: ${l}`}
                contentStyle={{ fontSize: 12, borderRadius: 8 }}
              />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {barData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {viewMode === 'trend' && trendData.length > 1 && (
        <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">
            Evoluție asigurați pe tranșe salariale (toate perioadele)
          </h3>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={trendData} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="luna" tick={{ fontSize: 10, fill: '#6b7280' }} />
              <YAxis
                tick={{ fontSize: 11, fill: '#6b7280' }}
                tickFormatter={(v) => v >= 1000 ? `${(v/1000).toFixed(0)}K` : v}
              />
              <Tooltip
                formatter={(val: number, name: string) => [fmt(val), name]}
                contentStyle={{ fontSize: 11, borderRadius: 8 }}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {trendKeys.map((key, i) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={BLUE_PALETTE[i % BLUE_PALETTE.length]}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Tabel detaliat */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100">
          <h3 className="text-sm font-semibold text-gray-700">Date complete pe tranșe</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wider">
                <th className="px-5 py-3 text-left">Tranșă salarială</th>
                <th className="px-5 py-3 text-right">Nr. asigurați</th>
                {colPondere && <th className="px-5 py-3 text-right">Pondere</th>}
                <th className="px-5 py-3 text-right">% din total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {barData.map((row, i) => (
                <tr key={i} className="hover:bg-blue-50/40 transition-colors">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full flex-shrink-0"
                        style={{ background: row.color }}
                      />
                      <span className="font-medium text-gray-800">{row.name}</span>
                    </div>
                  </td>
                  <td className="px-5 py-3 text-right font-mono text-gray-700">
                    {fmt(row.value)}
                  </td>
                  {colPondere && (
                    <td className="px-5 py-3 text-right text-gray-600">
                      {row.pondere?.toFixed(1)}%
                    </td>
                  )}
                  <td className="px-5 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <div className="w-24 bg-gray-100 rounded-full h-1.5">
                        <div
                          className="h-1.5 rounded-full"
                          style={{
                            width: `${(row.value / totalAsigurati * 100).toFixed(1)}%`,
                            background: row.color,
                          }}
                        />
                      </div>
                      <span className="text-xs text-gray-500 w-10 text-right">
                        {(row.value / totalAsigurati * 100).toFixed(1)}%
                      </span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="bg-blue-50 font-semibold">
                <td className="px-5 py-3 text-gray-700">Total</td>
                <td className="px-5 py-3 text-right font-mono text-blue-700">{fmt(totalAsigurati)}</td>
                {colPondere && <td className="px-5 py-3 text-right text-blue-700">100%</td>}
                <td className="px-5 py-3 text-right text-blue-700">100%</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  );
}

// ─── Tab Județe ───────────────────────────────────────────────────────────────

function TabJudete({ period, allPeriods }: { period: Period; allPeriods: Period[] }) {
  const [sortBy, setSortBy] = useState<'salariu' | 'asigurati' | 'judet'>('salariu');
  const [selectedJudet, setSelectedJudet] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'map' | 'chart' | 'table'>('chart');

  const judete = period.judete;
  if (!judete || judete.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400">
        <p className="text-4xl mb-3">🗺️</p>
        <p>Nu există date pe județe pentru această perioadă.</p>
      </div>
    );
  }

  // Detectăm coloanele
  const sampleRow = judete[0];
  const colJudet = Object.keys(sampleRow).find(k =>
    k.toLowerCase().includes('judet') || k.toLowerCase().includes('județ') ||
    k.toLowerCase().includes('denumire')
  ) || Object.keys(sampleRow)[0];

  const colSalariu = Object.keys(sampleRow).find(k =>
    k.toLowerCase().includes('salar') || k.toLowerCase().includes('venit') ||
    k.toLowerCase().includes('câștig')
  ) || Object.keys(sampleRow)[1];

  const colNrAsig = Object.keys(sampleRow).find(k =>
    (k.toLowerCase().includes('număr') || k.toLowerCase().includes('numar') || k.toLowerCase().includes('nr')) &&
    (k.toLowerCase().includes('asig') || k.toLowerCase().includes('pers'))
  ) || (Object.keys(sampleRow).length > 2 ? Object.keys(sampleRow)[2] : undefined);

  // Sortăm și procesăm datele
  const judetData = judete
    .map(row => ({
      judet: String(row[colJudet] || '').trim(),
      salariu: Number(row[colSalariu] || 0),
      asigurati: colNrAsig ? Number(row[colNrAsig] || 0) : 0,
    }))
    .filter(r => r.judet && r.judet !== 'nan' && r.salariu > 0);

  const sorted = [...judetData].sort((a, b) => {
    if (sortBy === 'salariu') return b.salariu - a.salariu;
    if (sortBy === 'asigurati') return b.asigurati - a.asigurati;
    return a.judet.localeCompare(b.judet, 'ro');
  });

  const maxSalariu = Math.max(...judetData.map(d => d.salariu));
  const minSalariu = Math.min(...judetData.map(d => d.salariu).filter(v => v > 0));
  const avgSalariu = judetData.reduce((s, d) => s + d.salariu, 0) / judetData.length;
  const totalAsig = judetData.reduce((s, d) => s + d.asigurati, 0);

  // Top 3 / bottom 3 pentru graficul orizontal
  const top10 = [...judetData]
    .sort((a, b) => b.salariu - a.salariu)
    .slice(0, 10)
    .map(d => ({ ...d, name: d.judet.length > 12 ? d.judet.substring(0, 12) + '…' : d.judet }));

  // Trend județe selectate
  const trendData = selectedJudet
    ? allPeriods.filter(p => p.judete?.length > 0).map(p => {
        const row = p.judete.find(r => String(r[colJudet] || '').trim() === selectedJudet);
        return {
          period: p.period,
          luna: `${p.luna.substring(0, 3)} ${p.year}`,
          salariu: row ? Number(row[colSalariu] || 0) : 0,
          asigurati: row && colNrAsig ? Number(row[colNrAsig] || 0) : 0,
        };
      })
    : [];

  return (
    <div className="space-y-6">
      {/* KPI */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard label="Salariu mediu național" value={`${fmt(avgSalariu)} RON`} sub="medie județe" color="#1e40af" />
        <KPICard
          label="Cel mai mare salariu"
          value={`${fmt(maxSalariu)} RON`}
          sub={judetData.find(d => d.salariu === maxSalariu)?.judet}
          color="#059669"
        />
        <KPICard
          label="Cel mai mic salariu"
          value={`${fmt(minSalariu)} RON`}
          sub={judetData.find(d => d.salariu === minSalariu)?.judet}
          color="#dc2626"
        />
        {totalAsig > 0 && (
          <KPICard label="Total asigurați" value={fmt(totalAsig)} sub="suma tuturor județelor" color="#7c3aed" />
        )}
      </div>

      {/* Toggle */}
      <div className="flex gap-2 flex-wrap">
        {(['chart', 'table'] as const).map(mode => (
          <button
            key={mode}
            onClick={() => setViewMode(mode)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              viewMode === mode
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {mode === 'chart' ? 'Top 10 județe' : 'Toate județele'}
          </button>
        ))}
        {selectedJudet && allPeriods.length > 1 && (
          <button
            onClick={() => setViewMode('map')}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              viewMode === 'map'
                ? 'bg-blue-600 text-white'
                : 'bg-green-100 text-green-700 hover:bg-green-200'
            }`}
          >
            📈 Evoluție: {selectedJudet}
          </button>
        )}
      </div>

      {/* Grafic Top 10 */}
      {viewMode === 'chart' && (
        <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">
            Top 10 județe după salariu mediu — {period.luna} {period.year}
          </h3>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={top10} layout="vertical" margin={{ top: 5, right: 60, left: 100, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
              <XAxis
                type="number"
                tick={{ fontSize: 11, fill: '#6b7280' }}
                tickFormatter={(v) => `${(v/1000).toFixed(0)}K`}
              />
              <YAxis
                type="category"
                dataKey="name"
                tick={{ fontSize: 11, fill: '#374151' }}
                width={95}
              />
              <Tooltip
                formatter={(val: number) => [`${fmt(val)} RON`, 'Salariu mediu']}
                contentStyle={{ fontSize: 12, borderRadius: 8 }}
              />
              <Bar dataKey="salariu" radius={[0, 4, 4, 0]}>
                {top10.map((entry, i) => (
                  <Cell
                    key={i}
                    fill={BLUE_PALETTE[Math.min(i, BLUE_PALETTE.length - 1)]}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <p className="text-xs text-gray-400 mt-2 text-center">
            Linie roșie = medie națională ({fmt(avgSalariu)} RON)
          </p>
        </div>
      )}

      {/* Evoluție județ selectat */}
      {viewMode === 'map' && selectedJudet && trendData.length > 1 && (
        <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">
            Evoluție salariu mediu — {selectedJudet}
          </h3>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="luna" tick={{ fontSize: 11, fill: '#6b7280' }} />
              <YAxis
                tick={{ fontSize: 11, fill: '#6b7280' }}
                tickFormatter={(v) => `${(v/1000).toFixed(1)}K`}
                domain={['auto', 'auto']}
              />
              <Tooltip
                formatter={(val: number) => [`${fmt(val)} RON`, 'Salariu mediu']}
                contentStyle={{ fontSize: 12, borderRadius: 8 }}
              />
              <Line
                type="monotone"
                dataKey="salariu"
                stroke="#2563eb"
                strokeWidth={2.5}
                dot={{ r: 4, fill: '#2563eb' }}
              />
            </LineChart>
          </ResponsiveContainer>
          <button
            onClick={() => { setSelectedJudet(null); setViewMode('table'); }}
            className="mt-3 text-xs text-gray-400 hover:text-gray-600 underline"
          >
            ← Înapoi la tabel
          </button>
        </div>
      )}

      {/* Tabel complet */}
      {(viewMode === 'table' || viewMode === 'map') && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100 flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-gray-700">Date pe județe</h3>
            <div className="flex gap-2 text-xs">
              <span className="text-gray-500">Sortare:</span>
              {(['salariu', 'asigurati', 'judet'] as const).map(s => (
                <button
                  key={s}
                  onClick={() => setSortBy(s)}
                  className={`px-2.5 py-1 rounded-full transition-colors ${
                    sortBy === s
                      ? 'bg-blue-100 text-blue-700 font-medium'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {s === 'salariu' ? 'Salariu' : s === 'asigurati' ? 'Asigurați' : 'Alfabet'}
                </button>
              ))}
            </div>
          </div>
          <div className="overflow-x-auto max-h-[480px] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-gray-50 z-10">
                <tr className="text-xs text-gray-500 uppercase tracking-wider">
                  <th className="px-5 py-3 text-left">#</th>
                  <th className="px-5 py-3 text-left">Județ</th>
                  <th className="px-5 py-3 text-right">Salariu mediu</th>
                  <th className="px-5 py-3 text-right hidden md:table-cell">vs. medie națională</th>
                  {totalAsig > 0 && <th className="px-5 py-3 text-right hidden md:table-cell">Nr. asigurați</th>}
                  {allPeriods.length > 1 && <th className="px-5 py-3 text-center hidden md:table-cell">Trend</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {sorted.map((row, i) => {
                  const diff = row.salariu - avgSalariu;
                  const diffPct = (diff / avgSalariu * 100).toFixed(1);
                  const isSelected = selectedJudet === row.judet;
                  return (
                    <tr
                      key={row.judet}
                      onClick={() => setSelectedJudet(isSelected ? null : row.judet)}
                      className={`transition-colors cursor-pointer ${
                        isSelected
                          ? 'bg-blue-50 ring-1 ring-inset ring-blue-200'
                          : 'hover:bg-gray-50'
                      }`}
                    >
                      <td className="px-5 py-3 text-gray-400 text-xs">{i + 1}</td>
                      <td className="px-5 py-3">
                        <span className="font-medium text-gray-800">{row.judet}</span>
                        {isSelected && (
                          <span className="ml-2 text-xs text-blue-500">selectat</span>
                        )}
                      </td>
                      <td className="px-5 py-3 text-right">
                        <span className="font-mono font-semibold text-gray-800">
                          {fmt(row.salariu)} RON
                        </span>
                      </td>
                      <td className="px-5 py-3 text-right hidden md:table-cell">
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                          diff > 0
                            ? 'bg-green-50 text-green-700'
                            : 'bg-red-50 text-red-600'
                        }`}>
                          {diff > 0 ? '+' : ''}{diffPct}%
                        </span>
                      </td>
                      {totalAsig > 0 && (
                        <td className="px-5 py-3 text-right font-mono text-gray-600 hidden md:table-cell">
                          {fmt(row.asigurati)}
                        </td>
                      )}
                      {allPeriods.length > 1 && (
                        <td className="px-5 py-3 text-center hidden md:table-cell">
                          <span className="text-xs text-blue-500 hover:underline">
                            {isSelected ? '📈 activ' : 'click pt. trend'}
                          </span>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {allPeriods.length > 1 && (
            <div className="px-5 py-2 bg-gray-50 text-xs text-gray-400 border-t border-gray-100">
              Click pe un județ pentru a vedea evoluția în timp
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Componenta principală ───────────────────────────────────────────────────

export default function CasaPensiiAsiguratiPage() {
  const [data, setData] = useState<CNPPData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<string>('');
  const [activeSubTab, setActiveSubTab] = useState<'salarii' | 'judete'>('salarii');

  useEffect(() => {
    fetch('/cnpp_asigurati.json')
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d: CNPPData) => {
        setData(d);
        // Selectează ultima perioadă
        if (d.periods?.length > 0) {
          setSelectedPeriod(d.periods[d.periods.length - 1].period);
        }
        setLoading(false);
      })
      .catch(e => {
        setError(e.message);
        setLoading(false);
      });
  }, []);

  const currentPeriod = useMemo(
    () => data?.periods?.find(p => p.period === selectedPeriod),
    [data, selectedPeriod]
  );

  const allPeriods = data?.periods ?? [];

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-500 text-sm">Se încarcă datele CNPP...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-4xl mb-3">⚠️</p>
          <p className="text-gray-600 text-sm">Nu s-au putut încărca datele: {error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      {/* Header pagină */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-xs text-gray-400 mb-2">
                <a href="/" className="hover:text-blue-600">24reco.com</a>
                <span>›</span>
                <span>Instituții Publice</span>
                <span>›</span>
                <span className="text-gray-600">Casa Națională de Pensii</span>
              </div>
              <h1 className="text-2xl font-bold text-gray-900">
                🏛️ Casa Națională de Pensii Publice
              </h1>
              <p className="text-gray-500 text-sm mt-1">
                Indicatori statistici Pilon I — Asigurați · Sursa: CNPP.ro
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-400">Ultima actualizare</p>
              <p className="text-sm font-medium text-gray-600">
                {data.updated_at
                  ? new Date(data.updated_at).toLocaleDateString('ro-RO', {
                      day: 'numeric', month: 'long', year: 'numeric'
                    })
                  : 'N/A'}
              </p>
              <a
                href="https://www.cnpp.ro/ro/indicatori-statistici-pilon-i"
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-500 hover:underline"
              >
                → Sursa oficială CNPP
              </a>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">

        {/* Selector perioadă */}
        <div className="bg-white rounded-xl border border-gray-100 p-4 shadow-sm">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-sm font-medium text-gray-600">Perioadă:</span>
            <div className="flex flex-wrap gap-2">
              {allPeriods.map(p => (
                <button
                  key={p.period}
                  onClick={() => setSelectedPeriod(p.period)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    selectedPeriod === p.period
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'bg-gray-100 text-gray-600 hover:bg-blue-50 hover:text-blue-600'
                  }`}
                >
                  {p.luna} {p.year}
                </button>
              ))}
            </div>
            {allPeriods.length > 0 && (
              <span className="ml-auto text-xs text-gray-400">
                {allPeriods.length} perioadă(e) disponibile
              </span>
            )}
          </div>
        </div>

        {/* Sub-tab Asigurati: Salarii / Județe */}
        {currentPeriod ? (
          <>
            {/* Tab switcher */}
            <div className="flex border-b border-gray-200">
              {(['salarii', 'judete'] as const).map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveSubTab(tab)}
                  className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                    activeSubTab === tab
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  {tab === 'salarii' ? '💰 Salarii' : '🗺️ Județe'}
                </button>
              ))}
            </div>

            {/* Conținut tab */}
            {activeSubTab === 'salarii' && (
              <TabSalarii period={currentPeriod} allPeriods={allPeriods} />
            )}
            {activeSubTab === 'judete' && (
              <TabJudete period={currentPeriod} allPeriods={allPeriods} />
            )}
          </>
        ) : (
          <div className="text-center py-16 text-gray-400">
            <p className="text-4xl mb-3">📋</p>
            <p>Selectează o perioadă pentru a vedea datele.</p>
          </div>
        )}
      </div>

      <Footer />
    </div>
  );
}
