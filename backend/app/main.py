import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List
from bson import ObjectId
from io import BytesIO

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pymongo.errors import PyMongoError
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.database import (
    get_database, get_mongo_client,
    USERS_COLLECTION, MENU_ITEMS_COLLECTION, CARTS_COLLECTION,
    ORDERS_COLLECTION, INVOICES_COLLECTION, NOTIFICATIONS_COLLECTION,
    VENUES_COLLECTION, RESTAURANT_PROFILES_COLLECTION
)
from app.models import (
    UserCreate, UserLogin, User, Token, UserRole,
    MenuItem, MenuItemCreate, Cart, CartItemAdd, CartItem,
    Order, OrderCreate, OrderStatus, OrderStatusUpdate,
    PaymentIntent, PaymentConfirmation, PaymentStatus,
    Invoice, Notification, NotificationType,
    Venue, VenueCreate, RestaurantProfile, RestaurantProfileUpdate,
    DashboardStats, OAuthProvider, OrderMode
)
from app.auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, require_role
)

load_dotenv(Path(__file__).resolve().parents[2] / '.env')

frontend_port = os.getenv('FRONTEND_PORT', '5173')
backend_port = os.getenv('BACKEND_PORT', '8000')

app = FastAPI(title='Food Ordering System API')

app.add_middleware(
    CORSMiddleware,
    allow_origins=[f'http://localhost:{frontend_port}', 'http://localhost:3000'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


# Health Check
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


# ============ Authentication APIs ============

@app.post('/api/auth/register', response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    db = get_database()
    users = db[USERS_COLLECTION]

    # Check if user already exists
    if users.find_one({"email": user_data.email}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create user
    user_dict = user_data.model_dump()
    user_dict['hashed_password'] = get_password_hash(user_dict.pop('password'))
    user_dict['oauth_provider'] = OAuthProvider.EMAIL.value
    user_dict['created_at'] = datetime.utcnow()
    user_dict['is_active'] = True

    result = users.insert_one(user_dict)
    user_dict['_id'] = str(result.inserted_id)

    # Create access token
    access_token = create_access_token(
        data={"sub": user_dict['_id'], "email": user_dict['email'], "role": user_dict['role']}
    )

    user = User(**{**user_dict, "_id": user_dict['_id']})
    return Token(access_token=access_token, user=user)


@app.post('/api/auth/login', response_model=Token)
async def login(credentials: UserLogin):
    db = get_database()
    users = db[USERS_COLLECTION]

    user = users.find_one({"email": credentials.email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not verify_password(credentials.password, user.get('hashed_password', '')):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    user['_id'] = str(user['_id'])
    access_token = create_access_token(
        data={"sub": user['_id'], "email": user['email'], "role": user.get('role', 'customer')}
    )

    user_obj = User(**user)
    return Token(access_token=access_token, user=user_obj)


@app.get('/api/auth/me', response_model=User)
async def get_me(current_user: dict = Depends(get_current_user)):
    db = get_database()
    users = db[USERS_COLLECTION]

    user = users.find_one({"_id": ObjectId(current_user['sub'])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user['_id'] = str(user['_id'])
    return User(**user)


# ============ Menu APIs ============

@app.get('/api/menu', response_model=List[MenuItem])
async def get_menu(
    venue_id: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    dietary_preference: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None
):
    db = get_database()
    menu_items = db[MENU_ITEMS_COLLECTION]

    query = {"is_available": True}

    if venue_id:
        query["venue_id"] = venue_id
    if category:
        query["category"] = category
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    if dietary_preference:
        query["dietary_preferences"] = dietary_preference
    if min_price is not None or max_price is not None:
        price_query = {}
        if min_price is not None:
            price_query["$gte"] = min_price
        if max_price is not None:
            price_query["$lte"] = max_price
        query["price"] = price_query

    items = list(menu_items.find(query))
    for item in items:
        item['_id'] = str(item['_id'])

    return [MenuItem(**item) for item in items]


@app.get('/api/menu/{item_id}', response_model=MenuItem)
async def get_menu_item(item_id: str):
    db = get_database()
    menu_items = db[MENU_ITEMS_COLLECTION]

    item = menu_items.find_one({"_id": ObjectId(item_id)})
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    item['_id'] = str(item['_id'])
    return MenuItem(**item)


@app.post('/api/menu', response_model=MenuItem, status_code=status.HTTP_201_CREATED)
async def create_menu_item(
    item_data: MenuItemCreate,
    current_user: dict = Depends(require_role([UserRole.RESTAURANT_ADMIN, UserRole.STAFF]))
):
    db = get_database()
    menu_items = db[MENU_ITEMS_COLLECTION]

    item_dict = item_data.model_dump()
    item_dict['created_at'] = datetime.utcnow()
    item_dict['updated_at'] = datetime.utcnow()

    result = menu_items.insert_one(item_dict)
    item_dict['_id'] = str(result.inserted_id)

    return MenuItem(**item_dict)


@app.put('/api/menu/{item_id}', response_model=MenuItem)
async def update_menu_item(
    item_id: str,
    item_data: MenuItemCreate,
    current_user: dict = Depends(require_role([UserRole.RESTAURANT_ADMIN, UserRole.STAFF]))
):
    db = get_database()
    menu_items = db[MENU_ITEMS_COLLECTION]

    item_dict = item_data.model_dump()
    item_dict['updated_at'] = datetime.utcnow()

    result = menu_items.update_one(
        {"_id": ObjectId(item_id)},
        {"$set": item_dict}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Menu item not found")

    item = menu_items.find_one({"_id": ObjectId(item_id)})
    item['_id'] = str(item['_id'])
    return MenuItem(**item)


@app.delete('/api/menu/{item_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_menu_item(
    item_id: str,
    current_user: dict = Depends(require_role([UserRole.RESTAURANT_ADMIN]))
):
    db = get_database()
    menu_items = db[MENU_ITEMS_COLLECTION]

    result = menu_items.delete_one({"_id": ObjectId(item_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Menu item not found")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============ Cart APIs ============

@app.get('/api/cart', response_model=Cart)
async def get_cart(current_user: dict = Depends(get_current_user)):
    db = get_database()
    carts = db[CARTS_COLLECTION]

    cart = carts.find_one({"user_id": current_user['sub']})
    if not cart:
        # Create empty cart
        cart = {
            "user_id": current_user['sub'],
            "venue_id": "",
            "items": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = carts.insert_one(cart)
        cart['_id'] = str(result.inserted_id)
    else:
        cart['_id'] = str(cart['_id'])

    return Cart(**cart)


@app.post('/api/cart/items', response_model=Cart)
async def add_to_cart(
    cart_item: CartItemAdd,
    current_user: dict = Depends(get_current_user)
):
    db = get_database()
    carts = db[CARTS_COLLECTION]
    menu_items = db[MENU_ITEMS_COLLECTION]

    # Get menu item details
    menu_item = menu_items.find_one({"_id": ObjectId(cart_item.item_id)})
    if not menu_item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    cart = carts.find_one({"user_id": current_user['sub']})

    new_cart_item = CartItem(
        item_id=cart_item.item_id,
        item_name=menu_item['name'],
        quantity=cart_item.quantity,
        price=menu_item['price'],
        customization=cart_item.customization
    )

    if not cart:
        cart = {
            "user_id": current_user['sub'],
            "venue_id": menu_item['venue_id'],
            "items": [new_cart_item.model_dump()],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = carts.insert_one(cart)
        cart['_id'] = str(result.inserted_id)
    else:
        # Check if item already exists
        existing_item_index = None
        for i, item in enumerate(cart.get('items', [])):
            if item['item_id'] == cart_item.item_id:
                existing_item_index = i
                break

        if existing_item_index is not None:
            cart['items'][existing_item_index]['quantity'] += cart_item.quantity
        else:
            cart['items'].append(new_cart_item.model_dump())

        cart['updated_at'] = datetime.utcnow()
        carts.update_one(
            {"user_id": current_user['sub']},
            {"$set": {"items": cart['items'], "updated_at": cart['updated_at']}}
        )
        cart['_id'] = str(cart['_id'])

    return Cart(**cart)


@app.put('/api/cart/items/{item_id}')
async def update_cart_item(
    item_id: str,
    quantity: int,
    current_user: dict = Depends(get_current_user)
):
    db = get_database()
    carts = db[CARTS_COLLECTION]

    cart = carts.find_one({"user_id": current_user['sub']})
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    for item in cart.get('items', []):
        if item['item_id'] == item_id:
            if quantity <= 0:
                cart['items'].remove(item)
            else:
                item['quantity'] = quantity
            break

    cart['updated_at'] = datetime.utcnow()
    carts.update_one(
        {"user_id": current_user['sub']},
        {"$set": {"items": cart['items'], "updated_at": cart['updated_at']}}
    )

    cart['_id'] = str(cart['_id'])
    return Cart(**cart)


@app.delete('/api/cart/items/{item_id}', status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_cart(
    item_id: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_database()
    carts = db[CARTS_COLLECTION]

    cart = carts.find_one({"user_id": current_user['sub']})
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    cart['items'] = [item for item in cart.get('items', []) if item['item_id'] != item_id]
    cart['updated_at'] = datetime.utcnow()

    carts.update_one(
        {"user_id": current_user['sub']},
        {"$set": {"items": cart['items'], "updated_at": cart['updated_at']}}
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.delete('/api/cart', status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(current_user: dict = Depends(get_current_user)):
    db = get_database()
    carts = db[CARTS_COLLECTION]

    carts.update_one(
        {"user_id": current_user['sub']},
        {"$set": {"items": [], "updated_at": datetime.utcnow()}}
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============ Order APIs ============

@app.post('/api/orders', response_model=Order, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    current_user: dict = Depends(get_current_user)
):
    db = get_database()
    carts = db[CARTS_COLLECTION]
    orders = db[ORDERS_COLLECTION]

    # Get cart
    cart = carts.find_one({"user_id": current_user['sub']})
    if not cart or not cart.get('items'):
        raise HTTPException(status_code=400, detail="Cart is empty")

    # Calculate total
    total_amount = sum(item['price'] * item['quantity'] for item in cart['items'])

    # Create order
    order = {
        "user_id": current_user['sub'],
        "venue_id": order_data.venue_id,
        "items": cart['items'],
        "order_mode": order_data.order_mode.value,
        "delivery_details": order_data.delivery_details.model_dump() if order_data.delivery_details else None,
        "total_amount": total_amount,
        "payment_status": PaymentStatus.PENDING.value,
        "order_status": OrderStatus.RECEIVED.value,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    result = orders.insert_one(order)
    order['_id'] = str(result.inserted_id)

    # Clear cart
    carts.update_one(
        {"user_id": current_user['sub']},
        {"$set": {"items": [], "updated_at": datetime.utcnow()}}
    )

    # Create notification
    notifications = db[NOTIFICATIONS_COLLECTION]
    notifications.insert_one({
        "user_id": current_user['sub'],
        "type": NotificationType.ORDER_CONFIRMATION.value,
        "title": "Order Confirmed",
        "message": f"Your order #{order['_id'][-6:]} has been placed successfully!",
        "is_read": False,
        "created_at": datetime.utcnow()
    })

    return Order(**order)


@app.get('/api/orders', response_model=List[Order])
async def get_orders(
    current_user: dict = Depends(get_current_user),
    status: Optional[OrderStatus] = None,
    venue_id: Optional[str] = None
):
    db = get_database()
    orders = db[ORDERS_COLLECTION]

    query = {}
    user_role = current_user.get('role')

    if user_role == UserRole.CUSTOMER.value:
        query["user_id"] = current_user['sub']

    if status:
        query["order_status"] = status.value
    if venue_id:
        query["venue_id"] = venue_id

    orders_list = list(orders.find(query).sort("created_at", -1))
    for order in orders_list:
        order['_id'] = str(order['_id'])

    return [Order(**order) for order in orders_list]


@app.get('/api/orders/{order_id}', response_model=Order)
async def get_order(
    order_id: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_database()
    orders = db[ORDERS_COLLECTION]

    order = orders.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Check authorization
    user_role = current_user.get('role')
    if user_role == UserRole.CUSTOMER.value and order['user_id'] != current_user['sub']:
        raise HTTPException(status_code=403, detail="Not authorized to view this order")

    order['_id'] = str(order['_id'])
    return Order(**order)


@app.put('/api/orders/{order_id}/status', response_model=Order)
async def update_order_status(
    order_id: str,
    status_update: OrderStatusUpdate,
    current_user: dict = Depends(require_role([UserRole.RESTAURANT_ADMIN, UserRole.STAFF]))
):
    db = get_database()
    orders = db[ORDERS_COLLECTION]

    result = orders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"order_status": status_update.order_status.value, "updated_at": datetime.utcnow()}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")

    order = orders.find_one({"_id": ObjectId(order_id)})
    order['_id'] = str(order['_id'])

    # Send notification
    notifications = db[NOTIFICATIONS_COLLECTION]
    notifications.insert_one({
        "user_id": order['user_id'],
        "type": NotificationType.ORDER_STATUS_UPDATE.value,
        "title": "Order Status Updated",
        "message": f"Your order #{order_id[-6:]} is now {status_update.order_status.value}",
        "is_read": False,
        "created_at": datetime.utcnow()
    })

    return Order(**order)


@app.post('/api/orders/{order_id}/reorder', response_model=Cart)
async def reorder(
    order_id: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_database()
    orders = db[ORDERS_COLLECTION]
    carts = db[CARTS_COLLECTION]

    order = orders.find_one({"_id": ObjectId(order_id), "user_id": current_user['sub']})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Clear current cart and add order items
    cart = {
        "user_id": current_user['sub'],
        "venue_id": order['venue_id'],
        "items": order['items'],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    carts.update_one(
        {"user_id": current_user['sub']},
        {"$set": cart},
        upsert=True
    )

    existing_cart = carts.find_one({"user_id": current_user['sub']})
    existing_cart['_id'] = str(existing_cart['_id'])

    return Cart(**existing_cart)


# ============ Payment APIs ============

@app.post('/api/payments/intent')
async def create_payment_intent(
    payment_data: PaymentIntent,
    current_user: dict = Depends(get_current_user)
):
    # Mock payment gateway integration
    return {
        "payment_intent_id": f"pi_{ObjectId()}",
        "client_secret": f"secret_{ObjectId()}",
        "amount": payment_data.amount,
        "currency": payment_data.currency
    }


@app.post('/api/payments/confirm')
async def confirm_payment(
    confirmation: PaymentConfirmation,
    current_user: dict = Depends(get_current_user)
):
    db = get_database()
    orders = db[ORDERS_COLLECTION]

    # Mock payment confirmation
    order = orders.find_one({"_id": ObjectId(confirmation.payment_id.split('_')[1])})
    if order:
        orders.update_one(
            {"_id": ObjectId(confirmation.payment_id.split('_')[1])},
            {"$set": {"payment_status": PaymentStatus.COMPLETED.value, "updated_at": datetime.utcnow()}}
        )

        # Create invoice
        invoices = db[INVOICES_COLLECTION]
        invoice = {
            "order_id": str(order['_id']),
            "user_id": order['user_id'],
            "venue_id": order['venue_id'],
            "invoice_number": f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{str(ObjectId())[-6:]}",
            "items": order['items'],
            "subtotal": order['total_amount'],
            "tax": order['total_amount'] * 0.1,
            "total_amount": order['total_amount'] * 1.1,
            "payment_method": "Card",
            "payment_status": PaymentStatus.COMPLETED.value,
            "created_at": datetime.utcnow()
        }
        invoices.insert_one(invoice)

        # Send notification
        notifications = db[NOTIFICATIONS_COLLECTION]
        notifications.insert_one({
            "user_id": order['user_id'],
            "type": NotificationType.PAYMENT_SUCCESS.value,
            "title": "Payment Successful",
            "message": f"Payment for order #{str(order['_id'])[-6:]} was successful!",
            "is_read": False,
            "created_at": datetime.utcnow()
        })

    return {"status": "success", "message": "Payment confirmed"}


# ============ Invoice APIs ============

@app.get('/api/invoices/{order_id}')
async def get_invoice(
    order_id: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_database()
    invoices = db[INVOICES_COLLECTION]

    invoice = invoices.find_one({"order_id": order_id})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice['user_id'] != current_user['sub']:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Generate PDF
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)

    # Header
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, 750, "INVOICE")
    p.setFont("Helvetica", 12)
    p.drawString(50, 730, f"Invoice Number: {invoice['invoice_number']}")
    p.drawString(50, 710, f"Date: {invoice['created_at'].strftime('%Y-%m-%d')}")

    # Items
    y = 670
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Items:")
    y -= 20
    p.setFont("Helvetica", 10)

    for item in invoice['items']:
        p.drawString(50, y, f"{item['item_name']} x{item['quantity']}")
        p.drawString(400, y, f"${item['price'] * item['quantity']:.2f}")
        y -= 15

    # Totals
    y -= 20
    p.setFont("Helvetica", 12)
    p.drawString(50, y, f"Subtotal:")
    p.drawString(400, y, f"${invoice['subtotal']:.2f}")
    y -= 20
    p.drawString(50, y, f"Tax:")
    p.drawString(400, y, f"${invoice['tax']:.2f}")
    y -= 20
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, f"Total:")
    p.drawString(400, y, f"${invoice['total_amount']:.2f}")

    p.showPage()
    p.save()
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=invoice_{invoice['invoice_number']}.pdf"}
    )


# ============ Notification APIs ============

@app.get('/api/notifications', response_model=List[Notification])
async def get_notifications(current_user: dict = Depends(get_current_user)):
    db = get_database()
    notifications = db[NOTIFICATIONS_COLLECTION]

    notifs = list(notifications.find({"user_id": current_user['sub']}).sort("created_at", -1).limit(50))
    for notif in notifs:
        notif['_id'] = str(notif['_id'])

    return [Notification(**notif) for notif in notifs]


@app.put('/api/notifications/{notification_id}/read')
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_database()
    notifications = db[NOTIFICATIONS_COLLECTION]

    result = notifications.update_one(
        {"_id": ObjectId(notification_id), "user_id": current_user['sub']},
        {"$set": {"is_read": True}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")

    return {"status": "success"}


# ============ Venue APIs ============

@app.get('/api/venues', response_model=List[Venue])
async def get_venues():
    db = get_database()
    venues = db[VENUES_COLLECTION]

    venues_list = list(venues.find({"is_active": True}))
    for venue in venues_list:
        venue['_id'] = str(venue['_id'])

    return [Venue(**venue) for venue in venues_list]


@app.post('/api/venues', response_model=Venue, status_code=status.HTTP_201_CREATED)
async def create_venue(
    venue_data: VenueCreate,
    current_user: dict = Depends(require_role([UserRole.RESTAURANT_ADMIN]))
):
    db = get_database()
    venues = db[VENUES_COLLECTION]

    venue_dict = venue_data.model_dump()
    venue_dict['created_at'] = datetime.utcnow()
    venue_dict['is_active'] = True

    result = venues.insert_one(venue_dict)
    venue_dict['_id'] = str(result.inserted_id)

    return Venue(**venue_dict)


# ============ Admin Dashboard APIs ============

@app.get('/api/admin/dashboard', response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: dict = Depends(require_role([UserRole.RESTAURANT_ADMIN, UserRole.STAFF]))
):
    db = get_database()
    orders = db[ORDERS_COLLECTION]
    menu_items = db[MENU_ITEMS_COLLECTION]

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Total orders today
    total_orders_today = orders.count_documents({"created_at": {"$gte": today}})

    # Total revenue today
    orders_today = list(orders.find({"created_at": {"$gte": today}, "payment_status": PaymentStatus.COMPLETED.value}))
    total_revenue_today = sum(order.get('total_amount', 0) for order in orders_today)

    # Active orders
    active_orders = orders.count_documents({
        "order_status": {"$in": [OrderStatus.RECEIVED.value, OrderStatus.PREPARING.value, OrderStatus.OUT_FOR_DELIVERY.value]}
    })

    # Total menu items
    total_menu_items = menu_items.count_documents({"is_available": True})

    # Pending orders
    pending_orders = orders.count_documents({"order_status": OrderStatus.RECEIVED.value})

    # Completed orders today
    completed_orders_today = orders.count_documents({
        "created_at": {"$gte": today},
        "order_status": OrderStatus.COMPLETED.value
    })

    return DashboardStats(
        total_orders_today=total_orders_today,
        total_revenue_today=total_revenue_today,
        active_orders=active_orders,
        total_menu_items=total_menu_items,
        pending_orders=pending_orders,
        completed_orders_today=completed_orders_today
    )


# ============ Restaurant Profile APIs ============

@app.get('/api/restaurant/profile/{venue_id}', response_model=RestaurantProfile)
async def get_restaurant_profile(venue_id: str):
    db = get_database()
    profiles = db[RESTAURANT_PROFILES_COLLECTION]

    profile = profiles.find_one({"venue_id": venue_id})
    if not profile:
        # Create default profile
        profile = {
            "venue_id": venue_id,
            "tax_rate": 0.1,
            "currency": "USD",
            "updated_at": datetime.utcnow()
        }
        result = profiles.insert_one(profile)
        profile['_id'] = str(result.inserted_id)
    else:
        profile['_id'] = str(profile['_id'])

    return RestaurantProfile(**profile)


@app.put('/api/restaurant/profile/{venue_id}', response_model=RestaurantProfile)
async def update_restaurant_profile(
    venue_id: str,
    profile_data: RestaurantProfileUpdate,
    current_user: dict = Depends(require_role([UserRole.RESTAURANT_ADMIN]))
):
    db = get_database()
    profiles = db[RESTAURANT_PROFILES_COLLECTION]

    update_dict = {k: v for k, v in profile_data.model_dump().items() if v is not None}
    update_dict['updated_at'] = datetime.utcnow()

    profiles.update_one(
        {"venue_id": venue_id},
        {"$set": update_dict},
        upsert=True
    )

    profile = profiles.find_one({"venue_id": venue_id})
    profile['_id'] = str(profile['_id'])

    return RestaurantProfile(**profile)
