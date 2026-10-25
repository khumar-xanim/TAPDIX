import { WorkerProfile, JobListing, ScoringResult } from '../../types/scoring.types';
import { WorkerScoringModel } from './workerScoring';

export class RecommendationEngine {
  static recommendWorkersForJob(
    workers: WorkerProfile[], 
    job: JobListing, 
    limit: number = 10
  ): ScoringResult[] {
    const scoringModel = new WorkerScoringModel(job.category);
    
    const scoredWorkers = workers.map(worker => 
      scoringModel.scoreWorker(worker, job)
    );
    
    return scoredWorkers
      .sort((a, b) => b.totalScore - a.totalScore)
      .slice(0, limit);
  }

  static getPersonalizedRecommendations(
    workers: WorkerProfile[],
    clientHistory: JobListing[],
    limit: number = 5
  ): WorkerProfile[] {
    if (clientHistory.length === 0) {
      return workers
        .sort((a, b) => b.rating - a.rating)
        .slice(0, limit);
    }
    
    const categoryFrequency: Record<string, number> = {};
    clientHistory.forEach(job => {
      categoryFrequency[job.category] = (categoryFrequency[job.category] || 0) + 1;
    });
    
    const preferredCategories = Object.entries(categoryFrequency)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 3)
      .map(([category]) => category);
    
    return workers
      .filter(worker => preferredCategories.includes(worker.category))
      .sort((a, b) => b.rating - a.rating)
      .slice(0, limit);
  }

  static findSimilarSuccessfulWorkers(
    targetJob: JobListing,
    allWorkers: WorkerProfile[],
    limit: number = 5
  ): WorkerProfile[] {
    return allWorkers
      .filter(worker => 
        worker.category === targetJob.category &&
        worker.completedJobs > 0 &&
        worker.rating >= 4.0
      )
      .sort((a, b) => {
        const scoreA = (a.experience * 0.3) + (a.rating * 20) + (a.completedJobs * 0.1);
        const scoreB = (b.experience * 0.3) + (b.rating * 20) + (b.completedJobs * 0.1);
        return scoreB - scoreA;
      })
      .slice(0, limit);
  }
}