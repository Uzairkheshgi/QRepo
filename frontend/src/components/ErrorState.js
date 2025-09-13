import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

const ErrorState = ({ status, onRetry }) => {
  return (
    <div className="card">
      <div className="text-center py-8">
        <div className="flex justify-center mb-4">
          <div className="p-3 bg-red-100 rounded-full">
            <AlertCircle size={48} className="text-red-600" />
          </div>
        </div>
        
        <h3 className="text-2xl font-bold text-red-600 mb-3">
          Indexing Failed
        </h3>
        
        <p className="text-gray-600 mb-6 max-w-md mx-auto">
          {status?.message || 'An error occurred while indexing the repository. Please check the URL and try again.'}
        </p>
        
        <button
          onClick={onRetry}
          className="btn-secondary inline-flex items-center gap-2"
        >
          <RefreshCw size={20} />
          Try Again
        </button>
      </div>
    </div>
  );
};

export default ErrorState;
