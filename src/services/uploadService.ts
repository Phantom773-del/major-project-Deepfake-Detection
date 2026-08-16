import type { UploadFile } from '../types';

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export const uploadService = {
  async uploadFile(
    _file: File,
    onProgress: (progress: number) => void
  ): Promise<{ jobId: string }> {
    for (let i = 0; i <= 100; i += 10) {
      await delay(150);
      onProgress(i);
    }
    return { jobId: `JOB-${Date.now()}` };
  },

  validateFile(file: File): { valid: boolean; error?: string } {
    const isImage = file.type.startsWith('image/');
    const isVideo = file.type.startsWith('video/');
    
    if (!isImage && !isVideo) {
      return { valid: false, error: 'Unsupported file type. Please upload images or videos.' };
    }

    const maxImageSize = 50 * 1024 * 1024; // 50MB
    const maxVideoSize = 500 * 1024 * 1024; // 500MB
    const maxSize = isVideo ? maxVideoSize : maxImageSize;

    if (file.size > maxSize) {
      return {
        valid: false,
        error: `File too large. Max size: ${isVideo ? '500MB' : '50MB'}`,
      };
    }

    return { valid: true };
  },
};

export type { UploadFile };
