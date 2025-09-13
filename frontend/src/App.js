import React, { useState, useEffect } from "react";
import axios from "axios";
import "./index.css";

// Components
import { Header, RepositoryIndexer, ChatInterface, ErrorState } from "./components";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

function App() {
  const [sessionId, setSessionId] = useState(null);
  const [status, setStatus] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isAskingQuestion, setIsAskingQuestion] = useState(false);

  // Poll for status updates
  useEffect(() => {
    if (sessionId && status?.status === "indexing") {
      const interval = setInterval(async () => {
        try {
          const response = await axios.get(
            `${API_BASE_URL}/status/${sessionId}`
          );
          setStatus(response.data);

          if (
            response.data.status === "ready" ||
            response.data.status === "error"
          ) {
            clearInterval(interval);
          }
        } catch (error) {
          console.error("Error checking status:", error);
          clearInterval(interval);
        }
      }, 2000);

      return () => clearInterval(interval);
    }
  }, [sessionId, status?.status]);

  const handleIndexRepository = async (repoUrl) => {
    setIsLoading(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/index`, {
        repo_url: repoUrl,
      });

      setSessionId(response.data.session_id);
      setStatus({
        status: "indexing",
        message: "Starting repository cloning...",
        progress: 0,
      });
      setMessages([]);
    } catch (error) {
      console.error("Error indexing repository:", error);
      let errorMessage = "Failed to start indexing. Please check the repository URL and try again.";
      
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.response?.status === 400) {
        errorMessage = "Invalid URL. Please provide a valid GitHub repository URL.";
      }
      
      setStatus({
        status: "error",
        message: errorMessage,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleAskQuestion = async (question) => {
    if (!question.trim() || !sessionId || isAskingQuestion) return;

    const userMessage = { type: "user", content: question };
    setMessages((prev) => [...prev, userMessage]);
    setIsAskingQuestion(true);

    try {
      const response = await axios.post(`${API_BASE_URL}/query`, {
        session_id: sessionId,
        question: question,
      });

      const assistantMessage = {
        type: "assistant",
        content: response.data.answer,
        sources: response.data.sources,
        confidence: response.data.confidence,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Error asking question:", error);
      const errorMessage = {
        type: "assistant",
        content:
          "Sorry, I encountered an error while processing your question. Please try again.",
        sources: [],
        confidence: "low",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsAskingQuestion(false);
    }
  };

  const handleRetry = () => {
    setStatus(null);
    setSessionId(null);
    setMessages([]);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <Header />
        
        <RepositoryIndexer
          onIndexRepository={handleIndexRepository}
          isLoading={isLoading}
          status={status}
        />

        {status?.status === "ready" && (
          <ChatInterface
            messages={messages}
            onAskQuestion={handleAskQuestion}
            isLoading={isAskingQuestion}
          />
        )}

        {status?.status === "error" && (
          <ErrorState
            status={status}
            onRetry={handleRetry}
          />
        )}
      </div>
    </div>
  );
}

export default App;
