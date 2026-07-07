import React from 'react';

export const Badge = ({ children, variant = 'default', className = '' }) => {
  const baseStyles = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium';
  
  const variants = {
    default: 'bg-gray-100 text-gray-800',
    prospecting: 'bg-blue-100 text-blue-800',
    demo: 'bg-purple-100 text-purple-800',
    proposal: 'bg-yellow-100 text-yellow-800',
    negotiation: 'bg-orange-100 text-orange-800',
    closed_won: 'bg-growth/20 text-growth',
    closed_lost: 'bg-gray-200 text-gray-800',
    risk: 'bg-risk/10 text-risk',
  };

  return (
    <span className={`${baseStyles} ${variants[variant] || variants.default} ${className}`}>
      {children}
    </span>
  );
};
