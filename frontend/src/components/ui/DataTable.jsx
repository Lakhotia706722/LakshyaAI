import React from 'react';
import { ArrowUp, ArrowDown } from 'lucide-react';

export const DataTable = ({ columns, data, emptyState }) => {
  if (!data || data.length === 0) {
    return emptyState || <div className="p-8 text-center text-gray-500">No data available</div>;
  }

  return (
    <div className="w-full overflow-x-auto border border-border rounded-xl">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="border-b border-border bg-gray-50/50">
            {columns.map((col, i) => (
              <th 
                key={i} 
                className="px-6 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider"
              >
                <div className="flex items-center gap-1">
                  {col.header}
                  {col.sortable && <ArrowDown className="w-3 h-3 text-gray-400" />}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-surface">
          {data.map((row, rowIndex) => (
            <tr key={rowIndex} className="border-b border-border last:border-0 hover:bg-gray-50/50 transition-colors h-12">
              {columns.map((col, colIndex) => (
                <td 
                  key={colIndex} 
                  className={`px-6 py-3 whitespace-nowrap text-sm text-ink ${col.isNumeric ? 'font-mono' : ''}`}
                >
                  {col.cell ? col.cell(row) : row[col.accessorKey]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
