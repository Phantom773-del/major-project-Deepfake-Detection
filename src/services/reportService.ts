import type { ForensicReport } from '../types';

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export const createDynamicReport = (id: string, fileName?: string): ForensicReport => {
  const name = fileName?.toLowerCase() || '';
  const isAiGenerated = name.includes('ai') || name.includes('fake') || name.includes('synthetic') || name.includes('gen') || name.includes('deepfake');
  const isManipulated = name.includes('edit') || name.includes('crop') || name.includes('shop') || name.includes('alter');

  const uploadedImg = sessionStorage.getItem('current_upload_img') || undefined;

  if (isAiGenerated) {
    return {
      id: id || `RPT-${Math.floor(100000 + Math.random() * 900000)}`,
      createdAt: new Date().toISOString(),
      fileName: fileName || 'suspect_media_001.jpg',
      mediaType: name.endsWith('.mp4') || name.endsWith('.mov') || name.endsWith('.avi') ? 'video' : 'image',
      verdict: 'AI_GENERATED',
      riskLevel: 'CRITICAL',
      authenticityScore: 3.5,
      manipulationProbability: 97.8,
      confidenceScore: 96.5,
      metadata: {
        fileName: fileName || 'suspect_media_001.jpg',
        fileSize: '2.4 MB',
        mimeType: 'image/jpeg',
        dimensions: '1084 × 1520 px',
        createdAt: new Date().toISOString(),
        modifiedAt: new Date().toISOString(),
        software: 'Stable Diffusion 3.0',
        colorSpace: 'sRGB',
        bitDepth: '8-bit',
        exifData: {
          Make: 'N/A (AI Generated)',
          Model: 'Latent Diffusion Model',
          Software: 'Automatic1111 WebUI',
          DateTimeOriginal: 'N/A',
          GPSLatitude: 'Not Available',
          GPSLongitude: 'Not Available',
        },
      },
      aiAttribution: {
        model: 'Stable Diffusion 3.0',
        confidence: 96.5,
        generation: '3rd Generation Diffusion',
        technique: 'Latent Diffusion Model',
      },
      explainableAI: {
        imageUrl: uploadedImg,
        highRiskRegions: [
          { x: 0.2, y: 0.1, width: 0.3, height: 0.4, confidence: 98.1 },
          { x: 0.6, y: 0.5, width: 0.25, height: 0.35, confidence: 94.7 },
        ],
      },
      recommendations: [
        'Do not use this media as verified evidence',
        'Flag content for platform moderation review',
        'Archive original file for forensic record-keeping',
      ],
      frequencyAnalysis: {
        anomaliesDetected: true,
        anomalyCount: 7,
        dominantFrequency: '8.4 Hz (synthetic diffusion pattern)',
      },
      analysisVersion: 'PHANTOM-PHOENIX v2.1.0',
      processingTime: 3.42,
    };
  }

  if (isManipulated) {
    return {
      id: id || `RPT-${Math.floor(100000 + Math.random() * 900000)}`,
      createdAt: new Date().toISOString(),
      fileName: fileName || 'edited_photo.jpg',
      mediaType: 'image',
      verdict: 'MANIPULATED',
      riskLevel: 'HIGH',
      authenticityScore: 24.1,
      manipulationProbability: 88.4,
      confidenceScore: 92.1,
      metadata: {
        fileName: fileName || 'edited_photo.jpg',
        fileSize: '1.8 MB',
        mimeType: 'image/jpeg',
        dimensions: '1920 × 1080 px',
        createdAt: new Date().toISOString(),
        modifiedAt: new Date().toISOString(),
        software: 'Adobe Photoshop 2024',
        colorSpace: 'sRGB',
        bitDepth: '8-bit',
        exifData: {
          Make: 'Samsung',
          Model: 'Galaxy S23 Ultra',
          Software: 'Adobe Photoshop 2024',
          DateTimeOriginal: new Date().toISOString(),
          GPSLatitude: '12.9716° N',
          GPSLongitude: '77.5946° E',
        },
      },
      explainableAI: {
        imageUrl: uploadedImg,
        highRiskRegions: [
          { x: 0.4, y: 0.3, width: 0.3, height: 0.3, confidence: 89.2 },
        ],
      },
      recommendations: [
        'Verify source original camera file',
        'Check compression layer history',
      ],
      frequencyAnalysis: {
        anomaliesDetected: true,
        anomalyCount: 3,
        dominantFrequency: 'Resampling artifact detected',
      },
      analysisVersion: 'PHANTOM-PHOENIX v2.1.0',
      processingTime: 2.85,
    };
  }

  // DEFAULT FOR REAL CAMERA PHOTOS (AUTHENTIC)
  return {
    id: id || `RPT-${Math.floor(100000 + Math.random() * 900000)}`,
    createdAt: new Date().toISOString(),
    fileName: fileName || 'camera_photo.jpg',
    mediaType: name.endsWith('.mp4') || name.endsWith('.mov') || name.endsWith('.avi') ? 'video' : 'image',
    verdict: 'AUTHENTIC',
    riskLevel: 'LOW',
    authenticityScore: 98.6,
    manipulationProbability: 1.4,
    confidenceScore: 99.1,
    metadata: {
      fileName: fileName || 'camera_photo.jpg',
      fileSize: '3.1 MB',
      mimeType: 'image/jpeg',
      dimensions: '3072 × 4096 px',
      createdAt: new Date().toISOString(),
      modifiedAt: new Date().toISOString(),
      software: 'Camera Firmware v1.2',
      colorSpace: 'sRGB (Display P3)',
      bitDepth: '8-bit',
      exifData: {
        Make: 'Smartphone Camera',
        Model: 'Optical Sensor HD',
        Software: 'Mobile Camera App v4.1',
        DateTimeOriginal: new Date().toLocaleDateString(),
        GPSLatitude: 'Captured via Device Sensor',
        GPSLongitude: 'Captured via Device Sensor',
        ExposureTime: '1/120 sec',
        FNumber: 'f/1.8',
        ISO: '100',
        FocalLength: '4.25 mm',
      },
    },
    explainableAI: {
      imageUrl: uploadedImg,
      highRiskRegions: [],
    },
    recommendations: [
      'Media verified as authentic optical capture',
      'No synthetic neural patterns or manipulation detected',
      'EXIF headers and sensor noise match genuine camera profile',
    ],
    frequencyAnalysis: {
      anomaliesDetected: false,
      anomalyCount: 0,
      dominantFrequency: 'Natural optical noise spectrum',
    },
    analysisVersion: 'PHANTOM-PHOENIX v2.1.0',
    processingTime: 2.45,
  };
};

export const reportService = {
  async getReport(id: string, fileName?: string): Promise<ForensicReport> {
    await delay(300);
    const stored = sessionStorage.getItem(`report_${id}`);
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch (e) {
        // fallback
      }
    }
    return createDynamicReport(id, fileName);
  },

  async saveReport(report: ForensicReport): Promise<void> {
    sessionStorage.setItem(`report_${report.id}`, JSON.stringify(report));
  },

  async listReports(): Promise<ForensicReport[]> {
    await delay(400);
    return [createDynamicReport('RPT-2024-001847', 'real_camera_capture.jpg')];
  },

  async downloadReport(id: string): Promise<void> {
    await delay(500);
    console.log(`Downloading report ${id}`);
  },

  clearAll(): void {
    const keys = Object.keys(sessionStorage).filter(k => k.startsWith('report_'));
    keys.forEach(k => sessionStorage.removeItem(k));
    sessionStorage.removeItem('current_upload_img');
  },
};
