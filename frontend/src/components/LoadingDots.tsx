import React from 'react';

interface LoadingDotsProps {
  size?: 'sm' | 'md';
  color?: string;
  label?: string;
}

const LoadingDots: React.FC<LoadingDotsProps> = ({
  size = 'md',
  color,
  label,
}) => {
  const dotSize = size === 'sm' ? 4 : 6;
  const gap = size === 'sm' ? 3 : 5;

  return (
    <div className="loading-dots" role="status" aria-label={label || 'Loading'}>
      {label && <span className="loading-dots-label">{label}</span>}
      <div className="loading-dots-track" style={{ gap: `${gap}px` }}>
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="loading-dots-dot"
            style={{
              width: `${dotSize}px`,
              height: `${dotSize}px`,
              backgroundColor: color || undefined,
              animationDelay: `${i * 0.2}s`,
            }}
          />
        ))}
      </div>
    </div>
  );
};

export default LoadingDots;
