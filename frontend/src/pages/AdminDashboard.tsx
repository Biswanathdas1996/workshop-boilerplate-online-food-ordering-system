import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { useAuth } from '../context/AuthContext';

interface Stats {
  total_orders_today: number;
  total_revenue_today: number;
  active_orders: number;
  total_menu_items: number;
  pending_orders: number;
  completed_orders_today: number;
}

export const AdminDashboard: React.FC = () => {
  const [stats, setStats] = useState<Stats | null>(null);
  const [orders, setOrders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const { isStaff } = useAuth();

  useEffect(() => {
    if (isStaff) {
      loadDashboard();
    }
  }, [isStaff]);

  const loadDashboard = async () => {
    try {
      const [statsData, ordersData] = await Promise.all([
        api.getDashboardStats(),
        api.getOrders(),
      ]);
      setStats(statsData);
      setOrders(ordersData);
    } catch (error) {
      console.error('Failed to load dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateOrderStatus = async (orderId: string, newStatus: string) => {
    try {
      await api.updateOrderStatus(orderId, newStatus);
      loadDashboard();
    } catch (error) {
      console.error('Failed to update order status:', error);
      alert('Failed to update order status');
    }
  };

  if (!isStaff) {
    return <div className="error-message">Access denied. Admin/Staff only.</div>;
  }

  if (loading) return <div className="loading">Loading dashboard...</div>;

  return (
    <div className="admin-dashboard">
      <h1>Admin Dashboard</h1>

      <div className="stats-grid">
        <div className="stat-card">
          <h3>Orders Today</h3>
          <p className="stat-value">{stats?.total_orders_today || 0}</p>
        </div>
        <div className="stat-card">
          <h3>Revenue Today</h3>
          <p className="stat-value">${(stats?.total_revenue_today || 0).toFixed(2)}</p>
        </div>
        <div className="stat-card">
          <h3>Active Orders</h3>
          <p className="stat-value">{stats?.active_orders || 0}</p>
        </div>
        <div className="stat-card">
          <h3>Menu Items</h3>
          <p className="stat-value">{stats?.total_menu_items || 0}</p>
        </div>
      </div>

      <div className="orders-management">
        <h2>Recent Orders</h2>
        <div className="orders-table">
          {orders.slice(0, 10).map((order) => (
            <div key={order.id} className="order-row">
              <div className="order-info">
                <strong>#{order.id.slice(-6)}</strong>
                <span>${order.total_amount.toFixed(2)}</span>
                <span>{new Date(order.created_at).toLocaleString()}</span>
              </div>
              <div className="order-status-control">
                <select
                  value={order.order_status}
                  onChange={(e) => handleUpdateOrderStatus(order.id, e.target.value)}
                  className="status-select"
                >
                  <option value="received">Received</option>
                  <option value="preparing">Preparing</option>
                  <option value="ready">Ready</option>
                  <option value="out_for_delivery">Out for Delivery</option>
                  <option value="completed">Completed</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
