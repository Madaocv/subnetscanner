'use client';

import { useState, useEffect } from 'react';
import { api, DeviceType, DeviceCreate } from '@/utils/api';

export default function DeviceTypesPage() {
  const [deviceTypes, setDeviceTypes] = useState<DeviceType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [editingDevice, setEditingDevice] = useState<DeviceType | null>(null);

  useEffect(() => {
    loadDeviceTypes();
  }, []);

  const loadDeviceTypes = async () => {
    try {
      setLoading(true);
      const data = await api.getDevices();
      setDeviceTypes(data);
      setError(null);
    } catch (err) {
      setError('Failed to load device types');
      console.error('Error loading device types:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (deviceId: number) => {
    if (!confirm('Are you sure you want to delete this device type?')) return;

    try {
      await api.deleteDevice(deviceId);
      await loadDeviceTypes();
    } catch (err) {
      setError('Failed to delete device type');
      console.error('Error deleting device type:', err);
    }
  };

  const handleEdit = (device: DeviceType) => {
    setEditingDevice(device);
    setShowModal(true);
  };

  const handleAdd = () => {
    setEditingDevice(null);
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setEditingDevice(null);
  };

  const handleSave = async () => {
    await loadDeviceTypes();
    handleCloseModal();
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <div className="flex">
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Error</h3>
            <div className="mt-2 text-sm text-red-700">
              <p>{error}</p>
            </div>
            <div className="mt-4">
              <button
                onClick={loadDeviceTypes}
                className="bg-red-100 px-3 py-2 rounded-md text-sm font-medium text-red-800 hover:bg-red-200"
              >
                Try again
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Device Types</h1>
        <button
          onClick={handleAdd}
          className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
        >
          Add Device Type
        </button>
      </div>

      {deviceTypes.length === 0 ? (
        <div className="text-center py-12">
          <h3 className="mt-2 text-sm font-medium text-gray-900">No device types</h3>
          <p className="mt-1 text-sm text-gray-500">Get started by creating a new device type.</p>
          <div className="mt-6">
            <button
              onClick={handleAdd}
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
            >
              Add Device Type
            </button>
          </div>
        </div>
      ) : (
        <div className="bg-white shadow overflow-hidden sm:rounded-md">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Hashrate
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Hash Boards
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Fans
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {deviceTypes.map((device) => (
                <tr key={device.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {device.name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {device.hashrate}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {device.HB}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {device.fans}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                    <button
                      onClick={() => handleEdit(device)}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(device.id!)}
                      className="text-red-600 hover:text-red-900"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <DeviceTypeModal
          device={editingDevice}
          onClose={handleCloseModal}
          onSave={handleSave}
        />
      )}
    </div>
  );
}

interface DeviceTypeModalProps {
  device: DeviceType | null;
  onClose: () => void;
  onSave: () => void;
}

function DeviceTypeModal({ device, onClose, onSave }: DeviceTypeModalProps) {
  const [formData, setFormData] = useState<DeviceCreate>({
    name: '',
    hashrate: '' as any,
    HB: '' as any,
    fans: '' as any,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (device) {
      setFormData(device);
    } else {
      // Reset form for new device with empty values
      setFormData({
        name: '',
        hashrate: '' as any,
        HB: '' as any,
        fans: '' as any,
      });
    }
  }, [device]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (device?.id) {
        await api.updateDevice(device.id, formData);
      } else {
        await api.createDevice(formData);
      }
      onSave();
    } catch (err: any) {
      setError(err.message || 'Failed to save device type');
      console.error('Error saving device type:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
        <div className="mt-3">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium text-gray-900">
              {device ? 'Edit Device Type' : 'Add Device Type'}
            </h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <span className="sr-only">Close</span>
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-3 mb-4">
              <div className="text-sm text-red-700">{error}</div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700">
                Name *
              </label>
              <input
                type="text"
                id="name"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                required
              />
            </div>

            <div>
              <label htmlFor="hashrate" className="block text-sm font-medium text-gray-700">
                Hashrate *
              </label>
              <input
                type="number"
                id="hashrate"
                value={formData.hashrate}
                onChange={(e) => setFormData(prev => ({ ...prev, hashrate: e.target.value === '' ? '' as any : parseInt(e.target.value) || 0 }))}
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                required
              />
            </div>

            <div>
              <label htmlFor="HB" className="block text-sm font-medium text-gray-700">
                Hash Boards *
              </label>
              <input
                type="number"
                id="HB"
                value={formData.HB}
                onChange={(e) => setFormData(prev => ({ ...prev, HB: e.target.value === '' ? '' as any : parseInt(e.target.value) || 0 }))}
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                required
              />
            </div>

            <div>
              <label htmlFor="fans" className="block text-sm font-medium text-gray-700">
                Fans *
              </label>
              <input
                type="number"
                id="fans"
                value={formData.fans}
                onChange={(e) => setFormData(prev => ({ ...prev, fans: e.target.value === '' ? '' as any : parseInt(e.target.value) || 0 }))}
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                required
              />
            </div>

            <div className="flex justify-end space-x-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Saving...' : (device ? 'Update' : 'Create')}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
