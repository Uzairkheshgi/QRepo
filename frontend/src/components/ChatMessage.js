import React from 'react';
import { User, Bot } from 'lucide-react';

const ChatMessage = ({ message, index }) => {
  const isUser = message.type === 'user';
  
  return (
    <div className={`flex gap-3 mb-6 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
        isUser ? 'bg-primary-500' : 'bg-gray-200'
      }`}>
        {isUser ? (
          <User size={16} className="text-white" />
        ) : (
          <Bot size={16} className="text-gray-600" />
        )}
      </div>
      
      <div className={`flex-1 max-w-[80%] ${isUser ? 'text-right' : 'text-left'}`}>
        <div className={`p-4 rounded-2xl ${
          isUser 
            ? 'bg-primary-500 text-white rounded-br-md' 
            : 'bg-white border border-gray-200 rounded-bl-md shadow-sm'
        }`}>
          <div className="whitespace-pre-wrap break-words">
            {message.content}
          </div>
        </div>
        
        {message.sources && message.sources.length > 0 && (
          <div className="mt-4 space-y-3">
            <h4 className="text-sm font-semibold text-gray-600 mb-2">
              Sources:
            </h4>
            {message.sources.map((source, sourceIndex) => (
              <div key={sourceIndex} className="source-item">
                <div className="source-file">{source.file}</div>
                <div className="source-snippet">{source.snippet}</div>
              </div>
            ))}
          </div>
        )}
        
        {message.confidence && (
          <div className={`mt-3 ${isUser ? 'text-right' : 'text-left'}`}>
            <span className={`confidence-${message.confidence}`}>
              Confidence: {message.confidence}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
