import { BrowserRouter, Routes, Route, Link, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { CartProvider, useCart } from './contexts/CartContext'
import { useState, useEffect } from 'react'

// ===================== AUTH COMPONENTS =====================
function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const { login } = useAuth()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    try {
      await login(email, password)
      window.location.href = '/menu'
    } catch (err) {
      setError('Invalid email or password')
    }
  }

  return (
    <div className="page">
      <div className="auth-container">
        <h1>Login</h1>
        {error && <div className="error-message">{error}</div>}
        <form onSubmit={handleSubmit} className="auth-form">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button type="submit" className="btn-primary">Login</button>
        </form>
        <p>Don't have an account? <Link to="/register">Register</Link></p>
      </div>
    </div>
  )
}

function RegisterPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [phone, setPhone] = useState('')
  const [error, setError] = useState('')
  const { register } = useAuth()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    try {
      await register(email, password, fullName, phone || undefined)
      window.location.href = '/menu'
    } catch (err) {
      setError('Registration failed. Email may already be in use.')
    }
  }

  return (
    <div className="page">
      <div className="auth-container">
        <h1>Register</h1>
        {error && <div className="error-message">{error}</div>}
        <form onSubmit={handleSubmit} className="auth-form">
          <input
            type="text"
            placeholder="Full Name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
          />
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            type="tel"
            placeholder="Phone (optional)"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button type="submit" className="btn-primary">Register</button>
        </form>
        <p>Already have an account? <Link to="/login">Login</Link></p>
      </div>
    </div>
  )
}

// ===================== MENU COMPONENTS =====================
interface MenuItem {
  _id: string
  name: string
  description: string
  price: number
  image_url?: string
  is_available: boolean
  category_id: string
  dietary_preferences: string[]
  add_ons: { name: string; price: number }[]
  spice_levels_available: string[]
}

interface Category {
  _id: string
  name: string
  description?: string
}

function MenuPage() {
  const [categories, setCategories] = useState<Category[]>([])
  const [menuItems, setMenuItems] = useState<MenuItem[]>([])
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [selectedVenue, setSelectedVenue] = useState('676f9e0a0b5c8d001f123456') // Default venue
  const [selectedItem, setSelectedItem] = useState<MenuItem | null>(null)
  const { token } = useAuth()
  const { addToCart } = useCart()

  useEffect(() => {
    fetchCategories()
    fetchMenuItems()
  }, [selectedVenue, selectedCategory, search])

  const fetchCategories = async () => {
    try {
      const response = await fetch(`/api/categories?venue_id=${selectedVenue}`)
      if (response.ok) {
        const data = await response.json()
        setCategories(data)
      }
    } catch (error) {
      console.error('Failed to fetch categories:', error)
    }
  }

  const fetchMenuItems = async () => {
    try {
      let url = `/api/menu-items?venue_id=${selectedVenue}`
      if (selectedCategory) url += `&category_id=${selectedCategory}`
      if (search) url += `&search=${encodeURIComponent(search)}`

      const response = await fetch(url)
      if (response.ok) {
        const data = await response.json()
        setMenuItems(data)
      }
    } catch (error) {
      console.error('Failed to fetch menu items:', error)
    }
  }

  const handleAddToCart = async (item: MenuItem) => {
    if (!token) {
      alert('Please login to add items to cart')
      window.location.href = '/login'
      return
    }

    try {
      await addToCart({
        menu_item_id: item._id,
        menu_item_name: item.name,
        menu_item_price: item.price,
        menu_item_image: item.image_url,
        quantity: 1
      })
      alert('Item added to cart!')
    } catch (error) {
      console.error('Failed to add to cart:', error)
      alert('Failed to add item to cart')
    }
  }

  const openItemDetails = (item: MenuItem) => {
    setSelectedItem(item)
  }

  return (
    <div className="page">
      <div className="menu-header">
        <h1>Our Menu</h1>
        <div className="search-bar">
          <input
            type="text"
            placeholder="Search menu items..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <div className="categories-nav">
        <button
          className={!selectedCategory ? 'active' : ''}
          onClick={() => setSelectedCategory(null)}
        >
          All
        </button>
        {categories.map(cat => (
          <button
            key={cat._id}
            className={selectedCategory === cat._id ? 'active' : ''}
            onClick={() => setSelectedCategory(cat._id)}
          >
            {cat.name}
          </button>
        ))}
      </div>

      <div className="menu-grid">
        {menuItems.map(item => (
          <div key={item._id} className="menu-item-card">
            {item.image_url && (
              <img src={item.image_url} alt={item.name} className="menu-item-image" />
            )}
            <div className="menu-item-content">
              <h3>{item.name}</h3>
              <p className="description">{item.description}</p>
              <p className="price">${item.price.toFixed(2)}</p>
              {item.dietary_preferences.length > 0 && (
                <div className="dietary-tags">
                  {item.dietary_preferences.map(pref => (
                    <span key={pref} className="tag">{pref}</span>
                  ))}
                </div>
              )}
              <div className="item-actions">
                <button className="btn-secondary" onClick={() => openItemDetails(item)}>
                  View Details
                </button>
                <button
                  className="btn-primary"
                  onClick={() => handleAddToCart(item)}
                  disabled={!item.is_available}
                >
                  {item.is_available ? 'Add to Cart' : 'Unavailable'}
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {selectedItem && (
        <ItemDetailsModal
          item={selectedItem}
          onClose={() => setSelectedItem(null)}
          onAddToCart={handleAddToCart}
        />
      )}
    </div>
  )
}

function ItemDetailsModal({ item, onClose, onAddToCart }: {
  item: MenuItem
  onClose: () => void
  onAddToCart: (item: MenuItem) => void
}) {
  const [selectedAddOns, setSelectedAddOns] = useState<string[]>([])
  const [spiceLevel, setSpiceLevel] = useState('')
  const [specialInstructions, setSpecialInstructions] = useState('')
  const [quantity, setQuantity] = useState(1)

  const handleAddToCart = () => {
    // For simplicity, using the basic add to cart
    onAddToCart(item)
    onClose()
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>&times;</button>
        <h2>{item.name}</h2>
        {item.image_url && <img src={item.image_url} alt={item.name} className="modal-image" />}
        <p className="description">{item.description}</p>
        <p className="price">${item.price.toFixed(2)}</p>

        {item.add_ons.length > 0 && (
          <div className="customization-section">
            <h3>Add-ons</h3>
            {item.add_ons.map((addon, idx) => (
              <label key={idx} className="checkbox-label">
                <input
                  type="checkbox"
                  checked={selectedAddOns.includes(addon.name)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedAddOns([...selectedAddOns, addon.name])
                    } else {
                      setSelectedAddOns(selectedAddOns.filter(a => a !== addon.name))
                    }
                  }}
                />
                {addon.name} (+${addon.price.toFixed(2)})
              </label>
            ))}
          </div>
        )}

        {item.spice_levels_available.length > 0 && (
          <div className="customization-section">
            <h3>Spice Level</h3>
            <select value={spiceLevel} onChange={(e) => setSpiceLevel(e.target.value)}>
              <option value="">Select spice level</option>
              {item.spice_levels_available.map(level => (
                <option key={level} value={level}>{level}</option>
              ))}
            </select>
          </div>
        )}

        <div className="customization-section">
          <h3>Special Instructions</h3>
          <textarea
            value={specialInstructions}
            onChange={(e) => setSpecialInstructions(e.target.value)}
            placeholder="Any special requests?"
          />
        </div>

        <div className="quantity-selector">
          <button onClick={() => setQuantity(Math.max(1, quantity - 1))}>-</button>
          <span>{quantity}</span>
          <button onClick={() => setQuantity(quantity + 1)}>+</button>
        </div>

        <button className="btn-primary" onClick={handleAddToCart}>
          Add to Cart - ${(item.price * quantity).toFixed(2)}
        </button>
      </div>
    </div>
  )
}

// ===================== CART COMPONENTS =====================
function CartPage() {
  const { cart, removeFromCart, updateQuantity, cartTotal } = useCart()
  const { token } = useAuth()

  if (!token) {
    return <Navigate to="/login" />
  }

  if (!cart || cart.items.length === 0) {
    return (
      <div className="page">
        <div className="empty-state">
          <h2>Your cart is empty</h2>
          <Link to="/menu" className="btn-primary">Browse Menu</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="page">
      <h1>Shopping Cart</h1>

      <div className="cart-items">
        {cart.items.map((item, index) => (
          <div key={index} className="cart-item">
            {item.menu_item_image && (
              <img src={item.menu_item_image} alt={item.menu_item_name} className="cart-item-image" />
            )}
            <div className="cart-item-details">
              <h3>{item.menu_item_name}</h3>
              <p className="price">${item.menu_item_price.toFixed(2)}</p>
            </div>
            <div className="quantity-control">
              <button onClick={() => updateQuantity(index, Math.max(1, item.quantity - 1))}>-</button>
              <span>{item.quantity}</span>
              <button onClick={() => updateQuantity(index, item.quantity + 1)}>+</button>
            </div>
            <p className="item-total">${(item.menu_item_price * item.quantity).toFixed(2)}</p>
            <button className="btn-remove" onClick={() => removeFromCart(index)}>Remove</button>
          </div>
        ))}
      </div>

      <div className="cart-summary">
        <h3>Order Summary</h3>
        <div className="summary-row">
          <span>Subtotal:</span>
          <span>${cartTotal.toFixed(2)}</span>
        </div>
        <div className="summary-row">
          <span>Tax (10%):</span>
          <span>${(cartTotal * 0.1).toFixed(2)}</span>
        </div>
        <div className="summary-row">
          <span>Delivery Fee:</span>
          <span>$5.00</span>
        </div>
        <div className="summary-row total">
          <span>Total:</span>
          <span>${(cartTotal * 1.1 + 5).toFixed(2)}</span>
        </div>
        <Link to="/checkout" className="btn-primary">Proceed to Checkout</Link>
      </div>
    </div>
  )
}

// ===================== CHECKOUT COMPONENTS =====================
function CheckoutPage() {
  const [orderMode, setOrderMode] = useState<'delivery' | 'pickup'>('delivery')
  const [address, setAddress] = useState('')
  const [city, setCity] = useState('')
  const [postalCode, setPostalCode] = useState('')
  const [phone, setPhone] = useState('')
  const [deliveryInstructions, setDeliveryInstructions] = useState('')
  const { cart, cartTotal } = useCart()
  const { token } = useAuth()

  const handlePlaceOrder = async () => {
    if (!token || !cart) return

    try {
      const orderData = {
        venue_id: cart.venue_id,
        order_mode: orderMode,
        delivery_details: orderMode === 'delivery' ? {
          address,
          city,
          postal_code: postalCode,
          phone,
          delivery_instructions: deliveryInstructions
        } : null
      }

      const response = await fetch('/api/orders', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(orderData)
      })

      if (response.ok) {
        const order = await response.json()
        window.location.href = `/payment/${order._id}`
      } else {
        alert('Failed to create order')
      }
    } catch (error) {
      console.error('Order creation failed:', error)
      alert('Failed to create order')
    }
  }

  if (!token) {
    return <Navigate to="/login" />
  }

  return (
    <div className="page">
      <h1>Checkout</h1>

      <div className="checkout-container">
        <div className="checkout-form">
          <h2>Order Details</h2>

          <div className="form-group">
            <label>Order Mode</label>
            <div className="radio-group">
              <label>
                <input
                  type="radio"
                  value="delivery"
                  checked={orderMode === 'delivery'}
                  onChange={() => setOrderMode('delivery')}
                />
                Delivery
              </label>
              <label>
                <input
                  type="radio"
                  value="pickup"
                  checked={orderMode === 'pickup'}
                  onChange={() => setOrderMode('pickup')}
                />
                Pickup
              </label>
            </div>
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

              <div className="form-row">
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

              <div className="form-group">
                <label>Delivery Instructions</label>
                <textarea
                  value={deliveryInstructions}
                  onChange={(e) => setDeliveryInstructions(e.target.value)}
                  placeholder="Any special instructions for delivery?"
                />
              </div>
            </>
          )}

          <button className="btn-primary" onClick={handlePlaceOrder}>
            Place Order
          </button>
        </div>

        <div className="order-summary">
          <h3>Order Summary</h3>
          {cart?.items.map((item, idx) => (
            <div key={idx} className="summary-item">
              <span>{item.menu_item_name} x{item.quantity}</span>
              <span>${(item.menu_item_price * item.quantity).toFixed(2)}</span>
            </div>
          ))}
          <div className="summary-total">
            <span>Total:</span>
            <span>${(cartTotal * 1.1 + (orderMode === 'delivery' ? 5 : 0)).toFixed(2)}</span>
          </div>
        </div>
      </div>
    </div>
  )
}

// ===================== ORDER TRACKING COMPONENTS =====================
function OrdersPage() {
  const [orders, setOrders] = useState<any[]>([])
  const { token } = useAuth()

  useEffect(() => {
    fetchOrders()
  }, [])

  const fetchOrders = async () => {
    if (!token) return

    try {
      const response = await fetch('/api/orders', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (response.ok) {
        const data = await response.json()
        setOrders(data)
      }
    } catch (error) {
      console.error('Failed to fetch orders:', error)
    }
  }

  const handleReorder = async (orderId: string) => {
    if (!token) return

    try {
      const response = await fetch(`/api/orders/${orderId}/reorder`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (response.ok) {
        alert('Items added to cart!')
        window.location.href = '/cart'
      }
    } catch (error) {
      console.error('Reorder failed:', error)
    }
  }

  if (!token) {
    return <Navigate to="/login" />
  }

  return (
    <div className="page">
      <h1>My Orders</h1>

      <div className="orders-list">
        {orders.map(order => (
          <div key={order._id} className="order-card">
            <div className="order-header">
              <h3>Order #{order.order_number}</h3>
              <span className={`status-badge status-${order.order_status}`}>
                {order.order_status}
              </span>
            </div>
            <p>Date: {new Date(order.created_at).toLocaleDateString()}</p>
            <p>Total: ${order.total_amount.toFixed(2)}</p>
            <p>Payment: {order.payment_status}</p>

            <div className="order-items">
              {order.items.map((item: any, idx: number) => (
                <div key={idx} className="order-item">
                  <span>{item.menu_item_name} x{item.quantity}</span>
                  <span>${item.subtotal.toFixed(2)}</span>
                </div>
              ))}
            </div>

            <div className="order-actions">
              <Link to={`/orders/${order._id}`} className="btn-secondary">Track Order</Link>
              <button className="btn-secondary" onClick={() => handleReorder(order._id)}>
                Reorder
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ===================== ADMIN DASHBOARD =====================
function AdminDashboard() {
  const [metrics, setMetrics] = useState<any>(null)
  const { user, token } = useAuth()

  useEffect(() => {
    if (user?.role === 'restaurant_admin') {
      fetchMetrics()
    }
  }, [user])

  const fetchMetrics = async () => {
    if (!token) return

    try {
      const response = await fetch('/api/admin/dashboard', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (response.ok) {
        const data = await response.json()
        setMetrics(data)
      }
    } catch (error) {
      console.error('Failed to fetch metrics:', error)
    }
  }

  if (user?.role !== 'restaurant_admin') {
    return <Navigate to="/" />
  }

  return (
    <div className="page">
      <h1>Admin Dashboard</h1>

      {metrics && (
        <div className="metrics-grid">
          <div className="metric-card">
            <h3>Daily Orders</h3>
            <p className="metric-value">{metrics.daily_orders}</p>
          </div>
          <div className="metric-card">
            <h3>Daily Revenue</h3>
            <p className="metric-value">${metrics.daily_revenue.toFixed(2)}</p>
          </div>
          <div className="metric-card">
            <h3>Active Menu Items</h3>
            <p className="metric-value">{metrics.active_menu_items}</p>
          </div>
          <div className="metric-card">
            <h3>Pending Orders</h3>
            <p className="metric-value">{metrics.pending_orders}</p>
          </div>
        </div>
      )}

      <div className="admin-actions">
        <Link to="/admin/menu" className="btn-primary">Manage Menu</Link>
        <Link to="/admin/orders" className="btn-primary">Manage Orders</Link>
        <Link to="/admin/profile" className="btn-primary">Restaurant Profile</Link>
      </div>
    </div>
  )
}

// ===================== NAVIGATION =====================
function Navigation() {
  const { user, logout } = useAuth()
  const { cartItemsCount } = useCart()

  return (
    <nav className="navbar">
      <Link to="/" className="nav-brand">Food Ordering System</Link>

      <div className="nav-links">
        <Link to="/menu">Menu</Link>

        {user ? (
          <>
            <Link to="/orders">My Orders</Link>
            <Link to="/cart" className="cart-link">
              Cart {cartItemsCount > 0 && <span className="cart-badge">{cartItemsCount}</span>}
            </Link>
            {(user.role === 'restaurant_admin' || user.role === 'staff') && (
              <Link to="/admin">Admin</Link>
            )}
            <span className="user-name">{user.full_name}</span>
            <button onClick={logout} className="btn-secondary">Logout</button>
          </>
        ) : (
          <>
            <Link to="/login" className="btn-secondary">Login</Link>
            <Link to="/register" className="btn-primary">Register</Link>
          </>
        )}
      </div>
    </nav>
  )
}

// ===================== MAIN APP =====================
function AppContent() {
  return (
    <BrowserRouter>
      <Navigation />
      <Routes>
        <Route path="/" element={<Navigate to="/menu" />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/menu" element={<MenuPage />} />
        <Route path="/cart" element={<CartPage />} />
        <Route path="/checkout" element={<CheckoutPage />} />
        <Route path="/orders" element={<OrdersPage />} />
        <Route path="/admin" element={<AdminDashboard />} />
      </Routes>
    </BrowserRouter>
  )
}

function App() {
  return (
    <AuthProvider>
      <CartProvider>
        <AppContent />
      </CartProvider>
    </AuthProvider>
  )
}

export default App
