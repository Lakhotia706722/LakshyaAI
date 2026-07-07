import React from 'react';

export const Sparkline = ({ data = [10, 25, 15, 40, 20, 50, 30], color = 'var(--color-primary)', width = 60, height = 24, className = '' }) => {
  if (!data || data.length === 0) return null;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  
  const points = data.map((val, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((val - min) / range) * height;
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg 
      width={width} 
      height={height} 
      viewBox={`0 -2 ${width} ${height + 4}`} 
      className={`overflow-visible ${className}`}
    >
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
    </svg>
  );
};
