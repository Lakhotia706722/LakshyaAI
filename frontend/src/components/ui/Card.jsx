import React from 'react';

export const Card = ({ children, className = '', interactive = false, ...props }) => {
  const baseStyles = 'bg-surface rounded-xl border border-border';
  const interactiveStyles = interactive ? 'transition-shadow hover:shadow-card-hover cursor-pointer' : 'shadow-card';
  
  return (
    <div className={`${baseStyles} ${interactiveStyles} ${className}`} {...props}>
      {children}
    </div>
  );
};

export const CardHeader = ({ children, className = '' }) => (
  <div className={`px-6 py-4 border-b border-border ${className}`}>
    {children}
  </div>
);

export const CardTitle = ({ children, className = '' }) => (
  <h3 className={`font-display font-semibold text-lg text-ink ${className}`}>
    {children}
  </h3>
);

export const CardContent = ({ children, className = '' }) => (
  <div className={`p-6 ${className}`}>
    {children}
  </div>
);
