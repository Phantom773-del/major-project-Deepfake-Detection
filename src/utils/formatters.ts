// ===== FILE FORMATTERS =====
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
};

export const formatDuration = (seconds: number): string => {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
};

// ===== DATE FORMATTERS =====
export const formatDate = (dateStr: string): string => {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
};

export const formatDateTime = (dateStr: string): string => {
  const date = new Date(dateStr);
  return date.toLocaleString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
};

export const formatRelativeTime = (dateStr: string): string => {
  const now = new Date();
  const date = new Date(dateStr);
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return formatDate(dateStr);
};

// ===== NUMBER FORMATTERS =====
export const formatNumber = (num: number): string => {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return num.toString();
};

export const formatPercentage = (value: number, decimals = 1): string => {
  return `${value.toFixed(decimals)}%`;
};

// ===== VERDICT HELPERS =====
export const getVerdictColor = (verdict: string): string => {
  switch (verdict) {
    case 'AUTHENTIC': return '#10b981';
    case 'MANIPULATED': return '#ef4444';
    case 'AI_GENERATED': return '#8b5cf6';
    case 'SUSPICIOUS': return '#f59e0b';
    default: return '#64748b';
  }
};

export const getVerdictBg = (verdict: string): string => {
  switch (verdict) {
    case 'AUTHENTIC': return 'rgba(16, 185, 129, 0.15)';
    case 'MANIPULATED': return 'rgba(239, 68, 68, 0.15)';
    case 'AI_GENERATED': return 'rgba(139, 92, 246, 0.15)';
    case 'SUSPICIOUS': return 'rgba(245, 158, 11, 0.15)';
    default: return 'rgba(100, 116, 139, 0.15)';
  }
};

export const getRiskColor = (risk: string): string => {
  switch (risk) {
    case 'LOW': return '#10b981';
    case 'MEDIUM': return '#f59e0b';
    case 'HIGH': return '#ef4444';
    case 'CRITICAL': return '#dc2626';
    default: return '#64748b';
  }
};

export const getStatusColor = (status: string): string => {
  switch (status) {
    case 'operational': return '#10b981';
    case 'degraded': return '#f59e0b';
    case 'down': return '#ef4444';
    default: return '#64748b';
  }
};

// ===== CLASS MERGE UTILITY =====
export const cn = (...classes: (string | undefined | null | boolean)[]): string => {
  return classes.filter(Boolean).join(' ');
};
