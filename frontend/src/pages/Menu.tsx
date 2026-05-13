import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { useAuth } from '../context/AuthContext';

interface MenuItem {
  id: string;
  name: string;
  description: string;
  category: string;
  price: number;
  image_url?: string;
  is_available: boolean;
  dietary_preferences: string[];
}

export const Menu: React.FC = () => {
  const [items, setItems] = useState<MenuItem[]>([]);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    loadMenu();
  }, [search, category]);

  const loadMenu = async () => {
    try {
      const params: any = {};
      if (search) params.search = search;
      if (category) params.category = category;
      const data = await api.getMenu(params);
      setItems(data);
      const uniqueCategories = [...new Set(data.map((item: MenuItem) => item.category))];
      setCategories(uniqueCategories);
    } catch (error) {
      console.error('Failed to load menu:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddToCart = async (itemId: string) => {
    if (!isAuthenticated) {
      alert('Please login to add items to cart');
      return;
    }
    try {
      await api.addToCart({ item_id: itemId, quantity: 1 });
      alert('Item added to cart!');
    } catch (error) {
      console.error('Failed to add to cart:', error);
      alert('Failed to add to cart');
    }
  };

  if (loading) return <div className="loading">Loading menu...</div>;

  return (
    <div className="menu-page">
      <div className="menu-header">
        <h1>Our Menu</h1>
        <div className="menu-filters">
          <input
            type="text"
            placeholder="Search menu..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="search-input"
          />
          <select value={category} onChange={(e) => setCategory(e.target.value)} className="category-select">
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="menu-grid">
        {items.map((item) => (
          <div key={item.id} className="menu-item-card">
            {item.image_url && (
              <div className="menu-item-image" style={{ backgroundImage: `url(${item.image_url})` }} />
            )}
            <div className="menu-item-content">
              <h3>{item.name}</h3>
              <p className="description">{item.description}</p>
              <div className="menu-item-footer">
                <span className="price">${item.price.toFixed(2)}</span>
                {item.is_available ? (
                  <button
                    className="btn btn-sm btn-primary"
                    onClick={() => handleAddToCart(item.id)}
                  >
                    Add to Cart
                  </button>
                ) : (
                  <span className="unavailable">Unavailable</span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
