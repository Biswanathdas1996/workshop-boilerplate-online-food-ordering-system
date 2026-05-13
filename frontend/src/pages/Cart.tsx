import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';

interface CartItem {
  item_id: string;
  item_name: string;
  quantity: number;
  price: number;
}

interface Cart {
  items: CartItem[];
}

export const Cart: React.FC = () => {
  const [cart, setCart] = useState<Cart>({ items: [] });
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadCart();
  }, []);

  const loadCart = async () => {
    try {
      const data = await api.getCart();
      setCart(data);
    } catch (error) {
      console.error('Failed to load cart:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateQuantity = async (itemId: string, newQuantity: number) => {
    try {
      await api.updateCartItem(itemId, newQuantity);
      loadCart();
    } catch (error) {
      console.error('Failed to update quantity:', error);
    }
  };

  const handleRemove = async (itemId: string) => {
    try {
      await api.removeFromCart(itemId);
      loadCart();
    } catch (error) {
      console.error('Failed to remove item:', error);
    }
  };

  const total = cart.items.reduce((sum, item) => sum + item.price * item.quantity, 0);

  if (loading) return <div className="loading">Loading cart...</div>;

  return (
    <div className="cart-page">
      <h1>Shopping Cart</h1>
      {cart.items.length === 0 ? (
        <div className="empty-cart">
          <p>Your cart is empty</p>
          <button className="btn btn-primary" onClick={() => navigate('/menu')}>
            Browse Menu
          </button>
        </div>
      ) : (
        <>
          <div className="cart-items">
            {cart.items.map((item) => (
              <div key={item.item_id} className="cart-item">
                <div className="cart-item-info">
                  <h3>{item.item_name}</h3>
                  <p className="price">${item.price.toFixed(2)}</p>
                </div>
                <div className="cart-item-actions">
                  <div className="quantity-control">
                    <button onClick={() => handleUpdateQuantity(item.item_id, item.quantity - 1)}>-</button>
                    <span>{item.quantity}</span>
                    <button onClick={() => handleUpdateQuantity(item.item_id, item.quantity + 1)}>+</button>
                  </div>
                  <button className="btn-remove" onClick={() => handleRemove(item.item_id)}>Remove</button>
                </div>
              </div>
            ))}
          </div>
          <div className="cart-summary">
            <h2>Total: ${total.toFixed(2)}</h2>
            <button className="btn btn-primary btn-lg" onClick={() => navigate('/checkout')}>
              Proceed to Checkout
            </button>
          </div>
        </>
      )}
    </div>
  );
};
