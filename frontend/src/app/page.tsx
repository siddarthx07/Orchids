"use client";

import { useState, useEffect, useRef } from "react";
import { CloneStatus, CloneResult } from "./types";
import { useWebSocket } from "./hooks/useWebSocket";

export default function Home() {
  const [url, setUrl] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [requestId, setRequestId] = useState<string | null>(null);
  const [cloneStatus, setCloneStatus] = useState<CloneStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [clonedUrl, setClonedUrl] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string>("");
  
  // WebSocket hook
  const webSocket = useWebSocket<{
    request_id: string;
    status: CloneStatus;
    url?: string;
    error?: string;
    message?: string;
  }>((id: string) => `ws://localhost:8080/ws/${id}`);

  // Handle URL input change
  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setUrl(e.target.value);
  };

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate URL
    if (!url) {
      setError("Please enter a URL");
      return;
    }

    try {
      // Reset any previous state
      setIsLoading(true);
      setError(null);
      setClonedUrl(null);
      setStatusMessage("");
      
      // Disconnect any existing WebSocket connection
      webSocket.disconnect();

      // Make API call to start cloning process
      const response = await fetch("http://localhost:8080/api/clone", {  
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to start cloning process");
      }

      const data = await response.json();
      setRequestId(data.request_id);
      setCloneStatus(data.status);
      setStatusMessage("Starting clone process...");
      
      // Connect to WebSocket for real-time updates
      webSocket.connect(data.request_id);
    } catch (err: any) {
      console.error("Submit error:", err);
      setError(err.message || "An error occurred");
      setIsLoading(false);
    }
  };

  // Handle WebSocket messages
  useEffect(() => {
    if (webSocket.lastMessage && requestId === webSocket.activeRequestId) {
      const message = webSocket.lastMessage;
      console.log('WebSocket update:', message);
      
      // Update status
      setCloneStatus(message.status);
      
      // Update status message if provided
      if (message.message) {
        setStatusMessage(message.message);
      }
      
      // Handle completion
      if (message.status === "completed") {
        setClonedUrl(`http://localhost:8080/api/clone/${message.request_id}/html`);
        setIsLoading(false);
      } 
      // Handle failure
      else if (message.status === "failed") {
        setError(message.error || "An unknown error occurred");
        setIsLoading(false);
      }
    }
  }, [webSocket.lastMessage, requestId, webSocket.activeRequestId]);
  
  // Clean up WebSocket on unmount
  useEffect(() => {
    return () => {
      webSocket.disconnect();
    };
  }, []);

  // Render status indicator
  const renderStatusIndicator = () => {
    if (cloneStatus === "idle") return null;

    const getStatusColor = () => {
      switch (cloneStatus) {
        case "pending":
        case "scraping":
        case "cloning":
          return "bg-blue-100 border-blue-400 text-blue-700";
        case "completed":
          return "bg-green-100 border-green-400 text-green-700";
        case "failed":
          return "bg-red-100 border-red-400 text-red-700";
        default:
          return "bg-gray-100 border-gray-400 text-gray-700";
      }
    };

    const getStatusMessage = () => {
      if (statusMessage) {
        return statusMessage;
      }
      
      switch (cloneStatus) {
        case "pending":
          return "Preparing to clone...";
        case "scraping":
          return "Scraping website content...";
        case "cloning":
          return "Generating clone with AI...";
        case "completed":
          return "Clone completed successfully!";
        case "failed":
          return `Cloning failed: ${error || "Unknown error"}`;
        default:
          return "Processing...";
      }
    };

    return (
      <div className={`${getStatusColor()} border px-4 py-3 rounded mb-6 relative`}>
        <p className="font-bold">
          {cloneStatus === "completed" ? "Success!" : cloneStatus.charAt(0).toUpperCase() + cloneStatus.slice(1)}
        </p>
        <p>{getStatusMessage()}</p>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      <div className="container max-w-5xl mx-auto px-4 py-8">
        <header className="flex flex-col items-center justify-center py-8">
          <h1 className="text-4xl font-bold mb-2 text-center bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">Website Cloner</h1>
          <p className="text-lg text-center text-gray-600 dark:text-gray-400 mb-8">
            Enter any website URL and get an AI-generated clone using Gemini 1.5 Pro and Browserbase
          </p>
        </header>

        <main className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 mb-8">
          <form onSubmit={handleSubmit} className="mb-8">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-grow">
                <label htmlFor="url" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Website URL
                </label>
                <input
                  type="text"
                  id="url"
                  placeholder="https://example.com"
                  value={url}
                  onChange={handleUrlChange}
                  disabled={isLoading}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                />
              </div>
              <div className="self-end">
                <button
                  type="submit"
                  disabled={isLoading}
                  className={`px-6 py-2 ${isLoading ? 'bg-gray-400' : 'bg-blue-600 hover:bg-blue-700'} text-white rounded-md transition-colors font-medium flex items-center gap-2`}
                >
                  {isLoading ? (
                    <>
                      <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Processing
                    </>
                  ) : (
                    'Clone Website'
                  )}
                </button>
              </div>
            </div>
          </form>

          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
              <p>{error}</p>
            </div>
          )}

          {renderStatusIndicator()}

          {clonedUrl && cloneStatus === "completed" && (
            <div className="mt-8">
              <h2 className="text-xl font-bold mb-4">Preview</h2>
              <div className="border border-gray-300 dark:border-gray-600 rounded-md overflow-hidden">
                <iframe
                  src={clonedUrl}
                  className="w-full"
                  style={{ height: '800px', minHeight: '80vh' }}
                  title="Cloned website preview"
                  sandbox="allow-same-origin allow-scripts allow-forms"
                  referrerPolicy="no-referrer"
                  loading="lazy"
                />
              </div>
              <div className="mt-4 flex justify-end">
                <a 
                  href={clonedUrl} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                >
                  Open in New Tab
                </a>
              </div>
            </div>
          )}

          {cloneStatus === "failed" && error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
              <p className="font-bold">Cloning failed</p>
              <p>{error}</p>
            </div>
          )}
        </main>

        <footer className="text-center text-gray-500 dark:text-gray-400 text-sm">
          <p>Built with Next.js, FastAPI, Browserbase SDK with Playwright, and Gemini 1.5 Pro</p>
        </footer>
      </div>
    </div>
  );
}
