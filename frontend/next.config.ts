import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Дозволяємо підключення до backend в Docker
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://backend:8000/:path*', // Проксі до backend контейнера
      },
    ];
  },
  // Налаштування для development в Docker
  experimental: {
    serverComponentsExternalPackages: [],
  },
};

export default nextConfig;
