'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import SiteForm from '@/components/SiteForm';
import { api, Site } from '@/utils/api';

export default function EditSitePage() {
  const params = useParams();
  const [site, setSite] = useState<Site | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const siteId = params.id as string;

  useEffect(() => {
    if (siteId) {
      loadSite();
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
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <SiteForm siteId={siteId} initialData={site} />
    </div>
  );
}
