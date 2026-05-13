import React, { useState, useEffect } from 'react';
import { api } from '../api';

interface Order {
  id: string;
  items: any[];
  total_amount: number;
  order_status: string;
  payment_status: string;
  created_at: string;
  order_mode: string;
}

export const Orders: React.FC = () => {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadOrders();
  }, []);

  const loadOrders = async () => {
    try {
      const data = await api.getOrders();
      setOrders(data);
    } catch (error) {
      console.error('Failed to load orders:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleReorder = async (orderId: string) => {
    try {
      await api.reorder(orderId);
      alert('Items added to cart!');
    } catch (error) {
      console.error('Failed to reorder:', error);
      alert('Failed to reorder');
    }
  };

  const handleDownloadInvoice = async (orderId: string) => {
    try {
      const blob = await api.getInvoice(orderId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `invoice_${orderId}.pdf`;
      a.click();
    } catch (error) {
      console.error('Failed to download invoice:', error);
      alert('Failed to download invoice');
    }
  };

  if (loading) return <div className="loading">Loading orders...</div>;

  return (
    <div className="orders-page">
      <h1>My Orders</h1>
      {orders.length === 0 ? (
        <p>No orders yet</p>
      ) : (
        <div className="orders-list">
          {orders.map((order) => (
            <div key={order.id} className="order-card">
              <div className="order-header">
                <h3>Order #{order.id.slice(-6)}</h3>
                <span className={`status-badge status-${order.order_status}`}>
                  {order.order_status}
                </span>
              </div>
              <div className="order-details">
                <p><strong>Mode:</strong> {order.order_mode}</p>
                <p><strong>Total:</strong> ${order.total_amount.toFixed(2)}</p>
                <p><strong>Payment:</strong> {order.payment_status}</p>
                <p><strong>Date:</strong> {new Date(order.created_at).toLocaleDateString()}</p>
              </div>
              <div className="order-items">
                <h4>Items:</h4>
                {order.items.map((item, idx) => (
                  <div key={idx} className="order-item">
                    {item.item_name} x{item.quantity}
                  </div>
                ))}
              </div>
              <div className="order-actions">
                <button className="btn btn-sm" onClick={() => handleReorder(order.id)}>
                  Reorder
                </button>
                {order.payment_status === 'completed' && (
                  <button className="btn btn-sm" onClick={() => handleDownloadInvoice(order.id)}>
                    Download Invoice
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
