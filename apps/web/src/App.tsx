import { Briefcase } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { analyze, getMeta } from './api'
import type { AnalyzeResponse, Meta, Urgency } from './api'
import ResultView from './components/ResultView'

const field = 'w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus:border-[#FF8C32] focus:outline-none'

export default function App() {
  const [meta, setMeta] = useState<Meta | null>(null)
  const [description, setDescription] = useState('')
  const [title, setTitle] = useState('')
  const [city, setCity] = useState('Bakı')
  const [district, setDistrict] = useState('Nəsimi')
  const [urgency, setUrgency] = useState<Urgency>('Normal')
  const [presetId, setPresetId] = useState('')
  const [result, setResult] = useState<AnalyzeResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getMeta()
      .then((m) => {
        setMeta(m)
        setDescription((d) => d || m.examples[0] || '')
      })
      .catch((e: Error) => setError(e.message))
  }, [])

  const districts = meta?.cities[city] ?? []

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const preset = meta?.photo_presets.find((p) => p.id === presetId)
      setResult(
        await analyze({ title, description, city, district, urgency, detections: preset?.detections ?? [], k: 5 }),
      )
    } catch (err) {
      setResult(null)
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#F9F9F9] text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <h1 className="flex items-center gap-2 text-2xl font-bold text-[#FF8C32]">
            <Briefcase /> Tapdix
          </h1>
          <p className="hidden text-sm text-slate-500 sm:block">Describe the problem. We find the right master.</p>
        </div>
      </header>

      <main className="mx-auto grid max-w-6xl gap-6 px-4 py-6 lg:grid-cols-2">
        <section aria-label="Listing form" className="rounded-xl border border-slate-200 bg-white p-5">
          <p className="mb-4 rounded-md bg-amber-50 p-2 text-xs text-amber-900">
            Prototype on <strong>synthetic data</strong>: masters are fake and the model has never seen a real customer.
            No login, nothing is stored.
          </p>
          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label htmlFor="description" className="mb-1 block text-sm font-medium">
                Describe the problem
              </label>
              <textarea
                id="description"
                className={field}
                rows={4}
                maxLength={2000}
                required
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
              <div className="mt-2 flex flex-wrap gap-1.5">
                {meta?.examples.map((ex) => (
                  <button
                    type="button"
                    key={ex}
                    onClick={() => setDescription(ex)}
                    className="rounded-full border border-slate-300 px-2 py-0.5 text-xs text-slate-600 hover:border-[#FF8C32]"
                  >
                    {ex}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label htmlFor="title" className="mb-1 block text-sm font-medium">
                Title <span className="font-normal text-slate-500">(optional)</span>
              </label>
              <input id="title" className={field} maxLength={200} value={title} onChange={(e) => setTitle(e.target.value)} />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="city" className="mb-1 block text-sm font-medium">
                  City
                </label>
                <select
                  id="city"
                  className={field}
                  value={city}
                  onChange={(e) => {
                    setCity(e.target.value)
                    setDistrict(meta?.cities[e.target.value]?.[0] ?? '')
                  }}
                >
                  {Object.keys(meta?.cities ?? { Bakı: [] }).map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="district" className="mb-1 block text-sm font-medium">
                  District
                </label>
                <select id="district" className={field} value={district} onChange={(e) => setDistrict(e.target.value)}>
                  {(districts.length ? districts : [district]).map((d) => (
                    <option key={d}>{d}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="urgency" className="mb-1 block text-sm font-medium">
                  Urgency
                </label>
                <select id="urgency" className={field} value={urgency} onChange={(e) => setUrgency(e.target.value as Urgency)}>
                  {(meta?.urgencies ?? ['Normal']).map((u) => (
                    <option key={u}>{u}</option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="photo" className="mb-1 block text-sm font-medium">
                  Simulated photo
                </label>
                <select id="photo" className={field} value={presetId} onChange={(e) => setPresetId(e.target.value)}>
                  <option value="">No photo</option>
                  {meta?.photo_presets.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !description.trim()}
              className="w-full rounded-md bg-[#FF8C32] px-4 py-2 font-semibold text-white hover:bg-[#e87d27] disabled:opacity-50"
            >
              {loading ? 'Analyzing…' : 'Analyze'}
            </button>
          </form>
        </section>

        <section aria-label="Result" className="rounded-xl border border-slate-200 bg-slate-50 p-5">
          {error && (
            <p role="alert" className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800">
              {error}
            </p>
          )}
          {!error && !result && <p className="text-sm text-slate-500">The result appears here.</p>}
          {result && <ResultView result={result} />}
        </section>
      </main>
    </div>
  )
}
