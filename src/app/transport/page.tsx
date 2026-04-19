import claseData from '@/data/transport/clase_transportatori.json'

interface ClasaTransportator {
  Denumire: string
  NrOperatori: number
  NrCamioane: number
  NrCamioaneMin: number
  NrCamioaneMax: number
}

export default function TransportPage() {
  const { date, actualizat, total, sursa } = claseData as {
    date: ClasaTransportator[]
    actualizat: string
    total: number
    sursa: string
  }

  return (
    <main className="max-w-5xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-1">Transport Marfă</h1>
      <p className="text-sm text-gray-500 mb-6">
        Sursă: {sursa} · Actualizat: {actualizat} · {total} clase
      </p>

      {date.length === 0 ? (
        <p className="text-gray-400">Nu există date disponibile.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-gray-100 text-left">
                <th className="p-3 border border-gray-200">#</th>
                <th className="p-3 border border-gray-200">Clasă</th>
                <th className="p-3 border border-gray-200 text-right">Nr. Operatori</th>
                <th className="p-3 border border-gray-200 text-right">Nr. Camioane</th>
                <th className="p-3 border border-gray-200 text-right">Min</th>
                <th className="p-3 border border-gray-200 text-right">Max</th>
              </tr>
            </thead>
            <tbody>
              {date.map((row, i) => (
                <tr key={i} className="hover:bg-gray-50 transition-colors">
                  <td className="p-3 border border-gray-200 text-gray-400">{i + 1}</td>
                  <td className="p-3 border border-gray-200 font-medium">{row.Denumire}</td>
                  <td className="p-3 border border-gray-200 text-right">{row.NrOperatori?.toLocaleString('ro-RO')}</td>
                  <td className="p-3 border border-gray-200 text-right">{row.NrCamioane?.toLocaleString('ro-RO')}</td>
                  <td className="p-3 border border-gray-200 text-right">{row.NrCamioaneMin}</td>
                  <td className="p-3 border border-gray-200 text-right">{row.NrCamioaneMax}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  )
}
