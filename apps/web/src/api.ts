// Types mirror services/api/app/schemas.py. Requests go through the Vite dev proxy (/api -> :8000).

export type Urgency = 'Low' | 'Normal' | 'Urgent' | 'Emergency'
export type Source = 'text' | 'photo' | 'text+photo' | 'ask_user'

export interface Detection {
  label: string
  confidence: number
}
export interface PhotoPreset {
  id: string
  label: string
  detections: Detection[]
}
export interface Meta {
  categories: { slug: string; name_en: string; name_az: string }[]
  cities: Record<string, string[]>
  urgencies: Urgency[]
  photo_presets: PhotoPreset[]
  examples: string[]
}
export interface AnalyzeRequest {
  title: string
  description: string
  city: string
  district: string
  urgency: Urgency
  detections: Detection[]
  k: number
}
export interface Decision {
  source: Source
  category: string | null
  category_name_az: string | null
  problem_type: string | null
  problem_name_az: string | null
  confidence: number
  reasons: string[]
  request_photo: boolean
  clarification_az: string | null
  alternatives: string[]
}
export interface Match {
  master: {
    master_id: string
    main_category: string
    years_experience: number
    average_rating: number
    rating_count: number
    verification_status: string
    accepts_emergency_jobs: boolean
  }
  score: number
  reasons: string[]
}
export interface AnalyzeResponse {
  text: {
    category: string
    category_prob: number
    problem_type: string
    problem_prob: number
    top_k: { problem_type: string; name_az: string; probability: number }[]
    keywords: { word: string; weight: number }[]
  }
  decision: Decision
  matches: Match[]
  note: string
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(url, init)
  } catch {
    throw new Error('Cannot reach the API. Is it running on port 8000? (see docs/RUN_LOCALLY.md)')
  }
  if (!res.ok) {
    let detail = ''
    try {
      const body = (await res.json()) as { detail?: unknown }
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail ?? '')
    } catch {
      /* response had no JSON body */
    }
    throw new Error(`API error ${res.status}${detail ? `: ${detail}` : ''}`)
  }
  return (await res.json()) as T
}

export const getMeta = () => request<Meta>('/api/meta')

export const analyze = (body: AnalyzeRequest) =>
  request<AnalyzeResponse>('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
