import { WorkerProfile, Review } from '../../types/scoring.types';

export class ScoreCalculator {
  static calculateExperienceScore(worker: WorkerProfile): number {
    const yearsScore = Math.min(worker.experience * 8, 50);
    const jobsScore = Math.min(worker.completedJobs * 0.5, 30);
    const ageExperienceRatio = worker.experience / Math.max(worker.age - 18, 1);
    const consistencyScore = Math.min(ageExperienceRatio * 40, 20);
    
    return yearsScore + jobsScore + consistencyScore;
  }

  static calculateQualityScore(worker: WorkerProfile): number {
    if (worker.reviews.length === 0) return 50;

    const avgQuality = worker.reviews.reduce((sum, r) => sum + r.quality, 0) / worker.reviews.length;
    const avgRating = worker.reviews.reduce((sum, r) => sum + r.rating, 0) / worker.reviews.length;
    
    const qualityScore = (avgQuality / 5) * 50;
    const ratingScore = (avgRating / 5) * 50;
    
    return qualityScore + ratingScore;
  }

  static calculateReliabilityScore(worker: WorkerProfile): number {
    const successScore = worker.successRate;
    const responseScore = Math.max(0, 100 - (worker.responseTime / 60) * 10);
    
    const recentReviews = worker.reviews.filter(r => {
      const daysSince = (Date.now() - r.date.getTime()) / (1000 * 60 * 60 * 24);
      return daysSince <= 90;
    });
    
    const consistencyScore = recentReviews.length >= 3 ? 20 : recentReviews.length * 6.67;
    
    return (successScore * 0.5) + (responseScore * 0.3) + (consistencyScore * 0.2);
  }

  static calculateReputationScore(worker: WorkerProfile): number {
    const baseRating = (worker.rating / 5) * 60;
    const reviewCountScore = Math.min(worker.reviews.length * 2, 20);
    const certificationScore = Math.min(worker.certifications.length * 5, 20);
    
    return baseRating + reviewCountScore + certificationScore;
  }

  static calculateCommunicationScore(reviews: Review[]): number {
    if (reviews.length === 0) return 70;
    
    const avgCommunication = reviews.reduce((sum, r) => sum + r.communication, 0) / reviews.length;
    return (avgCommunication / 5) * 100;
  }

  static calculateProfessionalismScore(reviews: Review[]): number {
    if (reviews.length === 0) return 70;
    
    const avgProfessionalism = reviews.reduce((sum, r) => sum + r.professionalism, 0) / reviews.length;
    const avgTimeliness = reviews.reduce((sum, r) => sum + r.timeliness, 0) / reviews.length;
    
    return ((avgProfessionalism + avgTimeliness) / 10) * 100;
  }
}