const LOCAL_API_BASE_URL = 'http://localhost:8080/api';
const PROD_API_BASE_URL = 'https://dms-backend-xef8.onrender.com/api';

export const resolveApiBaseUrl = (rawApiBaseUrl = import.meta.env.VITE_API_URL) => {
  const candidateBaseUrl = (rawApiBaseUrl || (import.meta.env.PROD ? PROD_API_BASE_URL : LOCAL_API_BASE_URL)).replace(/\/$/, '');

  return candidateBaseUrl.endsWith('/api') ? candidateBaseUrl : `${candidateBaseUrl}/api`;
};
