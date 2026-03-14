// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080/api';

console.log('[API] Initialized with base URL:', API_BASE_URL);

// Get auth token from localStorage
const getAuthToken = () => {
  try {
    const user = localStorage.getItem('dms_user');
    if (user) {
      const userData = JSON.parse(user);
      return userData.token;
    }
    return null;
  } catch (error) {
    console.error('[API] Error getting auth token:', error);
    return null;
  }
};

// API request helper
const apiRequest = async (endpoint, options = {}) => {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = getAuthToken();

  console.log('[API] Making request:', {
    method: options.method || 'GET',
    endpoint,
    hasToken: !!token,
    url
  });

  const headers = {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
  };

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    console.log('[API] Response received:', {
      status: response.status,
      statusText: response.statusText,
      ok: response.ok,
      endpoint
    });

    const raw = await response.text();
    let data = null;
    try {
      data = raw ? JSON.parse(raw) : {};
    } catch {
      data = { message: raw || 'API request failed' };
    }

    if (!response.ok) {
      let errorMessage =
        data?.message ||
        data?.detail ||
        (typeof data?.error?.details === 'string' ? data.error.details : null) ||
        'API request failed';

      // FastAPI validation errors are returned as structured details by backend middleware.
      if (
        response.status === 422 &&
        data?.error?.code === 'VALIDATION_ERROR' &&
        Array.isArray(data?.error?.details) &&
        data.error.details.length > 0
      ) {
        const first = data.error.details[0];
        const field = first?.field ? String(first.field).replace('body.', '') : 'field';
        const message = first?.message || 'Invalid value';
        errorMessage = `${field}: ${message}`;
      }

      if (
        response.status === 400 &&
        Array.isArray(data?.error?.details) &&
        data.error.details.length > 0
      ) {
        const first = data.error.details[0];
        errorMessage = first?.message || errorMessage;
      }

      console.error('[API] Request failed:', {
        endpoint,
        status: response.status,
        error: errorMessage,
        data
      });
      throw new Error(errorMessage);
    }

    console.log('[API] Request successful:', endpoint);
    return data;
  } catch (error) {
    console.error('[API] Request error:', {
      endpoint,
      error: error.message,
      stack: error.stack
    });
    throw error;
  }
};

// Auth API
export const authAPI = {
  login: async (email, password) => {
    console.log('[authAPI] Login attempt for:', email);
    try {
      const response = await apiRequest('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      console.log('[authAPI] Login successful');
      return response;
    } catch (error) {
      console.error('[authAPI] Login failed:', error.message);
      throw error;
    }
  },

  logout: async () => {
    console.log('[authAPI] Logging out');
    try {
      const response = await apiRequest('/auth/logout', {
        method: 'POST',
      });
      console.log('[authAPI] Logout successful');
      return response;
    } catch (error) {
      console.error('[authAPI] Logout failed:', error.message);
      throw error;
    }
  },

  getCurrentUser: async () => {
    console.log('[authAPI] Fetching current user');
    try {
      const response = await apiRequest('/auth/me');
      console.log('[authAPI] Current user fetched successfully');
      return response;
    } catch (error) {
      console.error('[authAPI] Failed to fetch current user:', error.message);
      throw error;
    }
  },

  changePassword: async (currentPassword, newPassword) => {
    console.log('[authAPI] Changing password');
    try {
      const response = await apiRequest('/auth/password', {
        method: 'PUT',
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
      console.log('[authAPI] Password changed successfully');
      return response;
    } catch (error) {
      console.error('[authAPI] Failed to change password:', error.message);
      throw error;
    }
  },
};

// Users API
export const usersAPI = {
  getUsers: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const response = await apiRequest(`/users?${queryString}`);
    return response;
  },

  getUser: async (userId) => {
    const response = await apiRequest(`/users/${userId}`);
    return response;
  },

  createUser: async (userData) => {
    const response = await apiRequest('/users', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
    return response;
  },

  updateUser: async (userId, userData) => {
    const response = await apiRequest(`/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(userData),
    });
    return response;
  },

  deleteUser: async (userId) => {
    const response = await apiRequest(`/users/${userId}`, {
      method: 'DELETE',
    });
    return response;
  },

  updateUserStatus: async (userId, status) => {
    const response = await apiRequest(`/users/${userId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
    return response;
  },
};

// Devices API
export const devicesAPI = {
  getDevices: async (params = {}) => {
    console.log('[devicesAPI] Getting devices with params:', params);
    try {
      const queryString = new URLSearchParams(params).toString();
      const response = await apiRequest(`/devices?${queryString}`);
      console.log('[devicesAPI] Successfully fetched', response.data?.length || 0, 'devices');
      return response;
    } catch (error) {
      console.error('[devicesAPI] Failed to get devices:', error.message);
      throw error;
    }
  },

  getDevice: async (deviceId) => {
    const response = await apiRequest(`/devices/${deviceId}`);
    return response;
  },

  getAvailableDevices: async () => {
    const response = await apiRequest('/devices/available');
    return response;
  },

  getMyOverview: async () => {
    const response = await apiRequest('/devices/my-overview');
    return response;
  },

  trackDeviceBySerial: async (serialNumber) => {
    console.log('[devicesAPI] Tracking device by serial:', serialNumber);
    try {
      const response = await apiRequest(`/devices/track/${serialNumber}`);
      console.log('[devicesAPI] Device tracking data retrieved');
      return response;
    } catch (error) {
      console.error('[devicesAPI] Failed to track device:', error.message);
      throw error;
    }
  },

  getDeviceHistory: async (deviceId) => {
    const response = await apiRequest(`/devices/${deviceId}/history`);
    return response;
  },

  createDevice: async (deviceData) => {
    console.log('[devicesAPI] Creating device:', deviceData);
    try {
      const response = await apiRequest('/devices', {
        method: 'POST',
        body: JSON.stringify(deviceData),
      });
      console.log('[devicesAPI] Device created successfully:', response.data);
      return response;
    } catch (error) {
      console.error('[devicesAPI] Failed to create device:', error.message);
      throw error;
    }
  },

  updateDevice: async (deviceId, deviceData) => {
    const response = await apiRequest(`/devices/${deviceId}`, {
      method: 'PUT',
      body: JSON.stringify(deviceData),
    });
    return response;
  },

  deleteDevice: async (deviceId) => {
    const response = await apiRequest(`/devices/${deviceId}`, {
      method: 'DELETE',
    });
    return response;
  },

  updateDeviceStatus: async (deviceId, status, notes) => {
    const response = await apiRequest(`/devices/${deviceId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status, notes }),
    });
    return response;
  },

  repairDeviceHolder: async (deviceId) => {
    const response = await apiRequest(`/devices/${deviceId}/repair-holder`, {
      method: 'POST',
    });
    return response;
  },

  bulkUpload: async (file) => {
    const token = getAuthToken();
    const formData = new FormData();
    formData.append('file', file);
    const url = `${API_BASE_URL}/devices/bulk-upload`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { ...(token && { Authorization: `Bearer ${token}` }) },
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || data.detail || 'Upload failed');
    return data;
  },

  getDevicesForReplacement: async (excludeDeviceId = null) => {
    const params = excludeDeviceId ? `?exclude_device_id=${excludeDeviceId}` : '';
    const response = await apiRequest(`/devices/for-replacement${params}`);
    return response;
  },

  requestDeviceEdit: async (deviceId, changes) => {
    const response = await apiRequest(`/devices/${deviceId}/request-edit`, {
      method: 'POST',
      body: JSON.stringify(changes),
    });
    return response;
  },
};

// Distributions API
export const distributionsAPI = {
  getDistributions: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const response = await apiRequest(`/distributions?${queryString}`);
    return response;
  },

  getDistribution: async (distributionId) => {
    const response = await apiRequest(`/distributions/${distributionId}`);
    return response;
  },

  getPendingDistributions: async () => {
    const response = await apiRequest('/distributions/pending');
    return response;
  },

  createDistribution: async (distributionData) => {
    const response = await apiRequest('/distributions', {
      method: 'POST',
      body: JSON.stringify(distributionData),
    });
    return response;
  },

  updateDistributionStatus: async (distributionId, status, notes) => {
    const response = await apiRequest(`/distributions/${distributionId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status, notes }),
    });
    return response;
  },

  cancelDistribution: async (distributionId) => {
    const response = await apiRequest(`/distributions/${distributionId}`, {
      method: 'DELETE',
    });
    return response;
  },

  confirmReceipt: async (distributionId, received, notes = '') => {
    const response = await apiRequest(`/distributions/${distributionId}/receipt`, {
      method: 'POST',
      body: JSON.stringify({ received, notes }),
    });
    return response;
  },
};

// Defects API
export const defectsAPI = {
  getDefects: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const response = await apiRequest(`/defects?${queryString}`);
    return response;
  },

  getDefect: async (defectId) => {
    const response = await apiRequest(`/defects/${defectId}`);
    return response;
  },

  createDefect: async (defectData) => {
    const response = await apiRequest('/defects', {
      method: 'POST',
      body: JSON.stringify(defectData),
    });
    return response;
  },

  updateDefect: async (defectId, defectData) => {
    const response = await apiRequest(`/defects/${defectId}`, {
      method: 'PUT',
      body: JSON.stringify(defectData),
    });
    return response;
  },

  updateDefectStatus: async (defectId, status, notes) => {
    const response = await apiRequest(`/defects/${defectId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status, notes }),
    });
    return response;
  },

  resolveDefect: async (defectId, resolution) => {
    const response = await apiRequest(`/defects/${defectId}/resolve`, {
      method: 'PATCH',
      body: JSON.stringify({ resolution }),
    });
    return response;
  },

  replaceDevice: async (defectId, replaceData) => {
    const response = await apiRequest(`/defects/${defectId}/replace`, {
      method: 'POST',
      body: JSON.stringify(replaceData),
    });
    return response;
  },

  enquireReplacement: async (defectId, message) => {
    const response = await apiRequest(`/defects/${defectId}/enquire`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
    return response;
  },

  resendReplacementConfirmation: async (defectId) => {
    const response = await apiRequest(`/defects/${defectId}/resend-confirmation`, {
      method: 'POST',
    });
    return response;
  },

  markReplacementWaiting: async (defectId, notes = '') => {
    const response = await apiRequest(`/defects/${defectId}/mark-waiting`, {
      method: 'POST',
      body: JSON.stringify({ notes }),
    });
    return response;
  },

  getReplacements: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const response = await apiRequest(`/defects/replacements?${queryString}`);
    return response;
  },

  confirmReplacementReceipt: async (defectId, notes = '') => {
    const response = await apiRequest(`/defects/${defectId}/replacement/confirm`, {
      method: 'POST',
      body: JSON.stringify({ notes }),
    });
    return response;
  },

  deleteDefect: async (defectId) => {
    const response = await apiRequest(`/defects/${defectId}`, {
      method: 'DELETE',
    });
    return response;
  },
};

// Returns API
export const returnsAPI = {
  getReturns: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const response = await apiRequest(`/returns?${queryString}`);
    return response;
  },

  getReturn: async (returnId) => {
    const response = await apiRequest(`/returns/${returnId}`);
    return response;
  },

  createReturn: async (returnData) => {
    const response = await apiRequest('/returns', {
      method: 'POST',
      body: JSON.stringify(returnData),
    });
    return response;
  },

  updateReturnStatus: async (returnId, status, notes) => {
    const response = await apiRequest(`/returns/${returnId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status, notes }),
    });
    return response;
  },

  cancelReturn: async (returnId) => {
    const response = await apiRequest(`/returns/${returnId}`, {
      method: 'DELETE',
    });
    return response;
  },
};

// Approvals API
export const approvalsAPI = {
  getApprovals: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const response = await apiRequest(`/approvals?${queryString}`);
    return response;
  },

  getApproval: async (approvalId) => {
    const response = await apiRequest(`/approvals/${approvalId}`);
    return response;
  },

  approveRequest: async (approvalId, notes) => {
    const response = await apiRequest(`/approvals/${approvalId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ notes }),
    });
    return response;
  },

  rejectRequest: async (approvalId, rejectionReason, notes) => {
    const response = await apiRequest(`/approvals/${approvalId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ rejection_reason: rejectionReason, notes }),
    });
    return response;
  },
};

// Operators API
export const operatorsAPI = {
  getOperators: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const response = await apiRequest(`/operators?${queryString}`);
    return response;
  },

  getOperator: async (operatorId) => {
    const response = await apiRequest(`/operators/${operatorId}`);
    return response;
  },

  getOperatorDevices: async (operatorId) => {
    const response = await apiRequest(`/operators/${operatorId}/devices`);
    return response;
  },

  createOperator: async (operatorData) => {
    const response = await apiRequest('/operators', {
      method: 'POST',
      body: JSON.stringify(operatorData),
    });
    return response;
  },

  updateOperator: async (operatorId, operatorData) => {
    const response = await apiRequest(`/operators/${operatorId}`, {
      method: 'PUT',
      body: JSON.stringify(operatorData),
    });
    return response;
  },

  deleteOperator: async (operatorId) => {
    const response = await apiRequest(`/operators/${operatorId}`, {
      method: 'DELETE',
    });
    return response;
  },
};

// Notifications API
export const notificationsAPI = {
  getNotifications: async (params = {}) => {
    console.log('[notificationsAPI] Getting notifications with params:', params);
    try {
      const queryString = new URLSearchParams(params).toString();
      const response = await apiRequest(`/notifications?${queryString}`);
      console.log('[notificationsAPI] Successfully fetched notifications');
      return response;
    } catch (error) {
      console.error('[notificationsAPI] Failed to get notifications:', error.message);
      throw error;
    }
  },

  getUnreadCount: async () => {
    console.log('[notificationsAPI] Getting unread count');
    try {
      const response = await apiRequest('/notifications/unread');
      console.log('[notificationsAPI] Unread count:', response.data?.count ?? 0);
      return response;
    } catch (error) {
      console.error('[notificationsAPI] Failed to get unread count:', error.message);
      throw error;
    }
  },

  getLatestNotifications: async (limit = 5) => {
    console.log('[notificationsAPI] Getting latest notifications, limit:', limit);
    try {
      const response = await apiRequest(`/notifications/latest?limit=${limit}`);
      console.log('[notificationsAPI] Successfully fetched', response.data?.length || 0, 'notifications');
      return response;
    } catch (error) {
      console.error('[notificationsAPI] Failed to get latest notifications:', error.message);
      throw error;
    }
  },

  markAsRead: async (notificationId) => {
    console.log('[notificationsAPI] Marking notification as read:', notificationId);
    try {
      const response = await apiRequest(`/notifications/${notificationId}/read`, {
        method: 'PATCH',
      });
      console.log('[notificationsAPI] Notification marked as read');
      return response;
    } catch (error) {
      console.error('[notificationsAPI] Failed to mark notification as read:', error.message);
      throw error;
    }
  },

  markAllAsRead: async () => {
    console.log('[notificationsAPI] Marking all notifications as read');
    try {
      const response = await apiRequest('/notifications/read-all', {
        method: 'PATCH',
      });
      console.log('[notificationsAPI] All notifications marked as read');
      return response;
    } catch (error) {
      console.error('[notificationsAPI] Failed to mark all notifications as read:', error.message);
      throw error;
    }
  },

  deleteNotification: async (notificationId) => {
    console.log('[notificationsAPI] Deleting notification:', notificationId);
    try {
      const response = await apiRequest(`/notifications/${notificationId}`, {
        method: 'DELETE',
      });
      console.log('[notificationsAPI] Notification deleted');
      return response;
    } catch (error) {
      console.error('[notificationsAPI] Failed to delete notification:', error.message);
      throw error;
    }
  },
};

// External Inventory API
export const externalInventoryAPI = {
  getDashboard: async () => {
    const response = await apiRequest('/external-inventory/dashboard');
    return response;
  },

  getItems: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const response = await apiRequest(`/external-inventory/items?${queryString}`);
    return response;
  },

  createItem: async (payload) => {
    const response = await apiRequest('/external-inventory/items', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return response;
  },

  updateItem: async (inventoryId, payload) => {
    const response = await apiRequest(`/external-inventory/items/${inventoryId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
    return response;
  },

  createAdjustment: async (payload) => {
    const response = await apiRequest('/external-inventory/adjustments', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return response;
  },

  getPurchaseOrders: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const response = await apiRequest(`/external-inventory/purchase-orders?${queryString}`);
    return response;
  },

  createPurchaseOrder: async (payload) => {
    const response = await apiRequest('/external-inventory/purchase-orders', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return response;
  },

  receivePurchaseOrder: async (poId, payload) => {
    const response = await apiRequest(`/external-inventory/purchase-orders/${poId}/receive`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return response;
  },

  getReceipts: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const response = await apiRequest(`/external-inventory/receipts?${queryString}`);
    return response;
  },

  getMovements: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const response = await apiRequest(`/external-inventory/movements?${queryString}`);
    return response;
  },
};

// Reports API
export const reportsAPI = {
  getInventoryReport: async () => {
    const response = await apiRequest('/reports/inventory');
    return response;
  },

  getDistributionSummary: async () => {
    const response = await apiRequest('/reports/distribution-summary');
    return response;
  },

  getDefectSummary: async () => {
    const response = await apiRequest('/reports/defect-summary');
    return response;
  },

  getReturnSummary: async () => {
    const response = await apiRequest('/reports/return-summary');
    return response;
  },

  getUserActivityReport: async () => {
    const response = await apiRequest('/reports/user-activity');
    return response;
  },

  getDeviceUtilizationReport: async () => {
    const response = await apiRequest('/reports/device-utilization');
    return response;
  },
};

// Dashboard API
export const dashboardAPI = {
  getStats: async () => {
    const response = await apiRequest('/dashboard/stats');
    return response;
  },

  getAdvancedMetrics: async () => {
    const response = await apiRequest('/dashboard/advanced-metrics');
    return response;
  },

  getRecentActivities: async (limit = 10) => {
    const response = await apiRequest(`/dashboard/recent-activities?limit=${limit}`);
    return response;
  },

  getDistributionChartData: async () => {
    const response = await apiRequest('/dashboard/charts/distributions');
    return response;
  },

  getDefectChartData: async () => {
    const response = await apiRequest('/dashboard/charts/defects');
    return response;
  },

  getSystemAlerts: async () => {
    const response = await apiRequest('/dashboard/alerts');
    return response;
  },
};

// Change Requests API
export const changeRequestsAPI = {
  submit: (data) => apiRequest('/change-requests', { method: 'POST', body: JSON.stringify(data) }),
  requestReplacementTransferFix: (defectId, notes = '') =>
    apiRequest('/change-requests', {
      method: 'POST',
      body: JSON.stringify({
        request_type: 'replacement_transfer_fix',
        device_id: String(defectId),
        reason: notes || undefined,
      }),
    }),
  getRequests: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return apiRequest(`/change-requests?${qs}`);
  },
  review: (requestId, data) => apiRequest(`/change-requests/${requestId}/review`, { method: 'PATCH', body: JSON.stringify(data) }),
};

// Admin user credentials update
export const adminUpdateCredentials = (userId, data) =>
  apiRequest(`/users/${userId}/credentials`, { method: 'PATCH', body: JSON.stringify(data) });

export default {
  auth: authAPI,
  users: usersAPI,
  devices: devicesAPI,
  distributions: distributionsAPI,
  defects: defectsAPI,
  returns: returnsAPI,
  approvals: approvalsAPI,
  operators: operatorsAPI,
  notifications: notificationsAPI,
  externalInventory: externalInventoryAPI,
  reports: reportsAPI,
  dashboard: dashboardAPI,
};
