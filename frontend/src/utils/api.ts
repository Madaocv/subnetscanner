// Конфігурація API URL для різних середовищ
const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? 'http://localhost:8000'  // Для production
  : typeof window !== 'undefined' 
    ? 'http://localhost:8000'  // Для браузера (локальна розробка)
    : 'http://backend:8000';   // Для SSR в Docker

// Експортуємо функцію для отримання повного URL
export const getApiUrl = (endpoint: string) => {
  // Видаляємо початковий слеш якщо є
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
  return `${API_BASE_URL}/${cleanEndpoint}`;
};

export { API_BASE_URL };

export interface Miner {
  id?: number;
  model: string;
  quantity: number;
  subsection_id?: number;
  created_at?: string;
  updated_at?: string;
}

export interface Subsection {
  id?: number;
  name: string;
  ip_ranges: string[];
  miners: Miner[];
  site_id?: number;
  created_at?: string;
  updated_at?: string;
}

export interface SubsectionCreate {
  name: string;
  ip_ranges: string[];
  miners: {
    model: string;
    quantity: number;
  }[];
}

export interface Site {
  id: number;
  name: string;
  username: string;
  password: string;
  timeout: number;
  subsections: Subsection[];
  created_at: string;
  updated_at: string;
}

export interface SiteCreate {
  name: string;
  username: string;
  password: string;
  timeout: number;
  subsections: SubsectionCreate[];
}

export interface DeviceType {
  id?: number;
  name: string;
  hashrate: number;
  HB: number;
  fans: number;
  created_at?: string;
  updated_at?: string;
}

export interface DeviceCreate {
  name: string;
  hashrate: number;
  HB: number;
  fans: number;
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorMessage = `HTTP error! status: ${response.status}`;
    
    try {
      const errorData = await response.json();
      if (errorData && errorData.detail) {
        errorMessage = errorData.detail;
      }
    } catch (jsonError) {
      // If response is not JSON, use generic message
      console.log('Failed to parse error response as JSON:', jsonError);
    }
    
    throw new ApiError(response.status, errorMessage);
  }
  return response.json();
}

export const api = {
  // Sites
  async getSites(): Promise<Site[]> {
    const response = await fetch(`${API_BASE_URL}/sites/`);
    return handleResponse<Site[]>(response);
  },

  async getSite(siteId: number): Promise<Site> {
    const response = await fetch(`${API_BASE_URL}/sites/${siteId}`);
    return handleResponse<Site>(response);
  },

  async createSite(site: SiteCreate): Promise<Site> {
    const response = await fetch(`${API_BASE_URL}/sites/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(site),
    });
    return handleResponse<Site>(response);
  },

  async updateSite(siteId: number, site: Partial<SiteCreate>): Promise<Site> {
    const response = await fetch(`${API_BASE_URL}/sites/${siteId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(site),
    });
    return handleResponse<Site>(response);
  },

  async deleteSite(siteId: number): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/sites/${siteId}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new ApiError(response.status, `HTTP error! status: ${response.status}`);
    }
  },

  // Device Types (renamed to match backend)
  async getDevices(): Promise<DeviceType[]> {
    const response = await fetch(`${API_BASE_URL}/devices/`);
    return handleResponse<DeviceType[]>(response);
  },

  async getDevice(deviceId: number): Promise<DeviceType> {
    const response = await fetch(`${API_BASE_URL}/devices/${deviceId}`);
    return handleResponse<DeviceType>(response);
  },

  async createDevice(device: DeviceCreate): Promise<DeviceType> {
    const response = await fetch(`${API_BASE_URL}/devices/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(device),
    });
    return handleResponse<DeviceType>(response);
  },

  async updateDevice(deviceId: number, device: Partial<DeviceCreate>): Promise<DeviceType> {
    const response = await fetch(`${API_BASE_URL}/devices/${deviceId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(device),
    });
    return handleResponse<DeviceType>(response);
  },

  async deleteDevice(deviceId: number): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/devices/${deviceId}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new ApiError(response.status, `HTTP error! status: ${response.status}`);
    }
  },
};
