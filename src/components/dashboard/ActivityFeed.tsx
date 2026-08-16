import React from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Clock, Image, Video, ExternalLink } from 'lucide-react';
import { GlassCard } from '../common/GlassCard';
import { StatusBadge } from '../common/StatusBadge';
import type { ActivityItem } from '../../types';

interface ActivityFeedProps {
  items: ActivityItem[];
  loading?: boolean;
}

const formatTimestamp = (ts: string) => {
  if (!ts || ts === 'Just now') return 'Just now';
  try {
    const date = new Date(ts);
    const now = new Date();
    const diff = (now.getTime() - date.getTime()) / 1000;
    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch {
    return ts;
  }
};

export const ActivityFeed: React.FC<ActivityFeedProps> = ({ items, loading }) => {
  const navigate = useNavigate();

  if (loading) {
    return (
      <GlassCard>
        <h3 className="text-white font-semibold mb-4">Recent Activity</h3>
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="skeleton h-14 rounded-xl" />
          ))}
        </div>
      </GlassCard>
    );
  }

  return (
    <GlassCard>
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-white font-semibold">Recent Activity</h3>
        <button
          onClick={() => navigate('/scan-history')}
          className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors font-mono flex items-center gap-1"
        >
          VIEW ALL <ExternalLink className="w-3 h-3" />
        </button>
      </div>

      {items.length === 0 ? (
        <div className="py-10 text-center">
          <div className="w-12 h-12 rounded-xl bg-slate-800/60 flex items-center justify-center mx-auto mb-3">
            <Clock className="w-6 h-6 text-slate-600" />
          </div>
          <p className="text-sm text-slate-500">No scans yet</p>
          <p className="text-xs text-slate-600 mt-1">Upload a media file to begin</p>
        </div>
      ) : (
        <div className="space-y-2">
          {items.slice(0, 8).map((item, index) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.04 }}
              onClick={() => item.reportId && navigate(`/report/${item.reportId}`)}
              className="flex items-center gap-3 p-3 rounded-xl hover:bg-slate-800/40 transition-colors cursor-pointer group"
            >
              {/* File Type Icon */}
              <div className="w-9 h-9 rounded-lg bg-slate-800 flex items-center justify-center flex-shrink-0">
                {item.mediaType === 'video'
                  ? <Video className="w-4 h-4 text-amber-400" />
                  : <Image className="w-4 h-4 text-blue-400" />
                }
              </div>

              {/* File Info */}
              <div className="flex-1 min-w-0">
                <p className="text-sm text-slate-200 font-medium truncate group-hover:text-white transition-colors">
                  {item.fileName}
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                  <Clock className="w-3 h-3 text-slate-600" />
                  <span className="text-xs text-slate-600 font-mono">{formatTimestamp(item.timestamp)}</span>
                </div>
              </div>

              {/* Score + Badge */}
              <div className="text-right flex-shrink-0 space-y-1">
                <p className="text-sm font-bold text-white font-mono">{item.confidenceScore.toFixed(0)}%</p>
                <StatusBadge verdict={item.verdict} size="sm" />
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </GlassCard>
  );
};
