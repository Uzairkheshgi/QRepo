import React from 'react';
import { Github } from 'lucide-react';

const Header = () => {
  return (
    <div className="text-center mb-10 py-12 px-8 bg-gradient-to-br from-primary-500 via-primary-600 to-primary-700 text-white rounded-2xl shadow-2xl">
      <div className="flex justify-center mb-4">
        <Github size={64} className="text-white/90" />
      </div>
      <h1 className="text-4xl md:text-5xl font-bold mb-4 bg-gradient-to-r from-white to-white/90 bg-clip-text text-transparent">
        GitHub Repository Q&A Tool
      </h1>
      <p className="text-lg md:text-xl text-white/90 max-w-2xl mx-auto leading-relaxed">
        Index any public GitHub repository and ask questions about its codebase using advanced AI
      </p>
    </div>
  );
};

export default Header;
