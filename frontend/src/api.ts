const API_BASE = '/api';

interface RequestOptions extends RequestInit {
  body?: any;
}

async function request(endpoint: string, options: RequestOptions = {}) {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const config: RequestInit = {
    ...options,
    headers,
  };

  if (options.body && typeof options.body !== 'string') {
    config.body = JSON.stringify(options.body);
  }

  const response = await fetch(`${API_BASE}${endpoint}`, config);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || 'Request failed');
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export const api = {
  // Auth
  register: (data: any) => request('/auth/register', { method: 'POST', body: data }),
  login: (data: any) => request('/auth/login', { method: 'POST', body: data }),
  getMe: () => request('/auth/me'),

  // Menu
  getMenu: (params?: any) => {
    const query = params ? '?' + new URLSearchParams(params).toString() : '';
    return request(`/menu${query}`);
  },
  getMenuItem: (id: string) => request(`/menu/${id}`),
  createMenuItem: (data: any) => request('/menu', { method: 'POST', body: data }),
  updateMenuItem: (id: string, data: any) => request(`/menu/${id}`, { method: 'PUT', body: data }),
  deleteMenuItem: (id: string) => request(`/menu/${id}`, { method: 'DELETE' }),

  // Cart
  getCart: () => request('/cart'),
  addToCart: (data: any) => request('/cart/items', { method: 'POST', body: data }),
  updateCartItem: (itemId: string, quantity: number) =>
    request(`/cart/items/${itemId}?quantity=${quantity}`, { method: 'PUT' }),
  removeFromCart: (itemId: string) => request(`/cart/items/${itemId}`, { method: 'DELETE' }),
  clearCart: () => request('/cart', { method: 'DELETE' }),

  // Orders
  createOrder: (data: any) => request('/orders', { method: 'POST', body: data }),
  getOrders: (params?: any) => {
    const query = params ? '?' + new URLSearchParams(params).toString() : '';
    return request(`/orders${query}`);
  },
  getOrder: (id: string) => request(`/orders/${id}`),
  updateOrderStatus: (id: string, status: string) =>
    request(`/orders/${id}/status`, { method: 'PUT', body: { order_status: status } }),
  reorder: (id: string) => request(`/orders/${id}/reorder`, { method: 'POST' }),

  // Payment
  createPaymentIntent: (data: any) => request('/payments/intent', { method: 'POST', body: data }),
  confirmPayment: (data: any) => request('/payments/confirm', { method: 'POST', body: data }),

  // Invoice
  getInvoice: (orderId: string) => fetch(`${API_BASE}/invoices/${orderId}`, {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
  }).then(r => r.blob()),

  // Notifications
  getNotifications: () => request('/notifications'),
  markNotificationRead: (id: string) => request(`/notifications/${id}/read`, { method: 'PUT' }),

  // Venues
  getVenues: () => request('/venues'),
  createVenue: (data: any) => request('/venues', { method: 'POST', body: data }),

  // Admin
  getDashboardStats: () => request('/admin/dashboard'),

  // Restaurant Profile
  getRestaurantProfile: (venueId: string) => request(`/restaurant/profile/${venueId}`),
  updateRestaurantProfile: (venueId: string, data: any) =>
    request(`/restaurant/profile/${venueId}`, { method: 'PUT', body: data }),
};
