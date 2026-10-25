import { WorkerProfile, JobListing, ScoringResult } from '../types/scoring.types';
import { WorkerScoringModel } from './models/workerScoring';
import { RecommendationEngine } from './models/recommendationEngine';

export class ScoringEngine {
  static scoreWorker(worker: WorkerProfile, job: JobListing): ScoringResult {
    const model = new WorkerScoringModel(job.category);
    return model.scoreWorker(worker, job);
  }

  static recommendWorkers(
    workers: WorkerProfile[], 
    job: JobListing, 
    limit: number = 10
  ): ScoringResult[] {
    return RecommendationEngine.recommendWorkersForJob(workers, job, limit);
  }

  static getPersonalizedRecommendations(
    workers: WorkerProfile[],
    clientHistory: JobListing[],
    limit: number = 5
  ): WorkerProfile[] {
    return RecommendationEngine.getPersonalizedRecommendations(workers, clientHistory, limit);
  }

  static findSimilarWorkers(
    targetJob: JobListing,
    allWorkers: WorkerProfile[],
    limit: number = 5
  ): WorkerProfile[] {
    return RecommendationEngine.findSimilarSuccessfulWorkers(targetJob, allWorkers, limit);
  }
}

export default ScoringEngine;