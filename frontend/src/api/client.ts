import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Model APIs
export const modelApi = {
  getAll: () => apiClient.get('/models'),
  getById: (id: string) => apiClient.get(`/models/${id}`),
  create: (data: { name: string; provider: string; baseUrl: string; apiKey: string }) => 
    apiClient.post('/models', data),
  update: (id: string, data: { name?: string; provider?: string; baseUrl?: string; apiKey?: string; isDefault?: boolean }) => 
    apiClient.put(`/models/${id}`, data),
  delete: (id: string) => apiClient.delete(`/models/${id}`),
  test: (data: { name: string; provider: string; baseUrl: string; apiKey: string }) => 
    apiClient.post('/models/test', data),
};

// Account APIs
export const accountApi = {
  getAll: () => apiClient.get('/accounts'),
  getById: (id: string) => apiClient.get(`/accounts/${id}`),
  create: (data: { name: string; exchange: string; apiKey: string; apiSecret: string; passphrase: string; isSimulated: boolean }) =>
    apiClient.post('/accounts', data),
  update: (id: string, data: { name?: string; exchange?: string; apiKey?: string; apiSecret?: string; passphrase?: string; isSimulated?: boolean }) =>
    apiClient.put(`/accounts/${id}`, data),
  delete: (id: string) => apiClient.delete(`/accounts/${id}`),
  test: (id: string) => apiClient.post(`/accounts/${id}/test`),
  testConfig: (data: { exchange: string; apiKey: string; apiSecret: string; passphrase: string; isSimulated: boolean }) =>
    apiClient.post('/accounts/test', data),
  getExchanges: () => apiClient.get('/exchanges'),
};

// Task APIs
export const taskApi = {
  getAll: () => apiClient.get('/tasks'),
  getById: (id: string) => apiClient.get(`/tasks/${id}`),
  create: (data: {
    name: string;
    symbol: string;
    tradingRules: string;
    interval: string;
    dailyTime?: string;
    modelId: string;
    accountId: string;
  }) => apiClient.post('/tasks', data),
  update: (id: string, data: Partial<{
    name: string;
    symbol: string;
    tradingRules: string;
    interval: string;
    dailyTime: string;
    modelId: string;
    accountId: string;
    isActive: boolean;
  }>) => apiClient.put(`/tasks/${id}`, data),
  delete: (id: string) => apiClient.delete(`/tasks/${id}`),
  toggle: (id: string) => apiClient.post(`/tasks/${id}/toggle`),
  runOnce: (id: string) => apiClient.post(`/tasks/${id}/run-once`),
};

// Execution APIs
export const executionApi = {
  getAll: async (params?: { taskId?: string; limit?: number; offset?: number }) => {
    const response = await apiClient.get('/executions', { params });
    return { data: response.data.items || [] };
  },
  getById: (id: string) => apiClient.get(`/executions/${id}`),
  getStats: async () => {
    const response = await apiClient.get('/executions/stats');
    return { data: response.data };
  },
  delete: (id: string) => apiClient.delete(`/executions/${id}`),
  deleteAll: () => apiClient.delete('/executions'),
};

// Exchange APIs
export const exchangeApi = {
  getTradingPairs: (exchange: string, simulated: boolean = true) => 
    apiClient.get(`/exchanges/${exchange}/trading-pairs`, { params: { simulated } }),
};
