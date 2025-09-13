import React, { useState, useRef, useEffect } from 'react';
import { MessageCircle, Send, Bot } from 'lucide-react';
import ChatMessage from './ChatMessage';

const ChatInterface = ({ messages, onAskQuestion, isLoading = false }) => {
  const [question, setQuestion] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!question.trim() || isLoading) return;
    
    onAskQuestion(question);
    setQuestion('');
  };

  return (
    <div className="card">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-green-100 rounded-lg">
          <MessageCircle size={24} className="text-green-600" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900">Chat with Repo</h2>
      </div>

      {messages.length > 0 ? (
        <div className="space-y-4 mb-6">
          <div className="max-h-96 overflow-y-auto p-4 bg-gray-50 rounded-xl border border-gray-200">
            {messages.map((message, index) => (
              <ChatMessage key={index} message={message} index={index} />
            ))}
            {isLoading && (
              <div className="flex gap-3 mb-6">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
                  <Bot size={16} className="text-gray-600" />
                </div>
                <div className="flex-1 max-w-[80%]">
                  <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-md shadow-sm p-4">
                    <div className="flex items-center gap-2 text-gray-500">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                      </div>
                      <span className="text-sm">AI is thinking...</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>
      ) : (
        <div className="text-center py-12 mb-6">
          <p className="text-gray-500 max-w-md mx-auto">
            Ask questions about the codebase you just indexed.
          </p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex gap-3">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about the codebase..."
          className="input-field flex-1"
          required
          disabled={isLoading}
        />
        <button 
          type="submit" 
          className="btn-primary px-6"
          disabled={isLoading || !question.trim()}
        >
          {isLoading ? (
            <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent" />
          ) : (
            <Send size={20} />
          )}
        </button>
      </form>
    </div>
  );
};

export default ChatInterface;
