import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../utils/formatters';

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  glow?: boolean;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  onClick?: () => void;
}

const paddingMap = {
  none: '',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
};

export const GlassCard: React.FC<GlassCardProps> = ({
  children,
  className,
  hover = false,
  glow = false,
  padding = 'md',
  onClick,
}) => {
  return (
    <motion.div
      className={cn(
        'glass-card',
        paddingMap[padding],
        hover && 'glass-card-hover cursor-pointer',
        glow && 'cyber-border',
        className
      )}
      whileHover={hover ? { y: -2 } : undefined}
      transition={{ duration: 0.2 }}
      onClick={onClick}
    >
      {children}
    </motion.div>
  );
};
