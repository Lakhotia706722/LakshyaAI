import React from 'react';
import { Sparkline } from './Sparkline';

export const EmptyState = ({ icon: Icon, message, className = '' }) => {
  return (
    <div className={`flex flex-col items-center justify-center p-12 text-center bg-surface border border-border rounded-xl border-dashed ${className}`}>
      {Icon ? (
        <div className="w-12 h-12 rounded-full bg-gray-50 flex items-center justify-center mb-4">
          <Icon className="w-6 h-6 text-gray-400" />
        </div>
      ) : (
        <div className="mb-4 opacity-30">
           <Sparkline data={[20,20,50,10,20,20]} color="var(--color-ink)" width={80} height={30} />
        </div>
      )}
      <p className="text-gray-500 font-medium text-sm">{message}</p>
    </div>
  );
};
