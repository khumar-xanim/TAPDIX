import type { AnalyzeResponse, Source } from '../api'

const BANNER: Record<Source, { title: string; cls: string }> = {
  text: { title: 'Understood from the text', cls: 'border-emerald-300 bg-emerald-50 text-emerald-900' },
  photo: { title: 'Text was unclear, so the photo was used', cls: 'border-sky-300 bg-sky-50 text-sky-900' },
  'text+photo': { title: 'Text and photo agree', cls: 'border-emerald-300 bg-emerald-50 text-emerald-900' },
  ask_user: { title: 'Not clear enough: asking the customer', cls: 'border-amber-300 bg-amber-50 text-amber-900' },
}

const pct = (x: number) => `${Math.round(x * 100)}%`

function Bar({ value }: { value: number }) {
  return (
    <div className="h-2 w-full rounded bg-slate-200" role="presentation">
      <div className="h-2 rounded bg-[#FF8C32]" style={{ width: pct(value) }} />
    </div>
  )
}

export default function ResultView({ result }: { result: AnalyzeResponse }) {
  const { decision: d, text: t, matches } = result
  const banner = BANNER[d.source]
  return (
    <div className="space-y-5" aria-live="polite">
      <div className={`rounded-lg border p-4 ${banner.cls}`}>
        <p className="font-semibold">{banner.title}</p>
        {d.category ? (
          <p className="mt-1 text-sm">
            <span className="font-medium">{d.category_name_az}</span> <span className="opacity-70">({d.category})</span>
            {d.problem_type && (
              <>
                {' '}
                &rarr; <span className="font-medium">{d.problem_name_az}</span>{' '}
                <span className="opacity-70">({d.problem_type})</span>
              </>
            )}
            <span className="ml-2 opacity-70">confidence {pct(d.confidence)}</span>
          </p>
        ) : (
          <p className="mt-1 text-sm">No category chosen yet.</p>
        )}
        {d.clarification_az && (
          <p className="mt-2 rounded bg-white/70 p-2 text-sm">
            Question for the customer: <span className="font-medium">{d.clarification_az}</span>
          </p>
        )}
        {d.request_photo && <p className="mt-2 text-sm">Also asking the customer to add a photo.</p>}
      </div>

      <section>
        <h3 className="mb-1 text-sm font-semibold text-slate-700">Why</h3>
        <ul className="list-disc pl-5 text-sm text-slate-700">
          {d.reasons.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      </section>

      <section>
        <h3 className="mb-1 text-sm font-semibold text-slate-700">What the text model saw</h3>
        <div className="mb-2 flex flex-wrap gap-1">
          {t.keywords.length ? (
            t.keywords.map((k) => (
              <span key={k.word} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
                {k.word}
              </span>
            ))
          ) : (
            <span className="text-xs text-slate-500">No telling words found (text too vague).</span>
          )}
        </div>
        <ul className="space-y-1.5">
          {t.top_k.map((p) => (
            <li key={p.problem_type} className="text-xs text-slate-600">
              <div className="mb-0.5 flex justify-between">
                <span>
                  {p.name_az} <span className="opacity-60">({p.problem_type})</span>
                </span>
                <span>{pct(p.probability)}</span>
              </div>
              <Bar value={p.probability} />
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h3 className="mb-1 text-sm font-semibold text-slate-700">Ranked masters</h3>
        {matches.length === 0 ? (
          <p className="text-sm text-slate-500">None yet: nothing to match until the problem is clear.</p>
        ) : (
          <ol className="space-y-2">
            {matches.map((m, i) => (
              <li key={m.master.master_id} className="rounded-lg border border-slate-200 bg-white p-3">
                <div className="flex items-baseline justify-between">
                  <span className="font-medium">
                    {i + 1}. Master {m.master.master_id.slice(0, 8)}
                  </span>
                  <span className="text-sm text-slate-600">score {m.score.toFixed(2)}</span>
                </div>
                <p className="mt-0.5 text-xs text-slate-500">
                  {m.master.rating_count > 0
                    ? `${m.master.average_rating.toFixed(1)} ★ (${m.master.rating_count} reviews)`
                    : 'no reviews yet'}{' '}
                  · {m.master.years_experience} yrs · {m.master.verification_status}
                </p>
                <div className="mt-1 flex flex-wrap gap-1">
                  {m.reasons.map((r) => (
                    <span key={r} className="rounded bg-orange-50 px-1.5 py-0.5 text-xs text-orange-900">
                      {r}
                    </span>
                  ))}
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>
      <p className="text-xs text-slate-500">{result.note}</p>
    </div>
  )
}
