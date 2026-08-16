import type {
  DashboardStats,
  ActivityItem,
  SystemStatus,
  ForensicReport,
  ScanTrendData,
  RiskDistributionData,
  AIAttributionData,
  ConfidenceData,
  TeamMember,
  FAQItem,
  Feature,
  AnalysisStage,
} from '../types';

// ===== DASHBOARD INITIAL DATA =====
export const MOCK_DASHBOARD_STATS: DashboardStats = {
  totalScans: 0,
  aiGeneratedMedia: 0,
  authenticMedia: 0,
  averageConfidence: 0.0,
  todayScans: 0,
  weeklyGrowth: 0.0,
};

export const MOCK_ACTIVITY: ActivityItem[] = [];

export const MOCK_SYSTEM_STATUS: SystemStatus = {
  services: [
    { name: 'AI Detection Engine', status: 'operational', latency: 42, uptime: 100 },
    { name: 'Metadata Extractor', status: 'operational', latency: 12, uptime: 100 },
    { name: 'Frequency Analyzer', status: 'operational', latency: 67, uptime: 100 },
    { name: 'Explainable AI Module', status: 'operational', latency: 85, uptime: 100 },
    { name: 'Report Generator', status: 'operational', latency: 18, uptime: 100 },
    { name: 'Storage Service', status: 'operational', latency: 8, uptime: 100 },
  ],
  lastChecked: new Date().toISOString(),
  overallStatus: 'operational',
};

// ===== CHART INITIAL DATA (zero – charts derive from real scan activity) =====
export const MOCK_SCAN_TREND: ScanTrendData[] = [];

export const MOCK_MONTHLY_TREND: ScanTrendData[] = [];

export const MOCK_RISK_DISTRIBUTION: RiskDistributionData[] = [
  { name: 'Low Risk',    value: 0, color: '#10b981' },
  { name: 'Medium Risk', value: 0, color: '#f59e0b' },
  { name: 'High Risk',   value: 0, color: '#ef4444' },
  { name: 'Critical',    value: 0, color: '#dc2626' },
];

export const MOCK_AI_ATTRIBUTION: AIAttributionData[] = [
  { model: 'Stable Diffusion', count: 0, percentage: 0 },
  { model: 'DALL-E 3',         count: 0, percentage: 0 },
  { model: 'Midjourney',       count: 0, percentage: 0 },
  { model: 'GAN-Based',        count: 0, percentage: 0 },
  { model: 'DeepFake Engine',  count: 0, percentage: 0 },
  { model: 'Unknown AI',       count: 0, percentage: 0 },
];

export const MOCK_CONFIDENCE_DIST: ConfidenceData[] = [
  { range: '50-60%',  count: 0 },
  { range: '60-70%',  count: 0 },
  { range: '70-80%',  count: 0 },
  { range: '80-90%',  count: 0 },
  { range: '90-95%',  count: 0 },
  { range: '95-99%',  count: 0 },
  { range: '99-100%', count: 0 },
];

// ===== FORENSIC REPORT MOCK =====
export const MOCK_REPORT: ForensicReport = {
  id: 'RPT-2024-001847',
  createdAt: new Date().toISOString(),
  fileName: 'suspect_media_001.jpg',
  mediaType: 'image',
  verdict: 'AI_GENERATED',
  riskLevel: 'CRITICAL',
  authenticityScore: 4.2,
  manipulationProbability: 98.7,
  confidenceScore: 97.3,
  metadata: {
    fileName: 'suspect_media_001.jpg',
    fileSize: '2.4 MB',
    mimeType: 'image/jpeg',
    dimensions: '1024 × 1024 px',
    createdAt: new Date().toISOString(),
    modifiedAt: new Date().toISOString(),
    software: 'Stable Diffusion 3.0',
    colorSpace: 'sRGB',
    bitDepth: '8-bit',
    exifData: {
      Make: 'N/A (AI Generated)',
      Model: 'Stable Diffusion 3.0',
      Software: 'Automatic1111 WebUI',
      DateTimeOriginal: 'N/A',
      GPSLatitude: 'Not Available',
      GPSLongitude: 'Not Available',
      ExposureTime: 'N/A',
      FNumber: 'N/A',
      ISO: 'N/A',
      FocalLength: 'N/A',
    },
  },
  aiAttribution: {
    model: 'Stable Diffusion 3.0',
    confidence: 97.3,
    generation: '3rd Generation Diffusion',
    technique: 'Latent Diffusion Model',
  },
  explainableAI: {
    highRiskRegions: [
      { x: 0.2, y: 0.1, width: 0.3, height: 0.4, confidence: 98.1 },
      { x: 0.6, y: 0.5, width: 0.25, height: 0.35, confidence: 94.7 },
    ],
  },
  recommendations: [
    'Do not use this media as evidence in legal proceedings',
    'Report to platform administrators for content moderation',
    'Cross-reference with original source metadata if available',
    'Consider initiating a chain-of-custody investigation',
    'Archive original file for forensic record-keeping',
    'Notify relevant authorities if used in disinformation campaigns',
  ],
  frequencyAnalysis: {
    anomaliesDetected: true,
    anomalyCount: 7,
    dominantFrequency: '8.4 Hz (synthetic pattern)',
  },
  analysisVersion: 'PHANTOM-PHOENIX v2.1.0',
  processingTime: 3.847,
};

// ===== ANALYSIS STAGES =====
export const ANALYSIS_STAGES: AnalysisStage[] = [
  { id: 'upload', name: 'Uploading File', description: 'File received and validated by ingestion service', status: 'pending', progress: 0 },
  { id: 'metadata', name: 'Extracting Metadata', description: 'Parsing EXIF, file signatures and provenance data', status: 'pending', progress: 0 },
  { id: 'objects', name: 'Detecting Objects', description: 'Running object and face detection models', status: 'pending', progress: 0 },
  { id: 'ai_model', name: 'Running AI Model', description: 'Multi-model neural network ensemble classifiers', status: 'pending', progress: 0 },
  { id: 'heatmap', name: 'Generating Heatmap', description: 'Creating GradCAM and XAI visualizations', status: 'pending', progress: 0 },
  { id: 'authenticity', name: 'Calculating Authenticity', description: 'Computing risk scores and manipulation probability', status: 'pending', progress: 0 },
  { id: 'report', name: 'Preparing Report', description: 'Compiling forensic intelligence report', status: 'pending', progress: 0 },
];

// ===== TEAM MEMBERS =====
export const TEAM_MEMBERS: TeamMember[] = [
  { id: '1', name: 'Shree Raksha', role: 'Frontend Architect', department: 'Engineering', avatar: 'SR', github: '#', linkedin: '#' },
];

// ===== FAQ =====
export const FAQ_ITEMS: FAQItem[] = [
  {
    id: '1',
    question: 'What types of media can PHANTOM PHOENIX analyze?',
    answer: 'PHANTOM PHOENIX supports analysis of images (JPEG, PNG, WebP, TIFF, BMP) and videos (MP4, AVI, MOV, MKV). Maximum file size is 500MB for videos and 50MB for images.',
  },
  {
    id: '2',
    question: 'How accurate is the AI detection system?',
    answer: 'Our multi-model ensemble achieves 97.3% accuracy on benchmark datasets including FaceForensics++, DFDC, and OpenForensics. Results are provided with confidence intervals.',
  },
  {
    id: '3',
    question: 'What does the Explainable AI module provide?',
    answer: 'The XAI module generates GradCAM heatmaps, LIME visualizations, and SHAP values to highlight which specific regions of an image/video triggered the detection system.',
  },
  {
    id: '4',
    question: 'Can reports be used as legal evidence?',
    answer: 'PHANTOM PHOENIX reports are designed for forensic intelligence purposes. For legal proceedings, please consult a qualified digital forensics expert who can provide expert testimony.',
  },
  {
    id: '5',
    question: 'How does AI model attribution work?',
    answer: 'We analyze unique fingerprints left by different generative models (Stable Diffusion, DALL-E, Midjourney, GANs) including noise patterns, frequency artifacts, and model-specific signatures.',
  },
  {
    id: '6',
    question: 'Is my uploaded data stored permanently?',
    answer: 'Uploaded files are processed in an isolated environment and automatically deleted after 24 hours. Reports are retained for 30 days unless exported. We never use your data for training.',
  },
  {
    id: '7',
    question: 'What is the typical processing time?',
    answer: 'Analysis takes 3-15 seconds for images and 15-120 seconds for videos depending on file size and resolution. Enterprise users have priority processing queues.',
  },
];

// ===== FEATURES =====
export const PLATFORM_FEATURES: Feature[] = [
  { id: '1', title: 'Deep Neural Detection', description: 'Multi-layer ensemble models trained on millions of authentic and AI-generated samples with 97.3% accuracy.', icon: 'Brain', color: 'cyber-blue' },
  { id: '2', title: 'Metadata Forensics', description: 'Extract and analyze EXIF data, file signatures, creation timestamps, and GPS coordinates for provenance verification.', icon: 'Database', color: 'cyber-cyan' },
  { id: '3', title: 'Frequency Analysis', description: 'DCT, FFT, and wavelet transform analysis to detect invisible artifacts left by AI generation and image editing tools.', icon: 'Activity', color: 'cyber-purple' },
  { id: '4', title: 'Explainable AI (XAI)', description: 'GradCAM heatmaps and LIME visualizations show exactly which regions triggered detection for full interpretability.', icon: 'Eye', color: 'cyber-green' },
  { id: '5', title: 'AI Model Attribution', description: 'Identify which specific AI model (Stable Diffusion, DALL-E, Midjourney, GAN) generated the media content.', icon: 'Target', color: 'cyber-amber' },
  { id: '6', title: 'Professional Reports', description: 'Generate comprehensive forensic intelligence reports with verdict, evidence, and actionable recommendations.', icon: 'FileText', color: 'cyber-red' },
];

// ===== WORKFLOW STEPS =====
export const WORKFLOW_STEPS = [
  { step: '01', title: 'Upload Media', description: 'Drag & drop or browse to upload images or video files' },
  { step: '02', title: 'Metadata Extraction', description: 'Automatically extracts EXIF, file signatures, and provenance data' },
  { step: '03', title: 'AI Detection', description: 'Runs multi-model neural network ensemble classifiers' },
  { step: '04', title: 'Frequency Analysis', description: 'DCT/FFT analysis detects synthetic patterns and compression artifacts' },
  { step: '05', title: 'Explainable AI', description: 'GradCAM and LIME generate visual explanations of detection' },
  { step: '06', title: 'AI Attribution', description: 'Identifies the generative model responsible for the content' },
  { step: '07', title: 'Risk Assessment', description: 'Computes risk score and manipulation probability' },
  { step: '08', title: 'Report Generation', description: 'Generates professional forensic intelligence report' },
];

// ===== NOTIFICATIONS MOCK =====
export const MOCK_NOTIFICATIONS = [
  { id: '1', title: 'Scan Complete', message: 'Analysis of suspect_media_001.jpg finished with CRITICAL risk.', time: '2 min ago', read: false, type: 'alert' as const },
  { id: '2', title: 'System Update', message: 'AI Detection Engine updated to v2.1.0.', time: '1 hr ago', read: false, type: 'info' as const },
  { id: '3', title: 'Report Ready', message: 'Forensic report RPT-001 is ready for download.', time: '3 hr ago', read: true, type: 'success' as const },
];
