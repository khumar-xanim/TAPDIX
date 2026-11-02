import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, vi } from 'vitest'
import App from './App'
import type { AnalyzeResponse, Meta } from './api'

const META: Meta = {
  categories: [{ slug: 'plumbing', name_en: 'Plumbing', name_az: 'Santexnika' }],
  cities: { Bakı: ['Nəsimi', 'Nərimanov'], Sumqayıt: ['Mərkəz'] },
  urgencies: ['Low', 'Normal', 'Urgent', 'Emergency'],
  photo_presets: [{ id: 'laptop', label: 'Photo: a laptop', detections: [{ label: 'laptop', confidence: 0.85 }] }],
  examples: ['Mətbəx kranı su axıdır, təcili lazımdır', 'Kömək lazımdır'],
}

const CLEAR: AnalyzeResponse = {
  text: {
    category: 'plumbing',
    category_prob: 0.93,
    problem_type: 'faucet_leak',
    problem_prob: 0.9,
    top_k: [{ problem_type: 'faucet_leak', name_az: 'Kran su axıdır', probability: 0.9 }],
    keywords: [{ word: 'kranin', weight: 0.7 }],
  },
  decision: {
    source: 'text',
    category: 'plumbing',
    category_name_az: 'Santexnika',
    problem_type: 'faucet_leak',
    problem_name_az: 'Kran su axıdır',
    confidence: 0.93,
    reasons: ['Elanın mətni kifayət qədər aydındır'],
    request_photo: false,
    clarification_az: null,
    alternatives: [],
  },
  matches: [
    {
      master: {
        master_id: 'abcdef12-0000-0000-0000-000000000000',
        main_category: 'plumbing',
        years_experience: 7,
        average_rating: 4.5,
        rating_count: 20,
        verification_status: 'Verified',
        accepts_emergency_jobs: true,
      },
      score: 0.81,
      reasons: ['Bacarıq: Kran təmiri', 'Eyni rayon'],
    },
  ],
  note: 'Masters are synthetic demo data.',
}

function mockApi(analyzeResponse: unknown, analyzeStatus = 200) {
  const fn = vi.fn((url: string) => {
    const ok = url === '/api/meta' || analyzeStatus === 200
    const body = url === '/api/meta' ? META : analyzeResponse
    return Promise.resolve({ ok, status: url === '/api/meta' ? 200 : analyzeStatus, json: () => Promise.resolve(body) })
  })
  vi.stubGlobal('fetch', fn)
  return fn
}

afterEach(() => vi.unstubAllGlobals())

test('renders the brand and the synthetic-data warning', async () => {
  mockApi(CLEAR)
  render(<App />)
  expect(screen.getByText('Tapdix')).toBeInTheDocument()
  expect(screen.getByText(/synthetic data/i)).toBeInTheDocument()
  await screen.findByRole('button', { name: /Mətbəx kranı su axıdır/ })
})

test('analyzing shows the decision, the keywords and the ranked master', async () => {
  const fetchMock = mockApi(CLEAR)
  render(<App />)
  await waitFor(() => expect((screen.getByLabelText(/Describe the problem/) as HTMLTextAreaElement).value).toContain('kranı'))
  fireEvent.change(screen.getByLabelText(/Urgency/), { target: { value: 'Urgent' } })
  fireEvent.click(screen.getByRole('button', { name: 'Analyze' }))

  expect(await screen.findByText('Understood from the text')).toBeInTheDocument()
  expect(screen.getByText('kranin')).toBeInTheDocument()
  expect(screen.getByText(/1\. Master abcdef12/)).toBeInTheDocument()
  expect(screen.getByText('Bacarıq: Kran təmiri')).toBeInTheDocument()

  const call = fetchMock.mock.calls.find((c) => c[0] === '/api/analyze') as unknown as [string, RequestInit]
  const sent = JSON.parse(call[1].body as string)
  expect(sent).toMatchObject({ urgency: 'Urgent', city: 'Bakı', district: 'Nəsimi', detections: [] })
})

test('changing the city changes the districts offered', async () => {
  mockApi(CLEAR)
  render(<App />)
  await screen.findByRole('option', { name: 'Sumqayıt' })
  fireEvent.change(screen.getByLabelText(/City/), { target: { value: 'Sumqayıt' } })
  expect(await screen.findByRole('option', { name: 'Mərkəz' })).toBeInTheDocument()
  expect((screen.getByLabelText(/District/) as HTMLSelectElement).value).toBe('Mərkəz')
})

test('a vague listing shows the question for the customer', async () => {
  const vague = {
    ...CLEAR,
    decision: {
      ...CLEAR.decision,
      source: 'ask_user',
      category: null,
      problem_type: null,
      clarification_az: 'Problemi bir az ətraflı yazın və ya şəkil əlavə edin.',
      request_photo: true,
    },
    matches: [],
  }
  mockApi(vague)
  render(<App />)
  await screen.findByRole('button', { name: 'Kömək lazımdır' })
  fireEvent.click(screen.getByRole('button', { name: 'Analyze' }))
  expect(await screen.findByText(/Not clear enough/)).toBeInTheDocument()
  expect(screen.getByText(/Problemi bir az ətraflı yazın/)).toBeInTheDocument()
  expect(screen.getByText(/nothing to match/)).toBeInTheDocument()
})

test('API errors are shown, not swallowed', async () => {
  mockApi({ detail: 'boom' }, 422)
  render(<App />)
  await screen.findByRole('button', { name: 'Kömək lazımdır' })
  fireEvent.click(screen.getByRole('button', { name: 'Analyze' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('API error 422: boom')
})
