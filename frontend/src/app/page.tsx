import Link from 'next/link';

export default function Home() {
  return (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Site Management System
        </h1>
        <p className="text-xl text-gray-600">
          Manage your mining sites, racks, and device types
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Sites Section */}
        <div className="bg-white rounded-lg shadow-lg p-8 hover:shadow-xl transition-shadow">
          <div className="text-center">
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
            </div>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">Sites Management</h2>
            <p className="text-gray-600 mb-6">
              View, create, and manage mining sites with their subsections, IP ranges, and miner configurations.
            </p>
            <div className="space-y-3">
              <Link
                href="/sites"
                className="block w-full bg-blue-600 text-white px-6 py-3 rounded-md hover:bg-blue-700 transition-colors font-medium"
              >
                View All Sites
              </Link>
              <Link
                href="/sites/new"
                className="block w-full bg-blue-100 text-blue-700 px-6 py-3 rounded-md hover:bg-blue-200 transition-colors font-medium"
              >
                Create New Site
              </Link>
            </div>
          </div>
        </div>

        {/* Device Types Section */}
        <div className="bg-white rounded-lg shadow-lg p-8 hover:shadow-xl transition-shadow">
          <div className="text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
              </svg>
            </div>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">Device Types</h2>
            <p className="text-gray-600 mb-6">
              Manage mining device specifications including hashrate, hash boards, fans, and other technical details.
            </p>
            <div className="space-y-3">
              <Link
                href="/device-types"
                className="block w-full bg-green-600 text-white px-6 py-3 rounded-md hover:bg-green-700 transition-colors font-medium"
              >
                View Device Types
              </Link>
              <Link
                href="/device-types"
                className="block w-full bg-green-100 text-green-700 px-6 py-3 rounded-md hover:bg-green-200 transition-colors font-medium text-center"
              >
                Create Device Type
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Stats or Additional Info */}
      {/* <div className="mt-12 bg-gray-100 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 text-center">
          Quick Navigation
        </h3>
        <div className="flex flex-wrap justify-center gap-4">
          <Link
            href="/sites"
            className="inline-flex items-center px-4 py-2 bg-white rounded-md shadow-sm hover:shadow-md transition-shadow text-gray-700 hover:text-blue-600"
          >
            📍 Sites List
          </Link>
          <Link
            href="/device-types"
            className="inline-flex items-center px-4 py-2 bg-white rounded-md shadow-sm hover:shadow-md transition-shadow text-gray-700 hover:text-green-600"
          >
            ⚙️ Device Types
          </Link>
        </div>
      </div> */}
    </div>
  );
}
