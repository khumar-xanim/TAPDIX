// RECONSTRUCTED from how the legacy ai/ files use these types.
// The original src/types/scoring.types.ts was not provided. If you still have it,
// diff it against this file — only the fields the engine reads matter for parity.

export interface Review {
  clientId: string;
  rating: number;          // 1-5 overall
  quality: number;         // 1-5
  communication: number;   // 1-5
  professionalism: number; // 1-5
  timeliness: number;      // 1-5
  date: Date;
}

export interface WorkerProfile {
  id: string;
  category: string;
  location: string;
  age: number;
  experience: number;      // years
  completedJobs: number;
  rating: number;          // 0-5
  successRate: number;     // 0-100
  responseTime: number;    // minutes
  certifications: string[];
  reviews: Review[];
}

export interface JobListing {
  id: string;
  category: string;
  location: string;
  complexity: number;      // 1-10
}

export interface ScoringWeights {
  experience: number;
  quality: number;
  reliability: number;
  match: number;
  reputation: number;
}

export interface ScoringResult {
  workerId: string;
  totalScore: number;
  breakdown: {
    experienceScore: number;
    qualityScore: number;
    reliabilityScore: number;
    matchScore: number;
    reputationScore: number;
  };
  confidence: number;
  recommendation: 'highly_recommended' | 'recommended' | 'suitable' | 'not_recommended';
  reasoning: string[];
}
