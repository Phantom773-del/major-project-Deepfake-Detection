// ===== ANALYSIS TYPES =====
export type Verdict = 'AUTHENTIC' | 'MANIPULATED' | 'AI_GENERATED' | 'SUSPICIOUS' | 'UNKNOWN';
export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type MediaType = 'image' | 'video';
export type AnalysisStatus = 'idle' | 'uploading' | 'processing' | 'completed' | 'error';

export type StageStatus = 'pending' | 'active' | 'completed' | 'error';

export interface AnalysisStage {
  id: string;
  name: string;
  description: string;
  status: StageStatus;
  progress: number;
  duration?: number;
}

export interface MetadataInfo {
  fileName: string;
  fileSize: string;
  mimeType: string;
  dimensions?: string;
  duration?: string;
  createdAt?: string;
  modifiedAt?: string;
  camera?: string;
  gpsLocation?: string;
  software?: string;
  colorSpace?: string;
  bitDepth?: string;
  frameRate?: string;
  codec?: string;
  hash?: string;
  compression?: string;
  exifData?: Record<string, string>;
}

export interface AIAttribution {
  model: string;
  confidence: number;
  generation: string;
  technique: string;
}

export interface ExplainableAI {
  imageUrl?: string;
  gradcamUrl?: string;
  limeSuperPixels?: number;
  shapValues?: Record<string, number>;
  attentionMap?: string;
  highRiskRegions: Array<{
    x: number;
    y: number;
    width: number;
    height: number;
    confidence: number;
  }>;
}

export interface ForensicReport {
  id: string;
  createdAt: string;
  fileName: string;
  mediaType: MediaType;
  verdict: Verdict;
  riskLevel: RiskLevel;
  authenticityScore: number;
  manipulationProbability: number;
  confidenceScore: number;
  metadata: MetadataInfo;
  aiAttribution?: AIAttribution;
  explainableAI?: ExplainableAI;
  recommendations: string[];
  frequencyAnalysis: {
    anomaliesDetected: boolean;
    anomalyCount: number;
    dominantFrequency: string;
  };
  analysisVersion: string;
  processingTime: number;
}

// ===== DASHBOARD TYPES =====
export interface DashboardStats {
  totalScans: number;
  aiGeneratedMedia: number;
  authenticMedia: number;
  averageConfidence: number;
  todayScans: number;
  weeklyGrowth: number;
  videosAnalysed?: number;
  riskAlerts?: number;
}

export interface ActivityItem {
  id: string;
  fileName: string;
  verdict: Verdict;
  confidenceScore: number;
  timestamp: string;
  mediaType: MediaType;
  riskLevel: RiskLevel;
  reportId?: string;
}

export interface SystemService {
  name: string;
  status: 'operational' | 'degraded' | 'down';
  latency: number;
  uptime: number;
}

export interface SystemStatus {
  services: SystemService[];
  lastChecked: string;
  overallStatus: 'operational' | 'degraded' | 'down';
}

// ===== CHART TYPES =====
export interface ScanTrendData {
  date: string;
  total: number;
  aiGenerated: number;
  authentic: number;
  suspicious: number;
}

export interface RiskDistributionData {
  name: string;
  value: number;
  color: string;
}

export interface AIAttributionData {
  model: string;
  count: number;
  percentage: number;
}

export interface ConfidenceData {
  range: string;
  count: number;
}

// ===== UPLOAD TYPES =====
export interface UploadFile {
  file: File;
  id: string;
  preview?: string;
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
}

// ===== API TYPES =====
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  error?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// ===== TEAM TYPES =====
export interface TeamMember {
  id: string;
  name: string;
  role: string;
  department: string;
  avatar: string;
  github?: string;
  linkedin?: string;
}

// ===== FAQ TYPES =====
export interface FAQItem {
  id: string;
  question: string;
  answer: string;
}

// ===== FEATURE TYPES =====
export interface Feature {
  id: string;
  title: string;
  description: string;
  icon: string;
  color: string;
}

// ===== NOTIFICATION TYPES =====
export interface Notification {
  id: string;
  title: string;
  message: string;
  time: string;
  read: boolean;
  type: 'alert' | 'info' | 'success' | 'warning';
}

// ===== SCAN HISTORY TYPES =====
export interface ScanHistoryItem extends ActivityItem {
  processingTime?: number;
  fileSize?: string;
  analysisVersion?: string;
}
