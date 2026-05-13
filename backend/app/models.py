from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


class UserRole(str, Enum):
    CUSTOMER = "customer"
    RESTAURANT_ADMIN = "restaurant_admin"
    STAFF = "staff"


class OAuthProvider(str, Enum):
    GOOGLE = "google"
    FACEBOOK = "facebook"
    EMAIL = "email"


class OrderStatus(str, Enum):
    RECEIVED = "received"
    PREPARING = "preparing"
    READY = "ready"
    OUT_FOR_DELIVERY = "out_for_delivery"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class OrderMode(str, Enum):
    DELIVERY = "delivery"
    PICKUP = "pickup"
    DINE_IN = "dine_in"


class DietaryPreference(str, Enum):
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    NON_VEGETARIAN = "non_vegetarian"
    GLUTEN_FREE = "gluten_free"
    HALAL = "halal"
    KOSHER = "kosher"


class NotificationType(str, Enum):
    ORDER_CONFIRMATION = "order_confirmation"
    ORDER_STATUS_UPDATE = "order_status_update"
    ORDER_CANCELLED = "order_cancelled"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"


# User Models
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: UserRole = UserRole.CUSTOMER


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class User(UserBase):
    id: str = Field(alias="_id")
    oauth_provider: OAuthProvider = OAuthProvider.EMAIL
    oauth_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

    class Config:
        populate_by_name = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User


# Menu Models
class AddOn(BaseModel):
    name: str
    price: float


class MenuItem(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    venue_id: str
    name: str
    description: Optional[str] = None
    category: str
    price: float
    image_url: Optional[str] = None
    ingredients: List[str] = []
    add_ons: List[AddOn] = []
    spice_levels: List[str] = ["mild", "medium", "hot"]
    dietary_preferences: List[DietaryPreference] = []
    is_available: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class MenuItemCreate(BaseModel):
    venue_id: str
    name: str
    description: Optional[str] = None
    category: str
    price: float
    image_url: Optional[str] = None
    ingredients: List[str] = []
    add_ons: List[AddOn] = []
    spice_levels: List[str] = ["mild", "medium", "hot"]
    dietary_preferences: List[DietaryPreference] = []
    is_available: bool = True


# Cart Models
class CartItemCustomization(BaseModel):
    add_ons: List[str] = []
    spice_level: Optional[str] = None
    special_instructions: Optional[str] = None


class CartItem(BaseModel):
    item_id: str
    item_name: str
    quantity: int
    price: float
    customization: Optional[CartItemCustomization] = None


class Cart(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    user_id: str
    venue_id: str
    items: List[CartItem] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class CartItemAdd(BaseModel):
    item_id: str
    quantity: int = 1
    customization: Optional[CartItemCustomization] = None


# Order Models
class DeliveryDetails(BaseModel):
    address: str
    city: str
    postal_code: str
    phone: str
    delivery_instructions: Optional[str] = None


class Order(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    user_id: str
    venue_id: str
    items: List[CartItem]
    order_mode: OrderMode
    delivery_details: Optional[DeliveryDetails] = None
    total_amount: float
    payment_status: PaymentStatus = PaymentStatus.PENDING
    order_status: OrderStatus = OrderStatus.RECEIVED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class OrderCreate(BaseModel):
    venue_id: str
    order_mode: OrderMode
    delivery_details: Optional[DeliveryDetails] = None


class OrderStatusUpdate(BaseModel):
    order_status: OrderStatus


# Payment Models
class PaymentIntent(BaseModel):
    order_id: str
    amount: float
    currency: str = "USD"


class PaymentConfirmation(BaseModel):
    payment_id: str
    status: PaymentStatus
    transaction_id: Optional[str] = None


# Invoice Models
class Invoice(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    order_id: str
    user_id: str
    venue_id: str
    invoice_number: str
    items: List[CartItem]
    subtotal: float
    tax: float
    total_amount: float
    payment_method: str
    payment_status: PaymentStatus
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


# Notification Models
class Notification(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    user_id: str
    type: NotificationType
    title: str
    message: str
    is_read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


# Venue Models
class VenueType(str, Enum):
    RESTAURANT = "restaurant"
    CAFE = "cafe"
    CLOUD_KITCHEN = "cloud_kitchen"


class ServiceArea(BaseModel):
    city: str
    postal_codes: List[str] = []


class OperatingHours(BaseModel):
    day: str
    open_time: str
    close_time: str
    is_open: bool = True


class Venue(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    name: str
    type: VenueType
    description: Optional[str] = None
    address: str
    city: str
    phone: str
    email: Optional[EmailStr] = None
    service_areas: List[ServiceArea] = []
    supported_order_modes: List[OrderMode] = []
    operating_hours: List[OperatingHours] = []
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class VenueCreate(BaseModel):
    name: str
    type: VenueType
    description: Optional[str] = None
    address: str
    city: str
    phone: str
    email: Optional[EmailStr] = None
    service_areas: List[ServiceArea] = []
    supported_order_modes: List[OrderMode] = []
    operating_hours: List[OperatingHours] = []


# Restaurant Profile Models
class RestaurantProfile(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    venue_id: str
    branch_name: Optional[str] = None
    manager_name: Optional[str] = None
    manager_email: Optional[EmailStr] = None
    manager_phone: Optional[str] = None
    tax_rate: float = 0.0
    currency: str = "USD"
    logo_url: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class RestaurantProfileUpdate(BaseModel):
    branch_name: Optional[str] = None
    manager_name: Optional[str] = None
    manager_email: Optional[EmailStr] = None
    manager_phone: Optional[str] = None
    tax_rate: Optional[float] = None
    currency: Optional[str] = None
    logo_url: Optional[str] = None


# Dashboard Models
class DashboardStats(BaseModel):
    total_orders_today: int
    total_revenue_today: float
    active_orders: int
    total_menu_items: int
    pending_orders: int
    completed_orders_today: int
