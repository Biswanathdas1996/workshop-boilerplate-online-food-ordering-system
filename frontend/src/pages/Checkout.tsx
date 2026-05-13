import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';

export const Checkout: React.FC = () => {
  const [orderMode, setOrderMode] = useState('delivery');
  const [address, setAddress] = useState('');
  const [city, setCity] = useState('');
  const [postalCode, setPostalCode] = useState('');
  const [phone, setPhone] = useState('');
  const [venues, setVenues] = useState<any[]>([]);
  const [selectedVenue, setSelectedVenue] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    loadVenues();
  }, []);

  const loadVenues = async () => {
    try {
      const data = await api.getVenues();
      setVenues(data);
      if (data.length > 0) setSelectedVenue(data[0].id);
    } catch (error) {
      console.error('Failed to load venues:', error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const orderData: any = {
        venue_id: selectedVenue,
        order_mode: orderMode,
      };

      if (orderMode === 'delivery') {
        orderData.delivery_details = {
          address,
          city,
          postal_code: postalCode,
          phone,
        };
      }

      const order = await api.createOrder(orderData);

      // Mock payment
      const paymentIntent = await api.createPaymentIntent({
        order_id: order.id,
        amount: order.total_amount,
      });

      await api.confirmPayment({
        payment_id: paymentIntent.payment_intent_id,
        status: 'completed',
      });

      alert('Order placed successfully!');
      navigate('/orders');
    } catch (error: any) {
      console.error('Checkout failed:', error);
      alert(error.message || 'Checkout failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="checkout-page">
      <h1>Checkout</h1>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Select Venue</label>
          <select value={selectedVenue} onChange={(e) => setSelectedVenue(e.target.value)} required>
            {venues.map((venue) => (
              <option key={venue.id} value={venue.id}>{venue.name}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label>Order Mode</label>
          <select value={orderMode} onChange={(e) => setOrderMode(e.target.value)}>
            <option value="delivery">Delivery</option>
            <option value="pickup">Pickup</option>
            <option value="dine_in">Dine In</option>
          </select>
        </div>

        {orderMode === 'delivery' && (
          <>
            <div className="form-group">
              <label>Address</label>
              <input
                type="text"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label>City</label>
              <input
                type="text"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label>Postal Code</label>
              <input
                type="text"
                value={postalCode}
                onChange={(e) => setPostalCode(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label>Phone</label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                required
              />
            </div>
          </>
        )}

        <button type="submit" className="btn btn-primary btn-lg" disabled={loading}>
          {loading ? 'Processing...' : 'Place Order'}
        </button>
      </form>
    </div>
  );
};
