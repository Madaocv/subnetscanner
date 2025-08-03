'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { SiteCreate, Site, SubsectionCreate, DeviceType, DeviceCreate } from '../utils/api';

interface SiteFormProps {
  siteId?: string;
  initialData?: Site;
}

export default function SiteForm({ siteId, initialData }: SiteFormProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [devices, setDevices] = useState<DeviceType[]>([]);
  const [showCreateDeviceModal, setShowCreateDeviceModal] = useState(false);
  
  // Execution state for Execute button
  const [execution, setExecution] = useState<any>(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResults, setExecutionResults] = useState<string>('');
  const [executionError, setExecutionError] = useState<string | null>(null);

  const [newDevice, setNewDevice] = useState<DeviceCreate>({
    name: '',
    hashrate: '' as any,
    HB: '' as any,
    fans: '' as any
  });
  
  const [formData, setFormData] = useState<SiteCreate>({
    name: '',
    username: '',
    password: '',
    timeout: 20,
    subsections: [
      {
        name: '',
        ip_ranges: [''],
        miners: [{ model: '', quantity: 1 }]
      }
    ]
  });

  // Fetch devices on component mount
  useEffect(() => {
    fetchDevices();
    if (siteId) {
      loadLatestExecution();
    }
  }, [siteId]);

  useEffect(() => {
    if (initialData) {
      setFormData({
        name: initialData.name,
        username: initialData.username,
        password: initialData.password,
        timeout: initialData.timeout,
        subsections: initialData.subsections.map(sub => ({
          name: sub.name,
          ip_ranges: sub.ip_ranges,
          miners: sub.miners.map(miner => ({
            model: miner.model,
            quantity: miner.quantity
          }))
        }))
      });
    }
  }, [initialData]);

  const fetchDevices = async () => {
    try {
      const response = await fetch('http://localhost:8000/devices/');
      if (response.ok) {
        const devicesData = await response.json();
        setDevices(devicesData);
      }
    } catch (error) {
      console.error('Error fetching devices:', error);
    }
  };

  // Load latest execution on component mount
  const loadLatestExecution = async () => {
    if (!siteId) return;
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

  const updateExecutionResults = (exec: any) => {
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
          // Зберігаємо тільки stdout з очищенням непотрібних рядків
          let results = 'No results available';
          if (executionData.result?.stdout) {
            results = executionData.result.stdout
              .replace(/Complete scan results saved to:.*$/gm, '')
              .replace(/✅ Results saved to reports\/.*$/gm, '')
              .trim();
          } else if (executionData.result?.error) {
            results = `Error: ${executionData.result.error}`;
          }
          setExecutionResults(results);
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

  // Validate IP range format (e.g., 10.32.101.0/24)
  const validateIpRange = (ipRange: string): boolean => {
    if (!ipRange.trim()) return false;
    
    const ipRangeRegex = /^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\/(\d{1,2})$/;
    const match = ipRange.match(ipRangeRegex);
    
    if (!match) return false;
    
    const [, ip, cidr] = match;
    const ipParts = ip.split('.').map(Number);
    const cidrNum = parseInt(cidr);
    
    // Validate IP parts (0-255)
    if (ipParts.some(part => part < 0 || part > 255)) return false;
    
    // Validate CIDR (0-32)
    if (cidrNum < 0 || cidrNum > 32) return false;
    
    return true;
  };

  // Get validation error message for IP range with smart suggestions
  const getIpRangeError = (ipRange: string): string | null => {
    if (!ipRange.trim()) return null;
    if (validateIpRange(ipRange)) return null;
    
    // Try to provide smart suggestions based on user input
    const trimmed = ipRange.trim();
    
    // Check if it looks like an IP address without CIDR
    const ipOnlyRegex = /^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$/;
    const ipMatch = trimmed.match(ipOnlyRegex);
    
    if (ipMatch) {
      const [, ip] = ipMatch;
      const ipParts = ip.split('.').map(Number);
      
      // Check if IP parts are valid (0-255)
      if (ipParts.every(part => part >= 0 && part <= 255)) {
        // Suggest network address with /24
        const networkIp = `${ipParts[0]}.${ipParts[1]}.${ipParts[2]}.0`;
        return `Missing CIDR notation. Try: ${networkIp}/24`;
      }
    }
    
    // Check if it has CIDR but invalid IP
    const withCidrRegex = /^(.+)\/(\d{1,2})$/;
    const cidrMatch = trimmed.match(withCidrRegex);
    
    if (cidrMatch) {
      const [, ipPart, cidr] = cidrMatch;
      const cidrNum = parseInt(cidr);
      
      if (cidrNum < 0 || cidrNum > 32) {
        return `Invalid CIDR. Use range 0-32, e.g., ${ipPart}/24`;
      }
      
      // Try to fix IP part
      const ipParts = ipPart.split('.');
      if (ipParts.length === 4) {
        const fixedParts = ipParts.map(part => {
          const num = parseInt(part);
          return isNaN(num) || num < 0 || num > 255 ? '0' : part;
        });
        return `Invalid IP address. Try: ${fixedParts.join('.')}/24`;
      }
    }
    
    // Check if it's partially typed IP
    const partialIpRegex = /^(\d{1,3}(?:\.\d{1,3}){0,2})$/;
    if (partialIpRegex.test(trimmed)) {
      const parts = trimmed.split('.');
      const suggestion = [...parts, ...Array(4 - parts.length).fill('0')].join('.');
      return `Incomplete IP. Try: ${suggestion}/24`;
    }
    
    // Default fallback with example based on first valid digits
    const digits = trimmed.match(/\d+/g);
    if (digits && digits.length > 0) {
      const firstDigit = Math.min(255, parseInt(digits[0]));
      return `Invalid format. Try: ${firstDigit}.32.101.0/24`;
    }
    
    return 'Invalid format. Use: 10.32.101.0/24';
  };

  const handleCreateDevice = async () => {
    if (!newDevice.name || !newDevice.hashrate || !newDevice.HB || !newDevice.fans) {
      alert('Please fill in all device fields');
      return;
    }

    try {
      const deviceData = {
        name: newDevice.name,
        hashrate: typeof newDevice.hashrate === 'string' ? parseInt(newDevice.hashrate) : newDevice.hashrate,
        HB: typeof newDevice.HB === 'string' ? parseInt(newDevice.HB) : newDevice.HB,
        fans: typeof newDevice.fans === 'string' ? parseInt(newDevice.fans) : newDevice.fans
      };

      const response = await fetch('http://localhost:8000/devices/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(deviceData),
      });

      if (!response.ok) {
        throw new Error('Failed to create device');
      }

      const createdDevice = await response.json();
      setDevices(prev => [...prev, createdDevice]);
      setShowCreateDeviceModal(false);
      
      // Reset form with empty values
      setNewDevice({
        name: '',
        hashrate: '' as any,
        HB: '' as any,
        fans: '' as any
      });
    } catch (err) {
      console.error('Error creating device:', err);
      alert('Failed to create device');
    }
  };



  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    // Validate all IP ranges
    const invalidRanges: string[] = [];
    formData.subsections.forEach((subsection, subIndex) => {
      subsection.ip_ranges.forEach((range, rangeIndex) => {
        if (!range.trim()) {
          invalidRanges.push(`Subsection "${subsection.name}" - IP Range ${rangeIndex + 1} is required`);
        } else if (!validateIpRange(range)) {
          invalidRanges.push(`Subsection "${subsection.name}" - IP Range "${range}" has invalid format`);
        }
      });
    });

    // Validate all miners have selected devices
    const invalidDevices: string[] = [];
    formData.subsections.forEach((subsection, subIndex) => {
      subsection.miners.forEach((miner, minerIndex) => {
        if (!miner.model.trim()) {
          invalidDevices.push(`Subsection "${subsection.name}" - Miner ${minerIndex + 1} device is required`);
        }
      });
    });

    const allErrors = [...invalidRanges, ...invalidDevices];
    if (allErrors.length > 0) {
      setError(`Please fix the following errors:\n${allErrors.join('\n')}`);
      setLoading(false);
      return;
    }

    try {
      const siteData = {
        ...formData,
        username: 'admin',
        password: 'admin',
        timeout: 30
      };

      let response;
      if (siteId) {
        response = await fetch(`http://localhost:8000/sites/${siteId}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(siteData),
        });
      } else {
        response = await fetch('http://localhost:8000/sites/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(siteData),
        });
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to save site');
      }

      const savedSite = await response.json();
      
      // Redirect to edit page after save
      router.push(`/sites/${savedSite.id}/edit`);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleExecute = async () => {
    if (!siteId) {
      setExecutionError('Site must be saved before execution');
      return;
    }

    setIsExecuting(true);
    setExecutionError(null);
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
      setExecutionError(err instanceof Error ? err.message : 'Unknown error');
      setExecutionResults(`Error starting execution: ${err instanceof Error ? err.message : 'Unknown error'}`);
      setIsExecuting(false);
    }
  };

  const addSubsection = () => {
    setFormData(prev => ({
      ...prev,
      subsections: [
        ...prev.subsections,
        {
          name: '',
          ip_ranges: [''],
          miners: [{ model: '', quantity: 1 }]
        }
      ]
    }));
  };

  const removeSubsection = (index: number) => {
    setFormData(prev => ({
      ...prev,
      subsections: prev.subsections.filter((_, i) => i !== index)
    }));
  };

  const updateSubsection = (index: number, field: keyof SubsectionCreate, value: any) => {
    setFormData(prev => ({
      ...prev,
      subsections: prev.subsections.map((sub, i) => 
        i === index ? { ...sub, [field]: value } : sub
      )
    }));
  };

  const addIpRange = (subsectionIndex: number) => {
    setFormData(prev => ({
      ...prev,
      subsections: prev.subsections.map((sub, i) => 
        i === subsectionIndex 
          ? { ...sub, ip_ranges: [...sub.ip_ranges, ''] }
          : sub
      )
    }));
  };

  const updateIpRange = (subsectionIndex: number, rangeIndex: number, value: string) => {
    setFormData(prev => ({
      ...prev,
      subsections: prev.subsections.map((sub, i) => 
        i === subsectionIndex 
          ? { 
              ...sub, 
              ip_ranges: sub.ip_ranges.map((range, ri) => ri === rangeIndex ? value : range)
            }
          : sub
      )
    }));
  };

  const removeIpRange = (subsectionIndex: number, rangeIndex: number) => {
    setFormData(prev => ({
      ...prev,
      subsections: prev.subsections.map((sub, i) => 
        i === subsectionIndex 
          ? { ...sub, ip_ranges: sub.ip_ranges.filter((_, ri) => ri !== rangeIndex) }
          : sub
      )
    }));
  };

  const addMiner = (subsectionIndex: number) => {
    setFormData(prev => ({
      ...prev,
      subsections: prev.subsections.map((sub, i) => 
        i === subsectionIndex 
          ? { ...sub, miners: [...sub.miners, { model: '', quantity: 1 }] }
          : sub
      )
    }));
  };

  const updateMiner = (subsectionIndex: number, minerIndex: number, field: 'model' | 'quantity', value: string | number) => {
    setFormData(prev => ({
      ...prev,
      subsections: prev.subsections.map((sub, i) => 
        i === subsectionIndex 
          ? { 
              ...sub, 
              miners: sub.miners.map((miner, mi) => 
                mi === minerIndex ? { ...miner, [field]: value } : miner
              )
            }
          : sub
      )
    }));
  };

  const removeMiner = (subsectionIndex: number, minerIndex: number) => {
    setFormData(prev => ({
      ...prev,
      subsections: prev.subsections.map((sub, i) => 
        i === subsectionIndex 
          ? { ...sub, miners: sub.miners.filter((_, mi) => mi !== minerIndex) }
          : sub
      )
    }));
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">
        {siteId ? 'Edit Site' : 'Create New Site'}
      </h1>

      {error && (
        <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Site Info */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-lg font-semibold mb-4">Site Information</h2>
          
          <div className="grid grid-cols-1 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Site Name *
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
          </div>
        </div>

        {/* Subsections */}
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">Subsections</h2>
            <button
              type="button"
              onClick={addSubsection}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
            >
              Add Subsection
            </button>
          </div>

          {formData.subsections.map((subsection, subsectionIndex) => (
            <div key={subsectionIndex} className="border border-gray-200 rounded-lg p-4 mb-4">
              <div className="flex justify-between items-center mb-3">
                <h3 className="font-medium">Subsection {subsectionIndex + 1}</h3>
                {formData.subsections.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeSubsection(subsectionIndex)}
                    className="text-red-600 hover:text-red-800"
                  >
                    Remove
                  </button>
                )}
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Subsection Name *
                </label>
                <input
                  type="text"
                  value={subsection.name}
                  onChange={(e) => updateSubsection(subsectionIndex, 'name', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              {/* IP Ranges */}
              <div className="mb-4">
                <div className="flex justify-between items-center mb-2">
                  <label className="block text-sm font-medium text-gray-700">
                    IP Ranges <span className="text-red-500">*</span>
                  </label>
                  <button
                    type="button"
                    onClick={() => addIpRange(subsectionIndex)}
                    className="text-sm px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    Add IP Range
                  </button>
                </div>
                
                {subsection.ip_ranges.map((range, rangeIndex) => {
                  const error = getIpRangeError(range);
                  return (
                    <div key={rangeIndex} className="mb-3">
                      <div className="flex gap-2 mb-1">
                        <input
                          type="text"
                          value={range}
                          onChange={(e) => updateIpRange(subsectionIndex, rangeIndex, e.target.value)}
                          placeholder="10.32.101.0/24"
                          required
                          className={`flex-1 px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
                            error 
                              ? 'border-red-300 focus:ring-red-500 focus:border-red-500' 
                              : 'border-gray-300 focus:ring-blue-500 focus:border-blue-500'
                          }`}
                        />
                        {subsection.ip_ranges.length > 1 && (
                          <button
                            type="button"
                            onClick={() => removeIpRange(subsectionIndex, rangeIndex)}
                            className="px-3 py-2 text-red-600 hover:text-red-800"
                          >
                            Remove
                          </button>
                        )}
                      </div>
                      {error && (
                        <p className="text-sm text-red-600 mt-1">{error}</p>
                      )}
                      {!error && range.trim() === '' && (
                        <p className="text-sm text-gray-500 mt-1">
                          Format: IP_ADDRESS/CIDR (e.g., 10.32.101.0/24)
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Miners */}
              <div>
                <div className="flex justify-between items-center mb-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Miners
                  </label>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => addMiner(subsectionIndex)}
                      className="text-sm px-3 py-1 bg-purple-600 text-white rounded hover:bg-purple-700"
                    >
                      Add Miner
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowCreateDeviceModal(true)}
                      className="text-sm px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700"
                    >
                      Create Device Type
                    </button>
                  </div>
                </div>
                
                {subsection.miners.map((miner, minerIndex) => (
                  <div key={minerIndex} className="flex gap-2 mb-2">
                    <select
                      value={miner.model}
                      onChange={(e) => updateMiner(subsectionIndex, minerIndex, 'model', e.target.value)}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    >
                      <option value="">Select device...</option>
                      {devices.map((device) => (
                        <option key={device.id} value={device.name}>
                          {device.name} ({device.hashrate}TH/s, {device.HB}HB, {device.fans}fans)
                        </option>
                      ))}
                    </select>
                    <input
                      type="number"
                      value={miner.quantity}
                      onChange={(e) => updateMiner(subsectionIndex, minerIndex, 'quantity', parseInt(e.target.value) || 1)}
                      placeholder="Qty"
                      className="w-20 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      min="1"
                    />
                    {subsection.miners.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeMiner(subsectionIndex, minerIndex)}
                        className="px-3 py-2 text-red-600 hover:text-red-800"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Submit Button */}
        <div className="flex gap-4">
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Saving...' : (siteId ? 'Update Site' : 'Create Site')}
          </button>
          
          <button
            type="button"
            onClick={() => router.push('/sites')}
            className="px-6 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
          >
            Cancel
          </button>
          
          {/* Execute button - only show for existing sites */}
          {siteId && (
            <button
              type="button"
              onClick={handleExecute}
              disabled={isExecuting}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isExecuting ? 'Executing...' : 'Execute Scan'}
            </button>
          )}

        </div>
        
        {/* Execution error display */}
        {executionError && (
          <div className="mt-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
            {executionError}
          </div>
        )}
        
        {/* Execution results display */}
        {siteId && (executionResults || execution) && (
          <div className="mt-6 bg-white shadow rounded-lg p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium text-gray-900">Site Execution</h3>
            </div>

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
                    <span className="font-medium text-gray-700">Created:</span>
                    <span className="ml-2 text-gray-600">
                      {new Date(execution.created_at).toLocaleString()}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {executionResults && (
              <div className="bg-gray-50 border border-gray-200 rounded-md p-3">
                <h4 className="text-sm font-medium text-gray-700 mb-2">Scan Results:</h4>
                <div className="bg-white p-4 rounded border max-h-96 overflow-y-auto">
                  {(() => {
                    // Перевіряємо, чи це помилка
                    if (executionResults.startsWith('Error:') || executionResults.includes('failed')) {
                      return (
                        <div className="text-red-600">
                          <pre className="text-sm whitespace-pre-wrap">{executionResults}</pre>
                        </div>
                      );
                    }
                    
                    // Перевіряємо, чи це старий формат з JSON (містить "Results:" та JSON)
                    if (executionResults.includes('Results:') && executionResults.includes('{')) {
                      try {
                        // Витягуємо JSON частину
                        const jsonStart = executionResults.indexOf('{');
                        const jsonPart = executionResults.substring(jsonStart);
                        const parsed = JSON.parse(jsonPart);
                        
                        if (parsed.stdout) {
                          const cleanedStdout = parsed.stdout
                            .replace(/Complete scan results saved to:.*$/gm, '')
                            .replace(/✅ Results saved to reports\/.*$/gm, '')
                            .trim();
                          
                          return (
                            <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono leading-relaxed">
                              {cleanedStdout}
                            </pre>
                          );
                        }
                      } catch (e) {
                        // Якщо не вдалося парсити, показуємо як є
                      }
                    }
                    
                    // Показуємо як звичайний текст
                    return (
                      <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono leading-relaxed">
                        {executionResults}
                      </pre>
                    );
                  })()}
                </div>
              </div>
            )}
          </div>
        )}
      </form>



      {/* Create Device Modal */}
      {showCreateDeviceModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-semibold mb-4">Create New Device</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Device Name *
                </label>
                <input
                  type="text"
                  value={newDevice.name}
                  onChange={(e) => setNewDevice(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., Antminer S19"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Hashrate (TH/s) *
                </label>
                <input
                  type="number"
                  value={newDevice.hashrate}
                  onChange={(e) => setNewDevice(prev => ({ ...prev, hashrate: e.target.value === '' ? '' : parseInt(e.target.value) || '' }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., 110"
                  min="0"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Hash Boards (HB) *
                </label>
                <input
                  type="number"
                  value={newDevice.HB}
                  onChange={(e) => setNewDevice(prev => ({ ...prev, HB: e.target.value === '' ? '' : parseInt(e.target.value) || '' }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., 3"
                  min="0"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Fans *
                </label>
                <input
                  type="number"
                  value={newDevice.fans}
                  onChange={(e) => setNewDevice(prev => ({ ...prev, fans: e.target.value === '' ? '' : parseInt(e.target.value) || '' }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., 4"
                  min="0"
                  required
                />
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                type="button"
                onClick={handleCreateDevice}
                disabled={!newDevice.name || !newDevice.hashrate || !newDevice.HB || !newDevice.fans || Number(newDevice.hashrate) <= 0 || Number(newDevice.HB) <= 0 || Number(newDevice.fans) <= 0}
                className="flex-1 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Create Device
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowCreateDeviceModal(false);
                  setNewDevice({ name: '', hashrate: '' as any, HB: '' as any, fans: '' as any });
                }}
                className="flex-1 px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
