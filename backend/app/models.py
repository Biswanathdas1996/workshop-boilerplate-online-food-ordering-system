from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


class UserRole(str, Enum):
    CUSTOMER = "customer"
    RESTAURANT_ADMIN = "restaurant_admin"
    STAFF = "staff"


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
    GLUTEN_FREE = "gluten_free"
    HALAL = "halal"
    KOSHER = "kosher"
    NONE = "none"


class NotificationType(str, Enum):
    ORDER_CONFIRMATION = "order_confirmation"
    ORDER_STATUS_UPDATE = "order_status_update"
    ORDER_CANCELLATION = "order_cancellation"
    PROMOTION = "promotion"


# User Models
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role: UserRole = UserRole.CUSTOMER


class UserRegister(UserBase):
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserInDB(UserBase):
    id: str = Field(alias="_id")
    hashed_password: str
    oauth_provider: Optional[str] = None
    oauth_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class UserResponse(UserBase):
    id: str = Field(alias="_id")
    created_at: datetime

    class Config:
        populate_by_name = True


# Category Models
class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    display_order: int = 0
    venue_id: str


class CategoryCreate(CategoryBase):
    pass


class CategoryInDB(CategoryBase):
    id: str = Field(alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


# Menu Item Models
class AddOn(BaseModel):
    name: str
    price: float


class SpiceLevel(str, Enum):
    NONE = "none"
    MILD = "mild"
    MEDIUM = "medium"
    HOT = "hot"
    EXTRA_HOT = "extra_hot"


class MenuItemBase(BaseModel):
    name: str
    description: str
    price: float
    category_id: str
    venue_id: str
    image_url: Optional[str] = None
    ingredients: List[str] = []
    dietary_preferences: List[DietaryPreference] = []
    add_ons: List[AddOn] = []
    spice_levels_available: List[SpiceLevel] = []
    is_available: bool = True


class MenuItemCreate(MenuItemBase):
    pass


class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category_id: Optional[str] = None
    image_url: Optional[str] = None
    ingredients: Optional[List[str]] = None
    dietary_preferences: Optional[List[DietaryPreference]] = None
    add_ons: Optional[List[AddOn]] = None
    spice_levels_available: Optional[List[SpiceLevel]] = None
    is_available: Optional[bool] = None


class MenuItemInDB(MenuItemBase):
    id: str = Field(alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


# Cart Models
class CartItemCustomization(BaseModel):
    add_ons: List[str] = []
    spice_level: Optional[SpiceLevel] = None
    special_instructions: Optional[str] = None


class CartItemBase(BaseModel):
    menu_item_id: str
    quantity: int = 1
    customization: Optional[CartItemCustomization] = None


class CartItem(CartItemBase):
    menu_item_name: str
    menu_item_price: float
    menu_item_image: Optional[str] = None


class CartBase(BaseModel):
    user_id: str
    venue_id: str
    items: List[CartItem] = []


class CartInDB(CartBase):
    id: str = Field(alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


# Order Models
class DeliveryDetails(BaseModel):
    address: str
    city: str
    postal_code: str
    phone: str
    delivery_instructions: Optional[str] = None


class OrderItemBase(BaseModel):
    menu_item_id: str
    menu_item_name: str
    menu_item_price: float
    quantity: int
    customization: Optional[CartItemCustomization] = None
    subtotal: float


class OrderBase(BaseModel):
    user_id: str
    venue_id: str
    items: List[OrderItemBase]
    order_mode: OrderMode
    delivery_details: Optional[DeliveryDetails] = None
    pickup_time: Optional[datetime] = None
    subtotal: float
    tax: float
    delivery_fee: float = 0.0
    total_amount: float
    payment_status: PaymentStatus = PaymentStatus.PENDING
    order_status: OrderStatus = OrderStatus.RECEIVED


class OrderCreate(BaseModel):
    venue_id: str
    order_mode: OrderMode
    delivery_details: Optional[DeliveryDetails] = None
    pickup_time: Optional[datetime] = None


class OrderInDB(OrderBase):
    id: str = Field(alias="_id")
    order_number: str
    payment_intent_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


# Invoice Models
class InvoiceBase(BaseModel):
    order_id: str
    order_number: str
    user_id: str
    venue_id: str
    invoice_date: datetime = Field(default_factory=datetime.utcnow)
    items: List[OrderItemBase]
    subtotal: float
    tax: float
    delivery_fee: float
    total_amount: float
    payment_method: str
    payment_status: PaymentStatus


class InvoiceInDB(InvoiceBase):
    id: str = Field(alias="_id")
    invoice_number: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


# Restaurant Profile Models
class OperatingHours(BaseModel):
    day: str
    open_time: str
    close_time: str
    is_closed: bool = False


class ServiceArea(BaseModel):
    city: str
    postal_codes: List[str] = []


class RestaurantProfileBase(BaseModel):
    venue_id: str
    branch_name: str
    address: str
    city: str
    postal_code: str
    phone: str
    email: EmailStr
    operating_hours: List[OperatingHours] = []
    service_areas: List[ServiceArea] = []
    supported_order_modes: List[OrderMode] = []
    min_order_amount: float = 0.0
    delivery_fee: float = 0.0


class RestaurantProfileCreate(RestaurantProfileBase):
    pass


class RestaurantProfileUpdate(BaseModel):
    branch_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    operating_hours: Optional[List[OperatingHours]] = None
    service_areas: Optional[List[ServiceArea]] = None
    supported_order_modes: Optional[List[OrderMode]] = None
    min_order_amount: Optional[float] = None
    delivery_fee: Optional[float] = None


class RestaurantProfileInDB(RestaurantProfileBase):
    id: str = Field(alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


# Venue Models
class VenueType(str, Enum):
    RESTAURANT = "restaurant"
    CAFE = "cafe"
    CLOUD_KITCHEN = "cloud_kitchen"


class VenueBase(BaseModel):
    name: str
    venue_type: VenueType
    description: Optional[str] = None
    logo_url: Optional[str] = None
    is_active: bool = True


class VenueCreate(VenueBase):
    pass


class VenueInDB(VenueBase):
    id: str = Field(alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


# Notification Models
class NotificationBase(BaseModel):
    user_id: str
    notification_type: NotificationType
    title: str
    message: str
    related_order_id: Optional[str] = None
    is_read: bool = False


class NotificationCreate(NotificationBase):
    pass


class NotificationInDB(NotificationBase):
    id: str = Field(alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


# Token Models
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[UserRole] = None
