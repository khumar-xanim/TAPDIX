import { WorkerProfile, JobListing, Review } from '../../types/scoring.types';

export class DataProcessor {
  static checkCategoryMatch(worker: WorkerProfile, job: JobListing): number {
    if (worker.category === job.category) return 100;
    
    const relatedCategories: Record<string, string[]> = {
      'Elektrik': ['Texniki xidmət', 'Tikinti'],
      'Tikinti': ['Elektrik', 'Su', 'Boyama'],
      'İT': ['Texniki xidmət'],
      'Su': ['Tikinti'],
    };
    
    if (relatedCategories[worker.category]?.includes(job.category)) {
      return 50;
    }
    
    return 0;
  }

  static checkLocationMatch(workerLocation: string, jobLocation: string): boolean {
    return workerLocation.toLowerCase().includes(jobLocation.toLowerCase()) ||
           jobLocation.toLowerCase().includes(workerLocation.toLowerCase());
  }

  static checkComplexityMatch(worker: WorkerProfile, job: JobListing): number {
    const requiredExperience = Math.ceil(job.complexity / 2);
    
    if (worker.experience >= requiredExperience * 2) return 100;
    if (worker.experience >= requiredExperience) return 80;
    if (worker.experience >= requiredExperience * 0.7) return 60;
    
    return 30;
  }

  static analyzeTrend(reviews: Review[]): 'improving' | 'stable' | 'declining' {
    if (reviews.length < 3) return 'stable';
    
    const sortedReviews = reviews.sort((a, b) => b.date.getTime() - a.date.getTime());
    const recent = sortedReviews.slice(0, 3);
    const older = sortedReviews.slice(3, 6);
    
    if (older.length === 0) return 'stable';
    
    const recentAvg = recent.reduce((sum, r) => sum + r.rating, 0) / recent.length;
    const olderAvg = older.reduce((sum, r) => sum + r.rating, 0) / older.length;
    
    const diff = recentAvg - olderAvg;
    
    if (diff > 0.3) return 'improving';
    if (diff < -0.3) return 'declining';
    return 'stable';
  }

  static analyzeClientSatisfaction(reviews: Review[]): {
    overallSatisfaction: number;
    repeatClients: number;
    complaintsRate: number;
  } {
    const overallSatisfaction = reviews.reduce((sum, r) => sum + r.rating, 0) / Math.max(reviews.length, 1);
    
    const clientIds = reviews.map(r => r.clientId);
    const uniqueClients = new Set(clientIds).size;
    const repeatClients = ((clientIds.length - uniqueClients) / Math.max(clientIds.length, 1)) * 100;
    
    const lowRatings = reviews.filter(r => r.rating <= 2).length;
    const complaintsRate = (lowRatings / Math.max(reviews.length, 1)) * 100;
    
    return {
      overallSatisfaction: (overallSatisfaction / 5) * 100,
      repeatClients,
      complaintsRate
    };
  }
}