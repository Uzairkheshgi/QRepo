import React, { useState } from 'react';
import { Github, Search, Loader } from 'lucide-react';

const RepositoryIndexer = ({ onIndexRepository, isLoading, status }) => {
  const [repoUrl, setRepoUrl] = useState('');

  const isValidGitHubUrl = (url) => {
    try {
      const urlObj = new URL(url);
      return urlObj.hostname === 'github.com' && 
             urlObj.pathname.split('/').length >= 3 &&
             urlObj.protocol === 'https:';
    } catch {
      return false;
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!repoUrl.trim()) return;
    
    if (!isValidGitHubUrl(repoUrl)) {
      alert('Please enter a valid GitHub repository URL (e.g., https://github.com/username/repository)');
      return;
    }
    
    onIndexRepository(repoUrl);
  };

  const getStatusIcon = () => {
    if (status?.status === "indexing") return <Loader className="animate-spin" size={20} />;
    if (status?.status === "ready") return <Search size={20} className="text-green-600" />;
    if (status?.status === "error") return <Github size={20} className="text-red-600" />;
    return null;
  };

  const getStatusClass = () => {
    if (status?.status === "indexing") return "status-indexing";
    if (status?.status === "ready") return "status-ready";
    if (status?.status === "error") return "status-error";
    return "";
  };

  return (
    <div className="card">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-primary-100 rounded-lg">
          <Search size={24} className="text-primary-600" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900">Index Repository</h2>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label htmlFor="repoUrl" className="block text-sm font-semibold text-gray-700 mb-2">
            GitHub Repository URL
          </label>
          <input
            type="url"
            id="repoUrl"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            placeholder="https://github.com/username/repository"
            className="input-field"
            required
            disabled={isLoading}
          />
        </div>
        
        <button 
          type="submit" 
          className="btn-primary w-full justify-center" 
          disabled={isLoading || !repoUrl.trim()}
        >
          {isLoading ? (
            <>
              <Loader className="animate-spin" size={20} />
              Indexing Repository...
            </>
          ) : (
            <>
              <Github size={20} />
              Index Repository
            </>
          )}
        </button>
      </form>

      {status && (
        <div className={`${getStatusClass()} mt-6`}>
          {getStatusIcon()}
          <div className="flex-1">
            <div className="font-medium">{status.message}</div>
            {status.progress !== undefined && (
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${status.progress}%` }}
                />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default RepositoryIndexer;
