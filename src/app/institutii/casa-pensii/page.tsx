'use client';

import { useState, useEffect, useMemo } from 'react';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, Legend, Cell,
} from 'recharts';

// ─── Tipuri (structura JSON generată de fetch_cnpp_asigurati.py) ─────────────

interface SalariuRow {
  grupa: string;
  transa: string;
  numar: number;              // asigurați normă întreagă
  venit_mediu: number;
  timp_partial: number;
  fara_contract: number;
  somaj: number;
  contract_individual: number;
}

interface JudetRow {
  cod: string;
  judet: string;
  angajatori: number;
  fond_salarii: number;
  asigurati: number;
  salariu_mediu: number;
}

interface Period {
  year: number;
  month: number;
  luna: string;
  period: string;
  total_asigurati: number | null;
  salarii: SalariuRow[];
  judete: JudetRow[];
}

interface CNPPData {
  updated_at: string;
  periods: Period[];
}

// ─── Utilitare ────────────────────────────────────────────────────────────────

function fmt(n: number | null | undefined, decimals = 0): string {
  if (n === null || n === undefined || isNaN(n)) return '-';
  return n.toLocaleString('ro-RO', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

// Culori pe gradient pentru tranșe (de la venit mic → mare)
function transaColor(index: number, total: number): string {
  const palette = [
    '#94a3b8', '#ef4444', '#f97316', '#f59e0b', '#eab308', '#84cc16',
    '#22c55e', '#10b981', '#14b8a6', '#06b6d4', '#0ea5e9', '#3b82f6',
    '#6366f1', '#8b5cf6', '#a855f7', '#d946ef',
  ];
  return palette[Math.min(index, palette.length - 1)];
}

const BLUE_PALETTE = [
  '#1e3a8a', '#1e40af', '#2563eb', '#3b82f6', '#60a5fa',
  '#93c5fd', '#bfdbfe', '#dbeafe', '#eff6ff', '#f8fafc',
];

// ─── KPI Card ─────────────────────────────────────────────────────────────────

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

  const salarii = period.salarii;
  if (!salarii || salarii.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400">
        <p className="text-4xl mb-3">📊</p>
        <p>Nu există date pentru această perioadă.</p>
      </div>
    );
  }

  const totalNormaIntreaga = period.total_asigurati
    ?? salarii.reduce((s, r) => s + r.numar, 0);

  const barData = salarii.map((row, i) => ({
    name: row.transa,
    value: row.numar,
    venitMediu: row.venit_mediu,
    timpPartial: row.timp_partial,
    color: transaColor(i, salarii.length),
  }));

  // Tranșa cu cei mai mulți asigurați (excludem "Fără venit")
  const dominanta = [...salarii]
    .filter(r => r.transa !== 'Fără venit')
    .sort((a, b) => b.numar - a.numar)[0];

  // Sub salariul minim = grupa 1 (sub 4050 în 2026)
  const subMinim = salarii.find(r => r.grupa === '1');
  // Peste ultima tranșă mare
  const pesteMax = salarii[salarii.length - 1];

  // Trend pe luni: total + tranșa dominantă
  const trendData = allPeriods
    .filter(p => p.salarii?.length > 0)
    .map(p => ({
      luna: `${p.luna.substring(0, 3)} ${p.year}`,
      total: p.total_asigurati ?? p.salarii.reduce((s, r) => s + r.numar, 0),
    }));

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard
          label="Total asigurați (normă întreagă)"
          value={fmt(totalNormaIntreaga)}
          sub={`${period.luna} ${period.year}`}
          color="#1e40af"
        />
        {dominanta && (
          <KPICard
            label="Tranșa dominantă"
            value={`${dominanta.transa} RON`}
            sub={`${fmt(dominanta.numar)} asigurați`}
            color="#2563eb"
          />
        )}
        {pesteMax && (
          <KPICard
            label={`Tranșa ${pesteMax.transa}`}
            value={`${((pesteMax.numar / totalNormaIntreaga) * 100).toFixed(1)}%`}
            sub={`${fmt(pesteMax.numar)} persoane`}
            color="#7c3aed"
          />
        )}
        {subMinim && (
          <KPICard
            label={`Sub salariul minim (${subMinim.transa})`}
            value={`${((subMinim.numar / totalNormaIntreaga) * 100).toFixed(1)}%`}
            sub={`${fmt(subMinim.numar)} persoane`}
            color="#dc2626"
          />
        )}
      </div>

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

      {viewMode === 'bar' && (
        <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">
            Asigurați cu normă întreagă pe tranșe de venit brut — {period.luna} {period.year}
          </h3>
          <ResponsiveContainer width="100%" height={340}>
            <BarChart data={barData} margin={{ top: 5, right: 20, left: 20, bottom: 70 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 10, fill: '#6b7280' }}
                angle={-45}
                textAnchor="end"
                height={80}
                interval={0}
              />
              <YAxis
                tick={{ fontSize: 11, fill: '#6b7280' }}
                tickFormatter={(v) => (v >= 1000000 ? `${(v/1000000).toFixed(1)}M` : v >= 1000 ? `${(v/1000).toFixed(0)}K` : String(v))}
              />
              <Tooltip
                formatter={(val: number, name: string) => [fmt(val), 'Asigurați']}
                labelFormatter={(l) => `Tranșă: ${l} RON`}
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
            Evoluție total asigurați cu normă întreagă
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={trendData} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="luna" tick={{ fontSize: 10, fill: '#6b7280' }} />
              <YAxis
                tick={{ fontSize: 11, fill: '#6b7280' }}
                tickFormatter={(v) => `${(v/1000000).toFixed(2)}M`}
                domain={['auto', 'auto']}
              />
              <Tooltip
                formatter={(val: number) => [fmt(val), 'Total asigurați']}
                contentStyle={{ fontSize: 12, borderRadius: 8 }}
              />
              <Line
                type="monotone"
                dataKey="total"
                stroke="#2563eb"
                strokeWidth={2.5}
                dot={{ r: 4, fill: '#2563eb' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Tabel detaliat */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100">
          <h3 className="text-sm font-semibold text-gray-700">
            Date complete pe tranșe și tipuri de asigurați
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wider">
                <th className="px-4 py-3 text-left">Tranșă venit (RON)</th>
                <th className="px-4 py-3 text-right">Normă întreagă</th>
                <th className="px-4 py-3 text-right hidden md:table-cell">Venit mediu</th>
                <th className="px-4 py-3 text-right hidden lg:table-cell">Timp parțial</th>
                <th className="px-4 py-3 text-right hidden lg:table-cell">Fără contract</th>
                <th className="px-4 py-3 text-right hidden xl:table-cell">Șomaj</th>
                <th className="px-4 py-3 text-right">% din total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {salarii.map((row, i) => {
                const pct = totalNormaIntreaga > 0
                  ? (row.numar / totalNormaIntreaga * 100)
                  : 0;
                return (
                  <tr key={i} className="hover:bg-blue-50/40 transition-colors">
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-2">
                        <div
                          className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                          style={{ background: transaColor(i, salarii.length) }}
                        />
                        <span className="font-medium text-gray-800">{row.transa}</span>
                      </div>
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono text-gray-700">
                      {fmt(row.numar)}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono text-gray-500 hidden md:table-cell">
                      {row.venit_mediu > 0 ? fmt(row.venit_mediu) : '-'}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono text-gray-500 hidden lg:table-cell">
                      {fmt(row.timp_partial)}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono text-gray-500 hidden lg:table-cell">
                      {fmt(row.fara_contract)}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono text-gray-500 hidden xl:table-cell">
                      {fmt(row.somaj)}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-20 bg-gray-100 rounded-full h-1.5">
                          <div
                            className="h-1.5 rounded-full"
                            style={{
                              width: `${Math.min(pct, 100)}%`,
                              background: transaColor(i, salarii.length),
                            }}
                          />
                        </div>
                        <span className="text-xs text-gray-500 w-10 text-right">
                          {pct.toFixed(1)}%
                        </span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr className="bg-blue-50 font-semibold">
                <td className="px-4 py-3 text-gray-700">Total</td>
                <td className="px-4 py-3 text-right font-mono text-blue-700">
                  {fmt(totalNormaIntreaga)}
                </td>
                <td className="hidden md:table-cell" />
                <td className="px-4 py-3 text-right font-mono text-blue-700 hidden lg:table-cell">
                  {fmt(salarii.reduce((s, r) => s + r.timp_partial, 0))}
                </td>
                <td className="px-4 py-3 text-right font-mono text-blue-700 hidden lg:table-cell">
                  {fmt(salarii.reduce((s, r) => s + r.fara_contract, 0))}
                </td>
                <td className="px-4 py-3 text-right font-mono text-blue-700 hidden xl:table-cell">
                  {fmt(salarii.reduce((s, r) => s + r.somaj, 0))}
                </td>
                <td className="px-4 py-3 text-right text-blue-700">100%</td>
              </tr>
            </tfoot>
          </table>
        </div>
        <div className="px-5 py-2 bg-gray-50 text-xs text-gray-400 border-t border-gray-100">
          Notă: „Fără venit" = persoane care au primit doar indemnizație pentru incapacitate temporară de muncă.
          Sursă: declarațiile D112, CNPP.
        </div>
      </div>
    </div>
  );
}

// ─── Tab Județe ───────────────────────────────────────────────────────────────

function TabJudete({ period, allPeriods }: { period: Period; allPeriods: Period[] }) {
  const [sortBy, setSortBy] = useState<'salariu' | 'asigurati' | 'angajatori' | 'judet'>('salariu');
  const [selectedJudet, setSelectedJudet] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'chart' | 'table' | 'trend'>('chart');

  const judete = period.judete;
  if (!judete || judete.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400">
        <p className="text-4xl mb-3">🗺️</p>
        <p>Nu există date pe județe pentru această perioadă.</p>
      </div>
    );
  }

  const sorted = [...judete].sort((a, b) => {
    if (sortBy === 'salariu') return b.salariu_mediu - a.salariu_mediu;
    if (sortBy === 'asigurati') return b.asigurati - a.asigurati;
    if (sortBy === 'angajatori') return b.angajatori - a.angajatori;
    return a.judet.localeCompare(b.judet, 'ro');
  });

  const maxSal = Math.max(...judete.map(d => d.salariu_mediu));
  const minSal = Math.min(...judete.map(d => d.salariu_mediu));
  const totalAsig = judete.reduce((s, d) => s + d.asigurati, 0);
  const totalAng = judete.reduce((s, d) => s + d.angajatori, 0);
  const totalFond = judete.reduce((s, d) => s + d.fond_salarii, 0);
  // Salariu mediu național ponderat = fond total / asigurați total
  const avgSalNational = totalAsig > 0 ? totalFond / totalAsig : 0;

  const top10 = [...judete]
    .sort((a, b) => b.salariu_mediu - a.salariu_mediu)
    .slice(0, 10)
    .map(d => ({
      name: d.judet.length > 13 ? d.judet.substring(0, 13) + '…' : d.judet,
      salariu: d.salariu_mediu,
    }));

  const trendData = selectedJudet
    ? allPeriods
        .filter(p => p.judete?.length > 0)
        .map(p => {
          const row = p.judete.find(r => r.judet === selectedJudet);
          return {
            luna: `${p.luna.substring(0, 3)} ${p.year}`,
            salariu: row?.salariu_mediu ?? 0,
            asigurati: row?.asigurati ?? 0,
          };
        })
        .filter(d => d.salariu > 0)
    : [];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard
          label="Salariu mediu național"
          value={`${fmt(avgSalNational)} RON`}
          sub="ponderat cu nr. asigurați"
          color="#1e40af"
        />
        <KPICard
          label="Cel mai mare salariu"
          value={`${fmt(maxSal)} RON`}
          sub={judete.find(d => d.salariu_mediu === maxSal)?.judet}
          color="#059669"
        />
        <KPICard
          label="Cel mai mic salariu"
          value={`${fmt(minSal)} RON`}
          sub={judete.find(d => d.salariu_mediu === minSal)?.judet}
          color="#dc2626"
        />
        <KPICard
          label="Total angajatori"
          value={fmt(totalAng)}
          sub={`${fmt(totalAsig)} asigurați`}
          color="#7c3aed"
        />
      </div>

      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setViewMode('chart')}
          className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
            viewMode === 'chart'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          Top 10 județe
        </button>
        <button
          onClick={() => setViewMode('table')}
          className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
            viewMode === 'table'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          Toate județele
        </button>
        {selectedJudet && allPeriods.length > 1 && (
          <button
            onClick={() => setViewMode('trend')}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              viewMode === 'trend'
                ? 'bg-blue-600 text-white'
                : 'bg-green-100 text-green-700 hover:bg-green-200'
            }`}
          >
            📈 Evoluție: {selectedJudet}
          </button>
        )}
      </div>

      {viewMode === 'chart' && (
        <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">
            Top 10 județe după salariul mediu brut — {period.luna} {period.year}
          </h3>
          <ResponsiveContainer width="100%" height={340}>
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
                formatter={(val: number) => [`${fmt(val)} RON`, 'Salariu mediu brut']}
                contentStyle={{ fontSize: 12, borderRadius: 8 }}
              />
              <Bar dataKey="salariu" radius={[0, 4, 4, 0]}>
                {top10.map((_, i) => (
                  <Cell key={i} fill={BLUE_PALETTE[Math.min(i, BLUE_PALETTE.length - 1)]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <p className="text-xs text-gray-400 mt-2 text-center">
            Medie națională ponderată: {fmt(avgSalNational)} RON
          </p>
        </div>
      )}

      {viewMode === 'trend' && selectedJudet && trendData.length > 1 && (
        <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">
            Evoluție salariu mediu brut — {selectedJudet}
          </h3>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="luna" tick={{ fontSize: 11, fill: '#6b7280' }} />
              <YAxis
                tick={{ fontSize: 11, fill: '#6b7280' }}
                tickFormatter={(v) => `${(v/1000).toFixed(1)}K`}
                domain={['auto', 'auto']}
              />
              <Tooltip
                formatter={(val: number) => [`${fmt(val)} RON`, 'Salariu mediu brut']}
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

      {(viewMode === 'table' || viewMode === 'trend') && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100 flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-gray-700">Date pe județe</h3>
            <div className="flex gap-2 text-xs items-center">
              <span className="text-gray-500">Sortare:</span>
              {([['salariu', 'Salariu'], ['asigurati', 'Asigurați'], ['angajatori', 'Angajatori'], ['judet', 'Alfabet']] as const).map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => setSortBy(key)}
                  className={`px-2.5 py-1 rounded-full transition-colors ${
                    sortBy === key
                      ? 'bg-blue-100 text-blue-700 font-medium'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <div className="overflow-x-auto max-h-[520px] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-gray-50 z-10">
                <tr className="text-xs text-gray-500 uppercase tracking-wider">
                  <th className="px-4 py-3 text-left">#</th>
                  <th className="px-4 py-3 text-left">Județ</th>
                  <th className="px-4 py-3 text-right">Salariu mediu brut</th>
                  <th className="px-4 py-3 text-right hidden md:table-cell">vs. medie</th>
                  <th className="px-4 py-3 text-right hidden md:table-cell">Asigurați</th>
                  <th className="px-4 py-3 text-right hidden lg:table-cell">Angajatori</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {sorted.map((row, i) => {
                  const diff = row.salariu_mediu - avgSalNational;
                  const diffPct = (diff / avgSalNational * 100).toFixed(1);
                  const isSelected = selectedJudet === row.judet;
                  return (
                    <tr
                      key={row.judet}
                      onClick={() => {
                        if (isSelected) {
                          setSelectedJudet(null);
                        } else {
                          setSelectedJudet(row.judet);
                          if (allPeriods.length > 1) setViewMode('trend');
                        }
                      }}
                      className={`transition-colors cursor-pointer ${
                        isSelected
                          ? 'bg-blue-50 ring-1 ring-inset ring-blue-200'
                          : 'hover:bg-gray-50'
                      }`}
                    >
                      <td className="px-4 py-2.5 text-gray-400 text-xs">{i + 1}</td>
                      <td className="px-4 py-2.5">
                        <span className="font-medium text-gray-800">{row.judet}</span>
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono font-semibold text-gray-800">
                        {fmt(row.salariu_mediu)} RON
                      </td>
                      <td className="px-4 py-2.5 text-right hidden md:table-cell">
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                          diff > 0 ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-600'
                        }`}>
                          {diff > 0 ? '+' : ''}{diffPct}%
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono text-gray-600 hidden md:table-cell">
                        {fmt(row.asigurati)}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono text-gray-600 hidden lg:table-cell">
                        {fmt(row.angajatori)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {allPeriods.length > 1 && (
            <div className="px-5 py-2 bg-gray-50 text-xs text-gray-400 border-t border-gray-100">
              Click pe un județ pentru a vedea evoluția salariului în timp
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

        {currentPeriod ? (
          <>
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
