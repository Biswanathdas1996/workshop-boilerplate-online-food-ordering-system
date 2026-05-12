from functools import lru_cache
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError
from bson import ObjectId
import stripe
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
from fastapi.responses import StreamingResponse

from .models import (
    UserRegister, UserLogin, UserResponse, UserRole, Token,
    CategoryCreate, CategoryInDB,
    MenuItemCreate, MenuItemUpdate, MenuItemInDB, DietaryPreference,
    CartItemBase, CartInDB, CartItem,
    OrderCreate, OrderInDB, OrderStatus, PaymentStatus, OrderMode,
    InvoiceInDB,
    RestaurantProfileCreate, RestaurantProfileUpdate, RestaurantProfileInDB,
    VenueCreate, VenueInDB,
    NotificationCreate, NotificationInDB, NotificationType
)
from .auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, require_role, oauth2_scheme
)

load_dotenv(Path(__file__).resolve().parents[2] / '.env')

frontend_port = os.getenv('FRONTEND_PORT', '5173')
backend_port = os.getenv('BACKEND_PORT', '8000')
stripe.api_key = os.getenv('STRIPE_SECRET_KEY', 'sk_test_dummy')

app = FastAPI(title='Online Food Ordering System API')

app.add_middleware(
    CORSMiddleware,
    allow_origins=[f'http://localhost:{frontend_port}'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_order_update(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
            except:
                self.disconnect(user_id)


manager = ConnectionManager()


@lru_cache(maxsize=1)
def get_mongo_client() -> MongoClient:
    mongodb_uri = os.getenv('MONGODB_URI')
    if not mongodb_uri:
        raise RuntimeError('MONGODB_URI is not configured.')
    return MongoClient(mongodb_uri, serverSelectionTimeoutMS=3000)


def get_db() -> Database:
    """Get database instance."""
    client = get_mongo_client()
    return client.get_default_database()


async def get_current_user_with_db(token: str = Depends(oauth2_scheme)):
    """Get current user with database dependency."""
    db = get_db()
    from .auth import get_current_user as _get_current_user
    return await _get_current_user(token, db)


# ==================== HEALTH CHECK ====================
@app.get('/api/health')
def health_check() -> dict[str, object]:
    backend_status = 'connected'
    database_status = 'disconnected'
    database_name = None

    try:
        client = get_mongo_client()
        client.admin.command('ping')
        default_database = client.get_default_database()
        database_name = default_database.name if default_database is not None else None
        database_status = 'connected'
    except (PyMongoError, RuntimeError):
        database_status = 'disconnected'

    return {
        'frontend': 'active',
        'backend': backend_status,
        'database': database_status,
        'databaseName': database_name,
        'backendPort': backend_port,
    }


# ==================== AUTHENTICATION APIs ====================
@app.post('/api/auth/register', response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserRegister):
    """Register a new user."""
    db = get_db()

    # Check if user already exists
    existing_user = db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    user_dict = user_data.model_dump(exclude={'password'})
    user_dict['hashed_password'] = get_password_hash(user_data.password)
    user_dict['created_at'] = datetime.utcnow()
    user_dict['updated_at'] = datetime.utcnow()

    result = db.users.insert_one(user_dict)
    user_dict['_id'] = str(result.inserted_id)

    return UserResponse(**user_dict)


@app.post('/api/auth/login', response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login user and return JWT token."""
    db = get_db()

    user_dict = db.users.find_one({"email": form_data.username})
    if not user_dict or not verify_password(form_data.password, user_dict.get('hashed_password', '')):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user_dict['email'], "role": user_dict.get('role', 'customer')}
    )

    return Token(access_token=access_token)


@app.get('/api/auth/me', response_model=UserResponse)
async def get_current_user_info(current_user = Depends(get_current_user_with_db)):
    """Get current user information."""
    return UserResponse(
        _id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        phone=current_user.phone,
        role=current_user.role,
        created_at=current_user.created_at
    )


# ==================== VENUE APIs ====================
@app.post('/api/venues', response_model=VenueInDB, status_code=status.HTTP_201_CREATED)
async def create_venue(
    venue_data: VenueCreate,
    current_user = Depends(get_current_user_with_db)
):
    """Create a new venue (admin only)."""
    if current_user.role not in [UserRole.RESTAURANT_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    db = get_db()
    venue_dict = venue_data.model_dump()
    venue_dict['created_at'] = datetime.utcnow()
    venue_dict['updated_at'] = datetime.utcnow()

    result = db.venues.insert_one(venue_dict)
    venue_dict['_id'] = str(result.inserted_id)

    return VenueInDB(**venue_dict)


@app.get('/api/venues', response_model=List[VenueInDB])
async def list_venues():
    """List all active venues."""
    db = get_db()
    venues = list(db.venues.find({"is_active": True}))

    for venue in venues:
        venue['_id'] = str(venue['_id'])

    return [VenueInDB(**venue) for venue in venues]


@app.get('/api/venues/{venue_id}', response_model=VenueInDB)
async def get_venue(venue_id: str):
    """Get venue details."""
    db = get_db()
    venue = db.venues.find_one({"_id": ObjectId(venue_id)})

    if not venue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found")

    venue['_id'] = str(venue['_id'])
    return VenueInDB(**venue)


# ==================== CATEGORY APIs ====================
@app.post('/api/categories', response_model=CategoryInDB, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    current_user = Depends(get_current_user_with_db)
):
    """Create a new category (admin only)."""
    if current_user.role not in [UserRole.RESTAURANT_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    db = get_db()
    category_dict = category_data.model_dump()
    category_dict['created_at'] = datetime.utcnow()

    result = db.categories.insert_one(category_dict)
    category_dict['_id'] = str(result.inserted_id)

    return CategoryInDB(**category_dict)


@app.get('/api/categories', response_model=List[CategoryInDB])
async def list_categories(venue_id: str = Query(...)):
    """List all categories for a venue."""
    db = get_db()
    categories = list(db.categories.find({"venue_id": venue_id}).sort("display_order", 1))

    for cat in categories:
        cat['_id'] = str(cat['_id'])

    return [CategoryInDB(**cat) for cat in categories]


# ==================== MENU ITEM APIs ====================
@app.post('/api/menu-items', response_model=MenuItemInDB, status_code=status.HTTP_201_CREATED)
async def create_menu_item(
    item_data: MenuItemCreate,
    current_user = Depends(get_current_user_with_db)
):
    """Create a new menu item (admin only)."""
    if current_user.role not in [UserRole.RESTAURANT_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    db = get_db()
    item_dict = item_data.model_dump()
    item_dict['created_at'] = datetime.utcnow()
    item_dict['updated_at'] = datetime.utcnow()

    result = db.menu_items.insert_one(item_dict)
    item_dict['_id'] = str(result.inserted_id)

    return MenuItemInDB(**item_dict)


@app.get('/api/menu-items', response_model=List[MenuItemInDB])
async def list_menu_items(
    venue_id: str = Query(...),
    category_id: Optional[str] = None,
    search: Optional[str] = None,
    dietary_preference: Optional[DietaryPreference] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None
):
    """List menu items with search and filters."""
    db = get_db()
    query = {"venue_id": venue_id, "is_available": True}

    if category_id:
        query['category_id'] = category_id

    if search:
        query['$or'] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]

    if dietary_preference:
        query['dietary_preferences'] = dietary_preference

    if min_price is not None or max_price is not None:
        query['price'] = {}
        if min_price is not None:
            query['price']['$gte'] = min_price
        if max_price is not None:
            query['price']['$lte'] = max_price

    items = list(db.menu_items.find(query))

    for item in items:
        item['_id'] = str(item['_id'])

    return [MenuItemInDB(**item) for item in items]


@app.get('/api/menu-items/{item_id}', response_model=MenuItemInDB)
async def get_menu_item(item_id: str):
    """Get menu item details."""
    db = get_db()
    item = db.menu_items.find_one({"_id": ObjectId(item_id)})

    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")

    item['_id'] = str(item['_id'])
    return MenuItemInDB(**item)


@app.put('/api/menu-items/{item_id}', response_model=MenuItemInDB)
async def update_menu_item(
    item_id: str,
    item_data: MenuItemUpdate,
    current_user = Depends(get_current_user_with_db)
):
    """Update menu item (admin only)."""
    if current_user.role not in [UserRole.RESTAURANT_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    db = get_db()
    update_data = {k: v for k, v in item_data.model_dump(exclude_unset=True).items() if v is not None}
    update_data['updated_at'] = datetime.utcnow()

    result = db.menu_items.find_one_and_update(
        {"_id": ObjectId(item_id)},
        {"$set": update_data},
        return_document=True
    )

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")

    result['_id'] = str(result['_id'])
    return MenuItemInDB(**result)


@app.delete('/api/menu-items/{item_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_menu_item(
    item_id: str,
    current_user = Depends(get_current_user_with_db)
):
    """Delete menu item (admin only)."""
    if current_user.role not in [UserRole.RESTAURANT_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    db = get_db()
    result = db.menu_items.delete_one({"_id": ObjectId(item_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")

    return None


# ==================== CART APIs ====================
@app.post('/api/cart/items', status_code=status.HTTP_201_CREATED)
async def add_to_cart(
    cart_item: CartItemBase,
    current_user = Depends(get_current_user_with_db)
):
    """Add item to cart."""
    db = get_db()

    # Get menu item details
    menu_item = db.menu_items.find_one({"_id": ObjectId(cart_item.menu_item_id)})
    if not menu_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")

    # Get or create cart
    cart = db.carts.find_one({"user_id": current_user.id})

    cart_item_dict = {
        "menu_item_id": cart_item.menu_item_id,
        "menu_item_name": menu_item['name'],
        "menu_item_price": menu_item['price'],
        "menu_item_image": menu_item.get('image_url'),
        "quantity": cart_item.quantity,
        "customization": cart_item.customization.model_dump() if cart_item.customization else None
    }

    if cart:
        # Update existing cart
        items = cart.get('items', [])
        items.append(cart_item_dict)
        db.carts.update_one(
            {"_id": cart['_id']},
            {"$set": {"items": items, "updated_at": datetime.utcnow()}}
        )
    else:
        # Create new cart
        new_cart = {
            "user_id": current_user.id,
            "venue_id": menu_item['venue_id'],
            "items": [cart_item_dict],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        db.carts.insert_one(new_cart)

    return {"message": "Item added to cart"}


@app.get('/api/cart', response_model=CartInDB)
async def get_cart(current_user = Depends(get_current_user_with_db)):
    """Get user's cart."""
    db = get_db()
    cart = db.carts.find_one({"user_id": current_user.id})

    if not cart:
        # Return empty cart
        return CartInDB(
            _id="new",
            user_id=current_user.id,
            venue_id="",
            items=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

    cart['_id'] = str(cart['_id'])
    return CartInDB(**cart)


@app.delete('/api/cart/items/{item_index}', status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_cart(
    item_index: int,
    current_user = Depends(get_current_user_with_db)
):
    """Remove item from cart."""
    db = get_db()
    cart = db.carts.find_one({"user_id": current_user.id})

    if not cart or item_index >= len(cart.get('items', [])):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")

    items = cart['items']
    items.pop(item_index)

    db.carts.update_one(
        {"_id": cart['_id']},
        {"$set": {"items": items, "updated_at": datetime.utcnow()}}
    )

    return None


@app.put('/api/cart/items/{item_index}/quantity')
async def update_cart_item_quantity(
    item_index: int,
    quantity: int,
    current_user = Depends(get_current_user_with_db)
):
    """Update cart item quantity."""
    db = get_db()
    cart = db.carts.find_one({"user_id": current_user.id})

    if not cart or item_index >= len(cart.get('items', [])):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")

    items = cart['items']
    items[item_index]['quantity'] = quantity

    db.carts.update_one(
        {"_id": cart['_id']},
        {"$set": {"items": items, "updated_at": datetime.utcnow()}}
    )

    return {"message": "Quantity updated"}


@app.delete('/api/cart', status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(current_user = Depends(get_current_user_with_db)):
    """Clear user's cart."""
    db = get_db()
    db.carts.delete_one({"user_id": current_user.id})
    return None


# ==================== ORDER APIs ====================
@app.post('/api/orders', response_model=OrderInDB, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    current_user = Depends(get_current_user_with_db)
):
    """Create a new order from cart."""
    db = get_db()

    # Get user's cart
    cart = db.carts.find_one({"user_id": current_user.id, "venue_id": order_data.venue_id})
    if not cart or not cart.get('items'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty")

    # Calculate totals
    subtotal = sum(item['menu_item_price'] * item['quantity'] for item in cart['items'])
    tax = subtotal * 0.1  # 10% tax
    delivery_fee = 5.0 if order_data.order_mode == OrderMode.DELIVERY else 0.0
    total_amount = subtotal + tax + delivery_fee

    # Generate order number
    order_number = f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

    # Create order
    order_dict = {
        "user_id": current_user.id,
        "venue_id": order_data.venue_id,
        "order_number": order_number,
        "items": cart['items'],
        "order_mode": order_data.order_mode,
        "delivery_details": order_data.delivery_details.model_dump() if order_data.delivery_details else None,
        "pickup_time": order_data.pickup_time,
        "subtotal": subtotal,
        "tax": tax,
        "delivery_fee": delivery_fee,
        "total_amount": total_amount,
        "payment_status": PaymentStatus.PENDING,
        "order_status": OrderStatus.RECEIVED,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    result = db.orders.insert_one(order_dict)
    order_dict['_id'] = str(result.inserted_id)

    # Clear cart
    db.carts.delete_one({"_id": cart['_id']})

    # Create notification
    notification_dict = {
        "user_id": current_user.id,
        "notification_type": NotificationType.ORDER_CONFIRMATION,
        "title": "Order Confirmed",
        "message": f"Your order {order_number} has been confirmed.",
        "related_order_id": order_dict['_id'],
        "is_read": False,
        "created_at": datetime.utcnow()
    }
    db.notifications.insert_one(notification_dict)

    return OrderInDB(**order_dict)


@app.get('/api/orders', response_model=List[OrderInDB])
async def list_orders(current_user = Depends(get_current_user_with_db)):
    """List user's orders."""
    db = get_db()
    orders = list(db.orders.find({"user_id": current_user.id}).sort("created_at", -1))

    for order in orders:
        order['_id'] = str(order['_id'])

    return [OrderInDB(**order) for order in orders]


@app.get('/api/orders/{order_id}', response_model=OrderInDB)
async def get_order(
    order_id: str,
    current_user = Depends(get_current_user_with_db)
):
    """Get order details."""
    db = get_db()
    order = db.orders.find_one({"_id": ObjectId(order_id)})

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # Check permission
    if order['user_id'] != current_user.id and current_user.role not in [UserRole.RESTAURANT_ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    order['_id'] = str(order['_id'])
    return OrderInDB(**order)


@app.post('/api/orders/{order_id}/reorder', response_model=OrderInDB)
async def reorder(
    order_id: str,
    current_user = Depends(get_current_user_with_db)
):
    """Reorder from a previous order."""
    db = get_db()
    old_order = db.orders.find_one({"_id": ObjectId(order_id), "user_id": current_user.id})

    if not old_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # Create new cart from old order
    cart_dict = {
        "user_id": current_user.id,
        "venue_id": old_order['venue_id'],
        "items": old_order['items'],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    # Delete existing cart if any
    db.carts.delete_one({"user_id": current_user.id})
    db.carts.insert_one(cart_dict)

    return {"message": "Items added to cart. Please proceed to checkout."}


# ==================== PAYMENT APIs ====================
@app.post('/api/payments/create-intent')
async def create_payment_intent(
    order_id: str,
    current_user = Depends(get_current_user_with_db)
):
    """Create Stripe payment intent."""
    db = get_db()
    order = db.orders.find_one({"_id": ObjectId(order_id), "user_id": current_user.id})

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    try:
        # Create Stripe payment intent
        intent = stripe.PaymentIntent.create(
            amount=int(order['total_amount'] * 100),  # Convert to cents
            currency='usd',
            metadata={'order_id': order_id}
        )

        # Update order with payment intent ID
        db.orders.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"payment_intent_id": intent.id, "payment_status": PaymentStatus.PROCESSING}}
        )

        return {"client_secret": intent.client_secret}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.post('/api/payments/webhook')
async def payment_webhook(payload: dict):
    """Handle Stripe webhook events."""
    db = get_db()

    # In production, verify webhook signature
    event_type = payload.get('type')

    if event_type == 'payment_intent.succeeded':
        payment_intent = payload['data']['object']
        order_id = payment_intent['metadata'].get('order_id')

        if order_id:
            db.orders.update_one(
                {"_id": ObjectId(order_id)},
                {"$set": {"payment_status": PaymentStatus.COMPLETED, "updated_at": datetime.utcnow()}}
            )

            # Create invoice
            order = db.orders.find_one({"_id": ObjectId(order_id)})
            if order:
                invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
                invoice_dict = {
                    "order_id": order_id,
                    "order_number": order['order_number'],
                    "user_id": order['user_id'],
                    "venue_id": order['venue_id'],
                    "invoice_number": invoice_number,
                    "invoice_date": datetime.utcnow(),
                    "items": order['items'],
                    "subtotal": order['subtotal'],
                    "tax": order['tax'],
                    "delivery_fee": order['delivery_fee'],
                    "total_amount": order['total_amount'],
                    "payment_method": "card",
                    "payment_status": PaymentStatus.COMPLETED,
                    "created_at": datetime.utcnow()
                }
                db.invoices.insert_one(invoice_dict)

    elif event_type == 'payment_intent.payment_failed':
        payment_intent = payload['data']['object']
        order_id = payment_intent['metadata'].get('order_id')

        if order_id:
            db.orders.update_one(
                {"_id": ObjectId(order_id)},
                {"$set": {"payment_status": PaymentStatus.FAILED, "updated_at": datetime.utcnow()}}
            )

    return {"status": "success"}


# ==================== INVOICE APIs ====================
@app.get('/api/invoices/{order_id}')
async def get_invoice(
    order_id: str,
    current_user = Depends(get_current_user_with_db)
):
    """Get invoice for an order."""
    db = get_db()
    invoice = db.invoices.find_one({"order_id": order_id})

    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    # Check permission
    if invoice['user_id'] != current_user.id and current_user.role not in [UserRole.RESTAURANT_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    invoice['_id'] = str(invoice['_id'])
    return InvoiceInDB(**invoice)


@app.get('/api/invoices/{order_id}/download')
async def download_invoice(
    order_id: str,
    current_user = Depends(get_current_user_with_db)
):
    """Download invoice as PDF."""
    db = get_db()
    invoice = db.invoices.find_one({"order_id": order_id})

    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    # Check permission
    if invoice['user_id'] != current_user.id and current_user.role not in [UserRole.RESTAURANT_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    # Generate PDF
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)

    # Add invoice content
    p.drawString(100, 750, f"INVOICE #{invoice['invoice_number']}")
    p.drawString(100, 730, f"Date: {invoice['invoice_date'].strftime('%Y-%m-%d')}")
    p.drawString(100, 710, f"Order Number: {invoice['order_number']}")

    y = 680
    p.drawString(100, y, "Items:")
    y -= 20

    for item in invoice['items']:
        p.drawString(120, y, f"{item['menu_item_name']} x{item['quantity']} - ${item['subtotal']:.2f}")
        y -= 20

    y -= 10
    p.drawString(100, y, f"Subtotal: ${invoice['subtotal']:.2f}")
    y -= 20
    p.drawString(100, y, f"Tax: ${invoice['tax']:.2f}")
    y -= 20
    p.drawString(100, y, f"Delivery Fee: ${invoice['delivery_fee']:.2f}")
    y -= 20
    p.drawString(100, y, f"Total: ${invoice['total_amount']:.2f}")

    p.showPage()
    p.save()

    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=invoice_{invoice['invoice_number']}.pdf"}
    )


# ==================== ADMIN DASHBOARD APIs ====================
@app.get('/api/admin/dashboard')
async def get_dashboard_metrics(
    current_user = Depends(get_current_user_with_db)
):
    """Get admin dashboard metrics."""
    if current_user.role not in [UserRole.RESTAURANT_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    db = get_db()
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Get daily orders
    daily_orders = db.orders.count_documents({
        "created_at": {"$gte": today}
    })

    # Get daily revenue
    pipeline = [
        {"$match": {"created_at": {"$gte": today}, "payment_status": PaymentStatus.COMPLETED}},
        {"$group": {"_id": None, "total": {"$sum": "$total_amount"}}}
    ]
    daily_revenue_result = list(db.orders.aggregate(pipeline))
    daily_revenue = daily_revenue_result[0]['total'] if daily_revenue_result else 0

    # Get active menu items count
    active_items = db.menu_items.count_documents({"is_available": True})

    # Get pending orders
    pending_orders = db.orders.count_documents({
        "order_status": {"$in": [OrderStatus.RECEIVED, OrderStatus.PREPARING]}
    })

    return {
        "daily_orders": daily_orders,
        "daily_revenue": daily_revenue,
        "active_menu_items": active_items,
        "pending_orders": pending_orders
    }


# ==================== ORDER MANAGEMENT APIs (Staff) ====================
@app.get('/api/staff/orders', response_model=List[OrderInDB])
async def list_orders_for_staff(
    current_user = Depends(get_current_user_with_db),
    status: Optional[OrderStatus] = None
):
    """List orders for staff management."""
    if current_user.role not in [UserRole.RESTAURANT_ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    db = get_db()
    query = {}
    if status:
        query['order_status'] = status

    orders = list(db.orders.find(query).sort("created_at", -1))

    for order in orders:
        order['_id'] = str(order['_id'])

    return [OrderInDB(**order) for order in orders]


@app.put('/api/staff/orders/{order_id}/status')
async def update_order_status(
    order_id: str,
    new_status: OrderStatus,
    current_user = Depends(get_current_user_with_db)
):
    """Update order status (staff only)."""
    if current_user.role not in [UserRole.RESTAURANT_ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    db = get_db()
    order = db.orders.find_one_and_update(
        {"_id": ObjectId(order_id)},
        {"$set": {"order_status": new_status, "updated_at": datetime.utcnow()}},
        return_document=True
    )

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # Send notification to customer
    notification_dict = {
        "user_id": order['user_id'],
        "notification_type": NotificationType.ORDER_STATUS_UPDATE,
        "title": "Order Status Updated",
        "message": f"Your order {order['order_number']} is now {new_status}.",
        "related_order_id": order_id,
        "is_read": False,
        "created_at": datetime.utcnow()
    }
    db.notifications.insert_one(notification_dict)

    # Send WebSocket update
    await manager.send_order_update(order['user_id'], {
        "order_id": order_id,
        "status": new_status,
        "message": f"Your order is now {new_status}"
    })

    return {"message": "Order status updated"}


# ==================== RESTAURANT PROFILE APIs ====================
@app.post('/api/restaurant-profiles', response_model=RestaurantProfileInDB, status_code=status.HTTP_201_CREATED)
async def create_restaurant_profile(
    profile_data: RestaurantProfileCreate,
    current_user = Depends(get_current_user_with_db)
):
    """Create restaurant profile (admin only)."""
    if current_user.role not in [UserRole.RESTAURANT_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    db = get_db()
    profile_dict = profile_data.model_dump()
    profile_dict['created_at'] = datetime.utcnow()
    profile_dict['updated_at'] = datetime.utcnow()

    result = db.restaurant_profiles.insert_one(profile_dict)
    profile_dict['_id'] = str(result.inserted_id)

    return RestaurantProfileInDB(**profile_dict)


@app.get('/api/restaurant-profiles/{venue_id}', response_model=RestaurantProfileInDB)
async def get_restaurant_profile(venue_id: str):
    """Get restaurant profile."""
    db = get_db()
    profile = db.restaurant_profiles.find_one({"venue_id": venue_id})

    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant profile not found")

    profile['_id'] = str(profile['_id'])
    return RestaurantProfileInDB(**profile)


@app.put('/api/restaurant-profiles/{venue_id}', response_model=RestaurantProfileInDB)
async def update_restaurant_profile(
    venue_id: str,
    profile_data: RestaurantProfileUpdate,
    current_user = Depends(get_current_user_with_db)
):
    """Update restaurant profile (admin only)."""
    if current_user.role not in [UserRole.RESTAURANT_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    db = get_db()
    update_data = {k: v for k, v in profile_data.model_dump(exclude_unset=True).items() if v is not None}
    update_data['updated_at'] = datetime.utcnow()

    profile = db.restaurant_profiles.find_one_and_update(
        {"venue_id": venue_id},
        {"$set": update_data},
        return_document=True
    )

    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant profile not found")

    profile['_id'] = str(profile['_id'])
    return RestaurantProfileInDB(**profile)


# ==================== NOTIFICATION APIs ====================
@app.get('/api/notifications', response_model=List[NotificationInDB])
async def list_notifications(
    current_user = Depends(get_current_user_with_db),
    unread_only: bool = False
):
    """List user notifications."""
    db = get_db()
    query = {"user_id": current_user.id}
    if unread_only:
        query['is_read'] = False

    notifications = list(db.notifications.find(query).sort("created_at", -1).limit(50))

    for notif in notifications:
        notif['_id'] = str(notif['_id'])

    return [NotificationInDB(**notif) for notif in notifications]


@app.put('/api/notifications/{notification_id}/read')
async def mark_notification_read(
    notification_id: str,
    current_user = Depends(get_current_user_with_db)
):
    """Mark notification as read."""
    db = get_db()
    result = db.notifications.update_one(
        {"_id": ObjectId(notification_id), "user_id": current_user.id},
        {"$set": {"is_read": True}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    return {"message": "Notification marked as read"}


# ==================== WEBSOCKET APIs ====================
@app.websocket("/ws/orders/{user_id}")
async def websocket_order_tracking(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time order tracking."""
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id)
