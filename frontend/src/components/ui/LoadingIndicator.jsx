import React from 'react';

export const LoadingIndicator = ({ message = "Loading...", className = '' }) => {
  return (
    <div className={`flex flex-col items-center justify-center p-8 space-y-4 ${className}`}>
      <div className="relative w-16 h-8 overflow-hidden">
        {/* Animated pulse line svg */}
        <svg 
          viewBox="0 0 100 50" 
          className="absolute inset-0 w-full h-full"
          style={{ animation: 'pulse-slide 1.5s infinite linear' }}
        >
          <style>
            {`
              @keyframes pulse-slide {
                0% { transform: translateX(-100%); }
                100% { transform: translateX(100%); }
              }
            `}
          </style>
          <polyline
            fill="none"
            stroke="var(--color-primary)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            points="0,25 20,25 30,10 40,40 50,25 100,25"
          />
        </svg>
      </div>
      {message && <p className="text-sm text-gray-500 font-medium">{message}</p>}
    </div>
  );
};
