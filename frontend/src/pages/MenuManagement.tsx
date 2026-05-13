import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { useAuth } from '../context/AuthContext';

export const MenuManagement: React.FC = () => {
  const [items, setItems] = useState<any[]>([]);
  const [venues, setVenues] = useState<any[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editingItem, setEditingItem] = useState<any>(null);
  const [formData, setFormData] = useState({
    venue_id: '',
    name: '',
    description: '',
    category: '',
    price: 0,
    image_url: '',
    is_available: true,
  });
  const { isStaff } = useAuth();

  useEffect(() => {
    if (isStaff) {
      loadData();
    }
  }, [isStaff]);

  const loadData = async () => {
    try {
      const [menuData, venuesData] = await Promise.all([
        api.getMenu(),
        api.getVenues(),
      ]);
      setItems(menuData);
      setVenues(venuesData);
      if (venuesData.length > 0) {
        setFormData((prev) => ({ ...prev, venue_id: venuesData[0].id }));
      }
    } catch (error) {
      console.error('Failed to load data:', error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingItem) {
        await api.updateMenuItem(editingItem.id, formData);
      } else {
        await api.createMenuItem(formData);
      }
      setShowForm(false);
      setEditingItem(null);
      resetForm();
      loadData();
    } catch (error) {
      console.error('Failed to save menu item:', error);
      alert('Failed to save menu item');
    }
  };

  const handleEdit = (item: any) => {
    setEditingItem(item);
    setFormData({
      venue_id: item.venue_id,
      name: item.name,
      description: item.description || '',
      category: item.category,
      price: item.price,
      image_url: item.image_url || '',
      is_available: item.is_available,
    });
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this item?')) return;
    try {
      await api.deleteMenuItem(id);
      loadData();
    } catch (error) {
      console.error('Failed to delete item:', error);
      alert('Failed to delete item');
    }
  };

  const resetForm = () => {
    setFormData({
      venue_id: venues.length > 0 ? venues[0].id : '',
      name: '',
      description: '',
      category: '',
      price: 0,
      image_url: '',
      is_available: true,
    });
  };

  if (!isStaff) {
    return <div className="error-message">Access denied. Admin/Staff only.</div>;
  }

  return (
    <div className="menu-management">
      <div className="management-header">
        <h1>Menu Management</h1>
        <button
          className="btn btn-primary"
          onClick={() => {
            resetForm();
            setEditingItem(null);
            setShowForm(true);
          }}
        >
          Add New Item
        </button>
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>{editingItem ? 'Edit' : 'Add'} Menu Item</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Venue</label>
                <select
                  value={formData.venue_id}
                  onChange={(e) => setFormData({ ...formData, venue_id: e.target.value })}
                  required
                >
                  {venues.map((venue) => (
                    <option key={venue.id} value={venue.id}>{venue.name}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Category</label>
                <input
                  type="text"
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Price</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.price}
                  onChange={(e) => setFormData({ ...formData, price: parseFloat(e.target.value) })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Image URL</label>
                <input
                  type="text"
                  value={formData.image_url}
                  onChange={(e) => setFormData({ ...formData, image_url: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={formData.is_available}
                    onChange={(e) => setFormData({ ...formData, is_available: e.target.checked })}
                  />
                  Available
                </label>
              </div>
              <div className="form-actions">
                <button type="submit" className="btn btn-primary">Save</button>
                <button type="button" className="btn" onClick={() => setShowForm(false)}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="items-table">
        {items.map((item) => (
          <div key={item.id} className="item-row">
            <div className="item-info">
              <strong>{item.name}</strong>
              <span>{item.category}</span>
              <span>${item.price.toFixed(2)}</span>
              <span className={item.is_available ? 'available' : 'unavailable'}>
                {item.is_available ? 'Available' : 'Unavailable'}
              </span>
            </div>
            <div className="item-actions">
              <button className="btn btn-sm" onClick={() => handleEdit(item)}>Edit</button>
              <button className="btn btn-sm btn-danger" onClick={() => handleDelete(item.id)}>Delete</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
