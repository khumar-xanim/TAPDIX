/**
 * Runs the ORIGINAL TypeScript scoring engine on seeded + hand-made cases and writes
 * ground-truth outputs to ml/tests/fixtures/legacy_cases.json.
 *
 *   npx -y tsx legacy/tools/gen_fixtures.ts
 *
 * The Python port (tapdix_ml.baseline) must reproduce these outputs exactly.
 */
import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { ScoringEngine } from '../ai/scoringEngine';
import type { WorkerProfile, JobListing, Review } from '../types/scoring.types';

// Freeze the clock: calculateReliabilityScore uses Date.now().
const FIXED_NOW_MS = Date.UTC(2026, 9, 23, 12, 0, 0);
Date.now = () => FIXED_NOW_MS;

// Seeded RNG (mulberry32) so fixtures are reproducible.
function rng(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rand = rng(20261023);
const ri = (lo: number, hi: number) => lo + Math.floor(rand() * (hi - lo + 1));
const pick = <T,>(xs: T[]): T => xs[Math.floor(rand() * xs.length)];

const CATS = ['Elektrik', 'İT', 'Tikinti', 'Su', 'Texniki xidmət', 'Boyama', 'Santexnika'];
const LOCS = ['Bakı', 'Sumqayıt', 'Gəncə', 'Bakı, Nəsimi', 'Bakı, Yasamal', 'Mingəçevir', 'İstanbul', 'BAKI'];
const CERTS = ['ISO', 'OSHA', 'Peşə sertifikatı', 'Elektrik təhlükəsizliyi', 'Cisco', 'AWS'];
const DAY = 86_400_000;

// Plain-JSON shapes (dates as ISO strings) — what the Python side loads.
type RevJ = Omit<Review, 'date'> & { date: string };
type WorkerJ = Omit<WorkerProfile, 'reviews'> & { reviews: RevJ[] };

const r1 = (x: number) => Math.round(x * 10) / 10;
function makeReview(): RevJ {
  // 40% of reviews carry one-decimal scores (e.g. 4.3) so float summation order is exercised.
  const frac = rand() < 0.4;
  const base = frac ? r1(1 + rand() * 4) : ri(1, 5);
  const j = () => Math.max(1, Math.min(5, frac ? r1(base + (rand() - 0.5)) : base + ri(-1, 1)));
  return {
    clientId: `c${ri(1, 8)}`,
    rating: base,
    quality: j(), communication: j(), professionalism: j(), timeliness: j(),
    date: new Date(FIXED_NOW_MS - ri(0, 400) * DAY - ri(0, 86_399) * 1000).toISOString(),
  };
}
let wid = 0;
function makeWorker(): WorkerJ {
  const n = ri(0, 14);
  const exp = rand() < 0.2 ? ri(0, 24) + 0.5 : ri(0, 25);
  const certN = ri(0, 4);
  return {
    id: `w${++wid}`,
    category: pick(CATS),
    location: pick(LOCS),
    age: ri(17, 65),
    experience: exp,
    completedJobs: ri(0, 150),
    rating: Math.round((1 + rand() * 4) * 4) / 4, // quarter steps -> exact .25/.75 ties hit toFixed
    successRate: ri(40, 100) + (rand() < 0.3 ? 0.5 : 0),
    responseTime: ri(5, 600),
    certifications: Array.from({ length: certN }, () => pick(CERTS)),
    reviews: Array.from({ length: n }, makeReview),
  };
}
let jid = 0;
const makeJob = (): JobListing => ({
  id: `j${++jid}`, category: pick(CATS), location: pick(LOCS), complexity: ri(1, 10),
});

// Engine expects Date objects; give it a fresh deep copy each call (engine mutates review order).
const toEngine = (w: WorkerJ): WorkerProfile => ({
  ...w, certifications: [...w.certifications],
  reviews: w.reviews.map((r) => ({ ...r, date: new Date(r.date) })),
});
const clone = <T,>(x: T): T => JSON.parse(JSON.stringify(x));

const out: any = { meta: { fixedNowMs: FIXED_NOW_MS, generator: 'legacy/tools/gen_fixtures.ts' }, score: [], recommend: [], personalized: [], similar: [] };

// ---- hand-made edge cases -------------------------------------------------
const edgeWorkers: WorkerJ[] = [];
let eid = 0;
const ew = (o: Partial<WorkerJ>): WorkerJ => ({ ...makeWorker(), ...o, id: `e${++eid}` });
const rv = (rating: number, daysAgo: number, c = 'c1'): RevJ => ({
  clientId: c, rating, quality: rating, communication: rating, professionalism: rating, timeliness: rating,
  date: new Date(FIXED_NOW_MS - daysAgo * DAY).toISOString(),
});
edgeWorkers.push(
  ew({ category: 'Elektrik', location: 'Bakı', reviews: [], completedJobs: 0, experience: 0, rating: 0, certifications: [] }),
  ew({ category: 'Elektrik', location: 'Bakı', reviews: [rv(5, 3)], rating: 5 }),                                  // 1 perfect review
  ew({ category: 'Elektrik', location: 'Bakı', reviews: [rv(5, 3), rv(4, 9), rv(5, 20)], rating: 4.67 }),          // exactly 3 -> trend stable
  ew({ category: 'Elektrik', location: 'Bakı', reviews: [rv(5, 1), rv(5, 2), rv(5, 3), rv(3, 4)], rating: 4.25 }), // 4 reviews, toFixed tie 4.25
  ew({ category: 'Su', location: '', rating: 4.25 }),                                                              // empty location
  ew({ category: 'Su', location: 'İstanbul', rating: 4.75 }),
  ew({ category: 'Tikinti', location: 'BAKI', age: 18 }),                                                          // age-18 = 0 -> max(...,1)
  ew({ category: 'Tikinti', location: 'Bakı', age: 17, experience: 12 }),
  ew({ category: 'İT', location: 'Bakı', certifications: ['a', 'b', 'c', 'd', 'e', 'f', 'g'], experience: 30, completedJobs: 400, rating: 5, successRate: 100, responseTime: 1,
       reviews: Array.from({ length: 12 }, (_, i) => rv(5, i + 1, `c${i}`)) }),                                      // everything maxed -> cap at 100
  ew({ category: 'İT', location: 'Bakı', experience: 5.5, reviews: Array.from({ length: 8 }, (_, i) => rv(i < 3 ? 2 : 5, i * 15 + 1, `c${i}`)) }), // declining
  ew({ category: 'İT', location: 'Bakı', experience: 5, reviews: Array.from({ length: 8 }, (_, i) => rv(i < 3 ? 5 : 2, i * 15 + 1, `c${i}`)) }), // improving
  ew({ category: 'Texniki xidmət', location: 'Bakı', responseTime: 900 }),                                          // response score floors at 0
);
const edgeJobs: JobListing[] = [
  { id: 'ej1', category: 'Elektrik', location: 'Bakı', complexity: 10 },
  { id: 'ej2', category: 'Su', location: '', complexity: 1 },
  { id: 'ej3', category: 'Santexnika', location: 'İstanbul', complexity: 5 },
  { id: 'ej4', category: 'İT', location: 'baki', complexity: 7 },
];
for (const w of edgeWorkers) for (const j of edgeJobs)
  out.score.push({ tag: 'edge', worker: clone(w), job: j, expected: ScoringEngine.scoreWorker(toEngine(w), j) });

// ---- random pairs ---------------------------------------------------------
for (let i = 0; i < 200; i++) {
  const w = makeWorker(); const j = makeJob();
  out.score.push({ tag: 'random', worker: clone(w), job: j, expected: ScoringEngine.scoreWorker(toEngine(w), j) });
}
// ---- recommend ------------------------------------------------------------
for (let i = 0; i < 25; i++) {
  const ws = Array.from({ length: ri(8, 25) }, makeWorker); const j = makeJob(); const limit = pick([1, 3, 5, 10, 50]);
  out.recommend.push({ workers: clone(ws), job: j, limit, expected: ScoringEngine.recommendWorkers(ws.map(toEngine), j, limit) });
}
// ---- personalized / similar ----------------------------------------------
for (let i = 0; i < 25; i++) {
  const ws = Array.from({ length: ri(8, 25) }, makeWorker);
  const hist = Array.from({ length: pick([0, 0, 1, 3, 6]) }, makeJob); const limit = pick([1, 3, 5, 10]);
  out.personalized.push({ workers: clone(ws), history: hist, limit,
    expected: ScoringEngine.getPersonalizedRecommendations(ws.map(toEngine), hist, limit).map((w) => w.id) });
  const tj = makeJob();
  out.similar.push({ workers: clone(ws), job: tj, limit,
    expected: ScoringEngine.findSimilarWorkers(tj, ws.map(toEngine), limit).map((w) => w.id) });
}

const here = dirname(fileURLToPath(import.meta.url));
const dest = resolve(here, '../../ml/tests/fixtures/legacy_cases.json');
mkdirSync(dirname(dest), { recursive: true });
writeFileSync(dest, JSON.stringify(out));
console.log(`wrote ${dest}: score=${out.score.length} recommend=${out.recommend.length} personalized=${out.personalized.length} similar=${out.similar.length}`);
