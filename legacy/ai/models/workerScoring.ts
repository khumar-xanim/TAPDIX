import { WorkerProfile, JobListing, ScoringResult, ScoringWeights } from '../../types/scoring.types';
import { ScoreCalculator } from '../utils/scoreCalculator';
import { DataProcessor } from '../utils/dataProcessor';
import { DEFAULT_WEIGHTS, CATEGORY_WEIGHTS, LOCATION_BONUS, CERTIFICATION_BONUS, MIN_REVIEWS_FOR_CONFIDENCE } from '../config/scoringConfig';

export class WorkerScoringModel {
  private weights: ScoringWeights;

  constructor(category?: string) {
    this.weights = category && CATEGORY_WEIGHTS[category] 
      ? CATEGORY_WEIGHTS[category] 
      : DEFAULT_WEIGHTS;
  }

  scoreWorker(worker: WorkerProfile, job: JobListing): ScoringResult {
    const experienceScore = ScoreCalculator.calculateExperienceScore(worker);
    const qualityScore = ScoreCalculator.calculateQualityScore(worker);
    const reliabilityScore = ScoreCalculator.calculateReliabilityScore(worker);
    const reputationScore = ScoreCalculator.calculateReputationScore(worker);
    
    const categoryMatch = DataProcessor.checkCategoryMatch(worker, job);
    const complexityMatch = DataProcessor.checkComplexityMatch(worker, job);
    const matchScore = (categoryMatch * 0.7) + (complexityMatch * 0.3);
    
    let bonus = 0;
    if (DataProcessor.checkLocationMatch(worker.location, job.location)) {
      bonus += LOCATION_BONUS;
    }
    if (worker.certifications.length > 0) {
      bonus += CERTIFICATION_BONUS * worker.certifications.length;
    }
    
    const totalScore = Math.min(100, 
      (experienceScore * this.weights.experience) +
      (qualityScore * this.weights.quality) +
      (reliabilityScore * this.weights.reliability) +
      (matchScore * this.weights.match) +
      (reputationScore * this.weights.reputation) +
      bonus
    );
    
    const trend = DataProcessor.analyzeTrend(worker.reviews);
    const trendAdjustment = trend === 'improving' ? 2 : trend === 'declining' ? -3 : 0;
    const adjustedScore = Math.max(0, Math.min(100, totalScore + trendAdjustment));
    
    const confidence = this.calculateConfidence(worker);
    const recommendation = this.getRecommendation(adjustedScore, confidence);
    const reasoning = this.generateReasoning(worker, job, {
      experienceScore,
      qualityScore,
      reliabilityScore,
      matchScore,
      reputationScore
    }, trend);
    
    return {
      workerId: worker.id,
      totalScore: Math.round(adjustedScore * 10) / 10,
      breakdown: {
        experienceScore: Math.round(experienceScore * 10) / 10,
        qualityScore: Math.round(qualityScore * 10) / 10,
        reliabilityScore: Math.round(reliabilityScore * 10) / 10,
        matchScore: Math.round(matchScore * 10) / 10,
        reputationScore: Math.round(reputationScore * 10) / 10
      },
      confidence: Math.round(confidence * 10) / 10,
      recommendation,
      reasoning
    };
  }

  private calculateConfidence(worker: WorkerProfile): number {
    let confidence = 50;
    
    if (worker.reviews.length >= MIN_REVIEWS_FOR_CONFIDENCE * 2) {
      confidence += 30;
    } else if (worker.reviews.length >= MIN_REVIEWS_FOR_CONFIDENCE) {
      confidence += 20;
    } else {
      confidence += worker.reviews.length * 3;
    }
    
    confidence += Math.min(worker.completedJobs * 0.5, 15);
    confidence += Math.min(worker.experience * 0.5, 5);
    
    return Math.min(100, confidence);
  }

  private getRecommendation(score: number, confidence: number): ScoringResult['recommendation'] {
    if (score >= 85 && confidence >= 70) return 'highly_recommended';
    if (score >= 70 && confidence >= 60) return 'recommended';
    if (score >= 55) return 'suitable';
    return 'not_recommended';
  }

  private generateReasoning(
    worker: WorkerProfile, 
    job: JobListing, 
    breakdown: ScoringResult['breakdown'],
    trend: 'improving' | 'stable' | 'declining'
  ): string[] {
    const reasons: string[] = [];
    
    if (breakdown.experienceScore >= 80) {
      reasons.push(`${worker.experience} illik təcrübəsi və ${worker.completedJobs} tamamlanmış işi var`);
    } else if (breakdown.experienceScore >= 60) {
      reasons.push(`Orta səviyyəli təcrübəyə malikdir`);
    }
    
    if (breakdown.qualityScore >= 85) {
      reasons.push(`Yüksək keyfiyyətli iş göstəriciləri (${worker.rating.toFixed(1)}/5.0)`);
    } else if (breakdown.qualityScore < 60) {
      reasons.push(`Keyfiyyət göstəriciləri inkişafa ehtiyac göstərir`);
    }
    
    if (breakdown.matchScore >= 80) {
      reasons.push(`İşin tələblərinə tam uyğundur`);
    } else if (breakdown.matchScore < 50) {
      reasons.push(`İş tələbləri ilə tam uyğun olmaya bilər`);
    }
    
    if (trend === 'improving') {
      reasons.push(`Son dövrdə performansı yüksəlməkdədir`);
    } else if (trend === 'declining') {
      reasons.push(`Son dövrdə performansda azalma müşahidə olunur`);
    }
    
    if (breakdown.reliabilityScore >= 80) {
      reasons.push(`Yüksək etibarlılıq və vaxtında çatdırılma göstəriciləri`);
    }
    
    if (worker.certifications.length > 0) {
      reasons.push(`${worker.certifications.length} sertifikata malikdir`);
    }
    
    if (DataProcessor.checkLocationMatch(worker.location, job.location)) {
      reasons.push(`İşin ərazisində yerləşir`);
    }
    
    return reasons;
  }
}