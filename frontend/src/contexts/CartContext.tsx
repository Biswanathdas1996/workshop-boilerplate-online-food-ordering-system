import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useAuth } from './AuthContext'

interface CartItem {
  menu_item_id: string
  menu_item_name: string
  menu_item_price: number
  menu_item_image?: string
  quantity: number
  customization?: {
    add_ons: string[]
    spice_level?: string
    special_instructions?: string
  }
}

interface Cart {
  _id: string
  user_id: string
  venue_id: string
  items: CartItem[]
  created_at: string
  updated_at: string
}

interface CartContextType {
  cart: Cart | null
  addToCart: (item: CartItem) => Promise<void>
  removeFromCart: (index: number) => Promise<void>
  updateQuantity: (index: number, quantity: number) => Promise<void>
  clearCart: () => Promise<void>
  refreshCart: () => Promise<void>
  cartTotal: number
  cartItemsCount: number
}

const CartContext = createContext<CartContextType | undefined>(undefined)

export const CartProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [cart, setCart] = useState<Cart | null>(null)
  const { token } = useAuth()

  const refreshCart = async () => {
    if (!token) {
      setCart(null)
      return
    }

    try {
      const response = await fetch('/api/cart', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (response.ok) {
        const data = await response.json()
        setCart(data)
      }
    } catch (error) {
      console.error('Failed to fetch cart:', error)
    }
  }

  useEffect(() => {
    if (token) {
      refreshCart()
    } else {
      setCart(null)
    }
  }, [token])

  const addToCart = async (item: CartItem) => {
    if (!token) throw new Error('Must be logged in')

    const response = await fetch('/api/cart/items', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        menu_item_id: item.menu_item_id,
        quantity: item.quantity,
        customization: item.customization
      })
    })

    if (!response.ok) throw new Error('Failed to add to cart')

    await refreshCart()
  }

  const removeFromCart = async (index: number) => {
    if (!token) throw new Error('Must be logged in')

    const response = await fetch(`/api/cart/items/${index}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (!response.ok) throw new Error('Failed to remove from cart')

    await refreshCart()
  }

  const updateQuantity = async (index: number, quantity: number) => {
    if (!token) throw new Error('Must be logged in')

    const response = await fetch(`/api/cart/items/${index}/quantity?quantity=${quantity}`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (!response.ok) throw new Error('Failed to update quantity')

    await refreshCart()
  }

  const clearCart = async () => {
    if (!token) throw new Error('Must be logged in')

    const response = await fetch('/api/cart', {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (!response.ok) throw new Error('Failed to clear cart')

    await refreshCart()
  }

  const cartTotal = cart?.items.reduce((total, item) => {
    return total + (item.menu_item_price * item.quantity)
  }, 0) || 0

  const cartItemsCount = cart?.items.reduce((count, item) => {
    return count + item.quantity
  }, 0) || 0

  return (
    <CartContext.Provider value={{
      cart,
      addToCart,
      removeFromCart,
      updateQuantity,
      clearCart,
      refreshCart,
      cartTotal,
      cartItemsCount
    }}>
      {children}
    </CartContext.Provider>
  )
}

export const useCart = (): CartContextType => {
  const context = useContext(CartContext)
  if (context === undefined) {
    throw new Error('useCart must be used within a CartProvider')
  }
  return context
}
