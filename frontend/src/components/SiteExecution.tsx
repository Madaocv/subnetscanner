'use client';

import { useState, useEffect } from 'react';

interface SiteExecutionProps {
  siteId: string;
}

interface Execution {
  id: number;
  site_id: number;
  status: string;
  result: any;
  created_at: string;
  updated_at: string;
}

export default function SiteExecution({ siteId }: SiteExecutionProps) {
  const [execution, setExecution] = useState<Execution | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResults, setExecutionResults] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  // Load latest execution on component mount
  useEffect(() => {
    loadLatestExecution();
  }, [siteId]);

  const loadLatestExecution = async () => {
    try {
      const response = await fetch(`http://localhost:8000/sites/${siteId}/executions`);
      if (response.ok) {
        const executions = await response.json();
        if (executions.length > 0) {
          const latest = executions[0]; // Assuming they're sorted by date
          setExecution(latest);
          updateExecutionResults(latest);
        }
      }
    } catch (err) {
      console.error('Error loading executions:', err);
    }
  };

  const updateExecutionResults = (exec: Execution) => {
    if (exec.status === 'pending') {
      setExecutionResults('Execution is pending...');
    } else if (exec.status === 'running') {
      setExecutionResults('Execution is running... Please wait (up to 2 minutes).');
    } else if (exec.status === 'completed') {
      const results = exec.result ? JSON.stringify(exec.result, null, 2) : 'No results available';
      setExecutionResults(`Execution completed successfully!\n\nResults:\n${results}`);
    } else if (exec.status === 'failed') {
      setExecutionResults(`Execution failed: ${exec.result?.error || 'Unknown error'}`);
    }
  };

  const handleExecute = async () => {
    setIsExecuting(true);
    setError(null);
    setExecutionResults('Starting site execution...');

    try {
      const response = await fetch(`http://localhost:8000/sites/${siteId}/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to start execution');
      }

      const newExecution = await response.json();
      setExecution(newExecution);
      setExecutionResults('Execution started successfully! Scanning in progress...\n\nThis may take up to 2 minutes to complete.');

      // Poll for execution status
      pollExecutionStatus(newExecution.id);
    } catch (err) {
      console.error('Error starting execution:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
      setExecutionResults(`Error starting execution: ${err instanceof Error ? err.message : 'Unknown error'}`);
      setIsExecuting(false);
    }
  };

  const pollExecutionStatus = async (execId: number) => {
    const maxPolls = 30; // 5 minutes max (10 second intervals)
    let pollCount = 0;

    const poll = async () => {
      try {
        const response = await fetch(`http://localhost:8000/executions/${execId}`);
        if (!response.ok) {
          throw new Error('Failed to get execution status');
        }

        const executionData = await response.json();
        setExecution(executionData);

        if (executionData.status === 'completed') {
          setIsExecuting(false);
          const results = executionData.result ? JSON.stringify(executionData.result, null, 2) : 'No results available';
          setExecutionResults(`Execution completed successfully!\n\nResults:\n${results}`);
        } else if (executionData.status === 'failed') {
          setIsExecuting(false);
          setExecutionResults(`Execution failed: ${executionData.result?.error || 'Unknown error'}`);
        } else if (pollCount < maxPolls) {
          // Continue polling
          pollCount++;
          setTimeout(poll, 10000); // Poll every 10 seconds
          setExecutionResults(`Execution in progress... (${pollCount}/${maxPolls})\n\nStatus: ${executionData.status}\n\nPlease wait while the scan completes.`);
        } else {
          setIsExecuting(false);
          setExecutionResults('Execution timed out. Please check the execution status manually.');
        }
      } catch (err) {
        console.error('Error polling execution status:', err);
        setIsExecuting(false);
        setExecutionResults(`Error checking execution status: ${err instanceof Error ? err.message : 'Unknown error'}`);
      }
    };

    poll();
  };

  return (
    <div className="mt-8 bg-white shadow rounded-lg p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-medium text-gray-900">Site Execution</h3>
        <button
          onClick={handleExecute}
          disabled={isExecuting}
          className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isExecuting ? 'Executing...' : 'Execute Scan'}
        </button>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-md p-3">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {execution && (
        <div className="mb-4 bg-gray-50 border border-gray-200 rounded-md p-3">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="font-medium text-gray-700">Status:</span>
              <span className={`ml-2 px-2 py-1 rounded-full text-xs ${
                execution.status === 'completed' ? 'bg-green-100 text-green-800' :
                execution.status === 'running' ? 'bg-blue-100 text-blue-800' :
                execution.status === 'failed' ? 'bg-red-100 text-red-800' :
                'bg-gray-100 text-gray-800'
              }`}>
                {execution.status}
              </span>
            </div>
            <div>
              <span className="font-medium text-gray-700">Last Updated:</span>
              <span className="ml-2 text-gray-600">
                {new Date(execution.updated_at).toLocaleString()}
              </span>
            </div>
          </div>
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Execution Results
        </label>
        <textarea
          value={executionResults}
          readOnly
          rows={12}
          className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 font-mono text-sm"
          placeholder="Execution results will appear here..."
        />
      </div>
    </div>
  );
}
