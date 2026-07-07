import React from 'react';
import { NavLink } from 'react-router-dom';

export const NavSidebar = ({ items, className = '' }) => {
  return (
    <nav className={`flex flex-col space-y-1 ${className}`}>
      {items.map((item, index) => (
        <NavLink
          key={index}
          to={item.href}
          className={({ isActive }) => `
            flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors relative
            ${isActive 
              ? 'text-ink bg-gray-50' 
              : 'text-gray-500 hover:text-ink hover:bg-gray-50'
            }
          `}
        >
          {({ isActive }) => (
            <>
              {isActive && (
                <div className="absolute left-0 top-1.5 bottom-1.5 w-1 bg-accent rounded-r-full" />
              )}
              <item.icon className={`w-5 h-5 ${isActive ? 'text-primary' : 'text-gray-400'}`} />
              {item.label}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
};
