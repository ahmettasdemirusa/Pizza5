from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import jwt
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
from passlib.context import CryptContext
import bcrypt
from geopy.distance import geodesic
import re

# Load environment variables
ROOT_DIR = Path(__file__).parent
from dotenv import load_dotenv
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'pizza_db')]

# Create the main app
app = FastAPI(title="NY Pizza Woodstock API", version="1.0.0")
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')
ALGORITHM = "HS256"

# Business Info
BUSINESS_ADDRESS = "10214 Hickory Flat Hwy, Woodstock, GA 30188"
BUSINESS_COORDS = (34.1014, -84.5191)  # Woodstock, GA coordinates

# ==================== MODELS ====================

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    first_name: str
    last_name: str
    phone: str
    is_admin: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Address(BaseModel):
    street: str
    city: str
    state: str
    zip_code: str
    phone: Optional[str] = None

class PizzaSize(BaseModel):
    name: str  # Small, Medium, XL
    base_price: float

class Pizza(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    category: str  # "classic", "specialty", "custom"
    image_url: str
    sizes: Dict[str, float]  # {"Small": 12.99, "Medium": 15.99, "XL": 18.99}
    toppings: List[str] = []
    is_available: bool = True

class MenuItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    category: str
    price: float
    image_url: str
    is_available: bool = True

class CartItem(BaseModel):
    item_id: str
    item_type: str  # "pizza", "menu_item"
    name: str
    size: Optional[str] = None  # For pizzas
    toppings: List[str] = []  # For custom pizzas
    quantity: int
    price: float
    special_instructions: Optional[str] = None

class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    items: List[CartItem]
    delivery_address: Optional[Address] = None
    order_type: str  # "delivery", "pickup"
    payment_method: str  # "cash", "online"
    subtotal: float
    delivery_fee: float = 0.0
    tax: float
    total: float
    status: str = "pending"  # pending, confirmed, preparing, ready, delivered, cancelled
    created_at: datetime = Field(default_factory=datetime.utcnow)
    estimated_delivery: Optional[datetime] = None
    special_instructions: Optional[str] = None

# ==================== AUTH FUNCTIONS ====================

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        user = await db.users.find_one({"email": email})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return User(**user)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

# ==================== UTILITY FUNCTIONS ====================

def calculate_delivery_fee(delivery_address: str) -> tuple:
    """Calculate delivery fee based on distance from business"""
    # For demo, we'll use a simple distance calculation
    # In production, you'd use proper geocoding
    base_fee = 4.00
    max_distance = 9  # miles
    
    # Simple distance estimation (in real app, use proper geocoding)
    # For now, return base fee for all addresses in Woodstock area
    distance = 3  # Assume 3 miles for demo
    
    if distance <= 5:
        return base_fee, True, distance
    elif distance <= max_distance:
        return base_fee + (distance - 5) * 2, True, distance
    else:
        return 0, False, distance  # Outside delivery area

# ==================== ROUTES ====================

@api_router.get("/")
async def root():
    return {"message": "NY Pizza Woodstock API", "status": "operational"}

# ==================== AUTH ROUTES ====================

@api_router.post("/auth/register")
async def register_user(user_data: UserRegister):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password and create user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=user_data.phone
    )
    
    user_doc = user.dict()
    user_doc["password"] = hashed_password
    
    await db.users.insert_one(user_doc)
    
    # Create access token
    access_token = create_access_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@api_router.post("/auth/login")
async def login_user(user_data: UserLogin):
    user = await db.users.find_one({"email": user_data.email})
    if not user or not verify_password(user_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token = create_access_token(data={"sub": user["email"]})
    
    user_obj = User(**user)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_obj
    }

@api_router.get("/auth/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

# ==================== MENU ROUTES ====================

@api_router.get("/menu/pizzas")
async def get_pizzas():
    pizzas = await db.pizzas.find({"is_available": True}).to_list(100)
    return pizzas

@api_router.get("/menu/items")
async def get_menu_items():
    items = await db.menu_items.find({"is_available": True}).to_list(100)
    return items

@api_router.get("/menu/categories")
async def get_categories():
    return {
        "pizza_categories": ["classic", "specialty"],
        "other_categories": ["pasta", "calzone", "stromboli", "appetizers", "salads", "desserts", "wings"]
    }

# ==================== ORDER ROUTES ====================

@api_router.post("/orders")
async def create_order(order_data: Order, current_user: User = Depends(get_current_user)):
    order_data.user_id = current_user.id
    
    # Calculate delivery fee if delivery order
    if order_data.order_type == "delivery" and order_data.delivery_address:
        address_str = f"{order_data.delivery_address.street}, {order_data.delivery_address.city}, {order_data.delivery_address.state}"
        delivery_fee, can_deliver, distance = calculate_delivery_fee(address_str)
        
        if not can_deliver:
            raise HTTPException(status_code=400, detail="Address outside delivery area")
        
        order_data.delivery_fee = delivery_fee
    
    # Calculate tax (8.5% for GA)
    tax_rate = 0.085
    order_data.tax = round(order_data.subtotal * tax_rate, 2)
    order_data.total = order_data.subtotal + order_data.delivery_fee + order_data.tax
    
    # Set estimated delivery time
    if order_data.order_type == "delivery":
        order_data.estimated_delivery = datetime.utcnow() + timedelta(minutes=45)
    else:
        order_data.estimated_delivery = datetime.utcnow() + timedelta(minutes=25)
    
    order_doc = order_data.dict()
    await db.orders.insert_one(order_doc)
    
    return order_data

@api_router.get("/orders/my-orders")
async def get_user_orders(current_user: User = Depends(get_current_user)):
    orders = await db.orders.find({"user_id": current_user.id}).sort("created_at", -1).to_list(50)
    return orders

@api_router.get("/orders/{order_id}")
async def get_order(order_id: str, current_user: User = Depends(get_current_user)):
    order = await db.orders.find_one({"id": order_id, "user_id": current_user.id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

# ==================== ADMIN ROUTES ====================

@api_router.get("/admin/orders")
async def get_all_orders(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    orders = await db.orders.find().sort("created_at", -1).to_list(100)
    return orders

@api_router.put("/admin/orders/{order_id}/status")
async def update_order_status(order_id: str, status: str, current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    valid_statuses = ["pending", "confirmed", "preparing", "ready", "delivered", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    result = await db.orders.update_one(
        {"id": order_id},
        {"$set": {"status": status}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {"message": "Order status updated"}

@api_router.post("/admin/pizzas")
async def create_pizza(pizza: Pizza, current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    pizza_doc = pizza.dict()
    await db.pizzas.insert_one(pizza_doc)
    return pizza

@api_router.post("/admin/menu-items")
async def create_menu_item(item: MenuItem, current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    item_doc = item.dict()
    await db.menu_items.insert_one(item_doc)
    return item

# Include the router in the main app
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

# Initialize sample data on startup
@app.on_event("startup")
async def startup_event():
    logger.info("Starting NY Pizza Woodstock API...")
    
    # Check if data already exists
    existing_pizzas = await db.pizzas.count_documents({})
    if existing_pizzas == 0:
        await initialize_sample_data()

async def initialize_sample_data():
    """Initialize the database with NY Pizza Woodstock menu data"""
    
    # Sample Pizzas
    pizzas = [
        {
            "id": str(uuid.uuid4()),
            "name": "NY Cheese Pizza",
            "description": "Classic New York style pizza with mozzarella cheese",
            "category": "classic",
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Cheese-Pizza-1-600x400.jpg",
            "sizes": {"Small": 12.99, "Medium": 15.99, "XL": 18.99},
            "toppings": [],
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Buffalo Chicken Pizza",
            "description": "Spicy buffalo chicken with ranch dressing and mozzarella",
            "category": "specialty",
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2019/11/Buffalo_Pizza-scaled-2-600x338.jpg",
            "sizes": {"Small": 16.99, "Medium": 19.99, "XL": 23.99},
            "toppings": ["Buffalo Chicken", "Ranch", "Mozzarella"],
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Steak & Cheese Pizza",
            "description": "Philly steak with cheese and peppers",
            "category": "specialty",
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2019/11/Steak_and_Cheese-scaled-1-600x338.jpg",
            "sizes": {"Small": 17.99, "Medium": 20.99, "XL": 24.99},
            "toppings": ["Philly Steak", "Cheese", "Peppers"],
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Deluxe Pizza",
            "description": "Loaded with pepperoni, sausage, peppers, mushrooms and onions",
            "category": "specialty",
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Deluxe_Pizza-scaled-1-600x338.jpg",
            "sizes": {"Small": 18.99, "Medium": 22.99, "XL": 26.99},
            "toppings": ["Pepperoni", "Sausage", "Peppers", "Mushrooms", "Onions"],
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Hawaiian Pizza",
            "description": "Ham and pineapple with mozzarella cheese",
            "category": "specialty",
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Hawaiian_Pizza-scaled-1-600x338.jpg",
            "sizes": {"Small": 16.99, "Medium": 19.99, "XL": 23.99},
            "toppings": ["Ham", "Pineapple", "Mozzarella"],
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "BBQ Chicken Pizza",
            "description": "Grilled chicken with BBQ sauce and red onions",
            "category": "specialty",
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/BBQ_Pizza-scaled-1-600x338.jpg",
            "sizes": {"Small": 17.99, "Medium": 20.99, "XL": 24.99},
            "toppings": ["BBQ Chicken", "BBQ Sauce", "Red Onions"],
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Meat Lovers Pizza",
            "description": "Pepperoni, sausage, ham, and meatballs",
            "category": "specialty",
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Meat_Lovers-scaled-2-600x338.jpg",
            "sizes": {"Small": 19.99, "Medium": 23.99, "XL": 27.99},
            "toppings": ["Pepperoni", "Sausage", "Ham", "Meatballs"],
            "is_available": True
        }
    ]
    
    # Sample Menu Items
    menu_items = [
        {
            "id": str(uuid.uuid4()),
            "name": "Homemade Meat Lasagna",
            "description": "Traditional meat lasagna with ricotta and mozzarella",
            "category": "pasta",
            "price": 14.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/meat-lasagne.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Cheese Calzone",
            "description": "Folded pizza dough stuffed with ricotta and mozzarella",
            "category": "calzone",
            "price": 11.75,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Calzone-scaled-1.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Pepperoni Calzone",
            "description": "Calzone with pepperoni, ricotta and mozzarella",
            "category": "calzone",
            "price": 12.75,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Calzone-scaled-1.jpg",
            "is_available": True
        }
    ]
    
    # Insert data
    await db.pizzas.insert_many(pizzas)
    await db.menu_items.insert_many(menu_items)
    
    # Create admin user
    admin_user = {
        "id": str(uuid.uuid4()),
        "email": "admin@nypizzawoodstock.com",
        "password": get_password_hash("admin123"),
        "first_name": "Admin",
        "last_name": "User",
        "phone": "(470) 545-0095",
        "is_admin": True,
        "created_at": datetime.utcnow()
    }
    
    await db.users.insert_one(admin_user)
    
    logger.info("Sample data initialized successfully!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)