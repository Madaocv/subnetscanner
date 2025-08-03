'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { api, Site } from '@/utils/api';

export default function SiteDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [site, setSite] = useState<Site | null>(null);
  const [executions, setExecutions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedExecution, setExpandedExecution] = useState<number | null>(null);

  const siteId = params.id as string;

  useEffect(() => {
    if (siteId) {
      loadSite();
      loadExecutions();
    }
  }, [siteId]);

  const loadSite = async () => {
    try {
      setLoading(true);
      const response = await fetch(`http://localhost:8000/sites/${siteId}`);
      if (response.ok) {
        const siteData = await response.json();
        setSite(siteData);
        setError(null);
      } else {
        throw new Error('Failed to fetch site');
      }
    } catch (err) {
      setError('Failed to load site');
      console.error('Error loading site:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadExecutions = async () => {
    try {
      const response = await fetch(`http://localhost:8000/sites/${siteId}/executions`);
      if (response.ok) {
        const executionsData = await response.json();
        setExecutions(executionsData);
      } else {
        console.error('Failed to fetch executions');
      }
    } catch (err) {
      console.error('Error loading executions:', err);
    }
  };

  const handleDelete = async () => {
    if (!confirm(`Are you sure you want to delete site ${site?.name}?`)) return;

    try {
      const response = await fetch(`http://localhost:8000/sites/${siteId}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        router.push('/sites');
      } else {
        throw new Error('Failed to delete site');
      }
    } catch (err) {
      setError('Failed to delete site');
      console.error('Error deleting site:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error || !site) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <div className="flex">
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Error</h3>
            <div className="mt-2 text-sm text-red-700">
              <p>{error || 'Site not found'}</p>
            </div>
            <div className="mt-4">
              <Link
                href="/"
                className="bg-red-100 px-3 py-2 rounded-md text-sm font-medium text-red-800 hover:bg-red-200"
              >
                Back to Sites
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const totalMiners = site.subsections.reduce((total, subsection) => {
    return total + subsection.miners.reduce((subTotal, miner) => subTotal + miner.quantity, 0);
  }, 0);

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Site: {site.name}
          </h1>
          <p className="text-gray-600">ID: {site.id}</p>
        </div>
        <div className="flex space-x-3">
          <Link
            href="/"
            className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
          >
            Back to Sites
          </Link>
          <Link
            href={`/sites/${site.id}/edit`}
            className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
          >
            Edit Site
          </Link>
          <button
            onClick={handleDelete}
            className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700"
          >
            Delete Site
          </button>
        </div>
      </div>

      <div className="bg-white shadow overflow-hidden sm:rounded-lg mb-8">
        <div className="px-4 py-5 sm:px-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900">Site Overview</h3>
          <p className="mt-1 max-w-2xl text-sm text-gray-500">Basic information about this site.</p>
        </div>
        <div className="border-t border-gray-200 px-4 py-5 sm:px-6">
          <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
            <div>
              <dt className="text-sm font-medium text-gray-500">Site ID</dt>
              <dd className="mt-1 text-sm text-gray-900">{site.id}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Site Name</dt>
              <dd className="mt-1 text-sm text-gray-900">{site.name}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Total Subsections</dt>
              <dd className="mt-1 text-sm text-gray-900">{site.subsections.length}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Total Miners</dt>
              <dd className="mt-1 text-sm text-gray-900">{totalMiners}</dd>
            </div>
          </dl>
        </div>
      </div>

      {/* Executions Section */}
      <div className="bg-white shadow overflow-hidden sm:rounded-lg mb-8">
        <div className="px-4 py-5 sm:px-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900">Execution History</h3>
          <p className="mt-1 max-w-2xl text-sm text-gray-500">All scan executions for this site.</p>
        </div>
        <div className="border-t border-gray-200">
          {executions.length === 0 ? (
            <div className="px-4 py-5 sm:px-6 text-center text-gray-500">
              No executions found for this site.
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {executions.map((execution) => (
                <div key={execution.id}>
                  <div
                    onClick={() => setExpandedExecution(expandedExecution === execution.id ? null : execution.id)}
                    className="px-4 py-4 hover:bg-gray-50 cursor-pointer transition-colors duration-150"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4">
                        <div>
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            execution.status === 'completed' ? 'bg-green-100 text-green-800' :
                            execution.status === 'running' ? 'bg-blue-100 text-blue-800' :
                            execution.status === 'failed' ? 'bg-red-100 text-red-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            Status: {execution.status}
                          </span>
                        </div>
                        <div className="text-sm text-gray-500">
                          Created: {new Date(execution.created_at).toLocaleString('uk-UA', {
                            day: '2-digit',
                            month: '2-digit',
                            year: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                            second: '2-digit'
                          })}
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <div className="text-sm text-gray-400">
                          {expandedExecution === execution.id ? 'Hide details' : 'Show details'}
                        </div>
                        <div className={`transform transition-transform duration-200 ${
                          expandedExecution === execution.id ? 'rotate-180' : ''
                        }`}>
                          ▼
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Випадаючий блок з деталями */}
                  {expandedExecution === execution.id && (
                    <div className="px-4 pb-4 bg-gray-50 border-t border-gray-200">
                      <div className="pt-4 space-y-4">
                        <div className="grid grid-cols-2 gap-4">
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
                            <span className="font-medium text-gray-700">Created:</span>
                            <span className="ml-2 text-gray-600">
                              {new Date(execution.created_at).toLocaleString()}
                            </span>
                          </div>
                        </div>
                        
                        {execution.result && (
                          <div>
                            <h4 className="text-sm font-medium text-gray-700 mb-2">Scan Results:</h4>
                            <div className="bg-white p-4 rounded border max-h-96 overflow-y-auto">
                              {execution.result.stdout ? (
                                <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono leading-relaxed">
                                  {execution.result.stdout
                                    .replace(/Complete scan results saved to:.*$/gm, '')
                                    .replace(/✅ Results saved to reports\/.*$/gm, '')
                                    .trim()
                                  }
                                </pre>
                              ) : execution.result.error ? (
                                <div className="text-red-600">
                                  <p className="font-medium mb-2">Error occurred:</p>
                                  <pre className="text-sm whitespace-pre-wrap">{execution.result.error}</pre>
                                </div>
                              ) : (
                                <div className="text-gray-500 italic">
                                  No scan output available
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>



      <div className="space-y-6">
        {site.subsections.map((subsection, index) => (
          <div key={index} className="bg-white shadow overflow-hidden sm:rounded-lg">
            <div className="px-4 py-5 sm:px-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900">{subsection.name}</h3>
            </div>
            <div className="border-t border-gray-200">
              <div className="px-4 py-5 sm:px-6">
                <h4 className="text-sm font-medium text-gray-500 mb-3">IP Ranges</h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                  {subsection.ip_ranges.map((range, rangeIndex) => (
                    <span
                      key={rangeIndex}
                      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                    >
                      {range}
                    </span>
                  ))}
                </div>
              </div>
              <div className="px-4 py-5 sm:px-6 border-t border-gray-200">
                <h4 className="text-sm font-medium text-gray-500 mb-3">Miners</h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {subsection.miners.map((miner, minerIndex) => (
                    <div
                      key={minerIndex}
                      className="bg-gray-50 rounded-lg p-3"
                    >
                      <div className="text-sm font-medium text-gray-900">{miner.model}</div>
                      <div className="text-sm text-gray-500">Quantity: {miner.quantity}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
