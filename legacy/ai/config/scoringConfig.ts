import { ScoringWeights } from '../../types/scoring.types';

export const DEFAULT_WEIGHTS: ScoringWeights = {
  experience: 0.25,
  quality: 0.30,
  reliability: 0.20,
  match: 0.15,
  reputation: 0.10
};

export const CATEGORY_WEIGHTS: Record<string, ScoringWeights> = {
  'Elektrik': {
    experience: 0.30,
    quality: 0.35,
    reliability: 0.20,
    match: 0.10,
    reputation: 0.05
  },
  'İT': {
    experience: 0.20,
    quality: 0.35,
    reliability: 0.15,
    match: 0.20,
    reputation: 0.10
  },
  'Tikinti': {
    experience: 0.30,
    quality: 0.30,
    reliability: 0.25,
    match: 0.10,
    reputation: 0.05
  },
  'Su': {
    experience: 0.25,
    quality: 0.30,
    reliability: 0.25,
    match: 0.15,
    reputation: 0.05
  }
};

export const URGENCY_MULTIPLIERS = {
  low: 1.0,
  medium: 1.1,
  high: 1.2
};

export const LOCATION_BONUS = 5;
export const CERTIFICATION_BONUS = 3;
export const MIN_REVIEWS_FOR_CONFIDENCE = 5;