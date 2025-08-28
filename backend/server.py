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
    # Convert ObjectId to string for JSON serialization
    for pizza in pizzas:
        if '_id' in pizza:
            del pizza['_id']
    return pizzas

@api_router.get("/menu/items")
async def get_menu_items():
    items = await db.menu_items.find({"is_available": True}).to_list(100)
    # Convert ObjectId to string for JSON serialization
    for item in items:
        if '_id' in item:
            del item['_id']
    return items

@api_router.get("/menu/categories")
async def get_categories():
    return {
        "pizza_categories": ["classic", "specialty"],
        "other_categories": ["pasta", "calzone", "stromboli", "appetizers", "salads", "desserts", "wings", "burgers", "hot_subs", "cold_subs", "gyros", "sides", "beverages", "slice"]
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
    # Convert ObjectId to string for JSON serialization
    for order in orders:
        if '_id' in order:
            del order['_id']
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
    """Initialize the database with NY Pizza Woodstock complete menu data"""
    
    # Complete Pizzas List
    pizzas = [
        # Classic Pizzas
        {
            "id": str(uuid.uuid4()),
            "name": "NY Cheese Pizza",
            "description": "Classic New York style pizza with mozzarella cheese",
            "category": "classic",
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Cheese-Pizza-1-600x400.jpg",
            "sizes": {"Medium": 13.95, "Large": 15.95, "Xlarge": 17.95},
            "toppings": [],
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Sicilian Pizza",
            "description": "Extra Large 18″ thick crust Sicilian style pizza",
            "category": "classic",
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Sicilian-1-600x450.jpg",
            "sizes": {"Extra Large 18\"": 22.95},
            "toppings": [],
            "is_available": True
        },
        # Specialty Pizzas
        {
            "id": str(uuid.uuid4()),
            "name": "Buffalo Chicken Pizza",
            "description": "Chicken, buffalo sauce & cheddar cheese",
            "category": "specialty",
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2019/11/Buffalo_Pizza-scaled-2-600x338.jpg",
            "sizes": {"Medium": 18.95, "Large": 20.95, "Xlarge": 22.95},
            "toppings": ["Buffalo Chicken", "Buffalo Sauce", "Cheddar Cheese"],
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Steak & Cheese Pizza",
            "description": "Philly steak with cheese and peppers",
            "category": "specialty",
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2019/11/Steak_and_Cheese-scaled-1-600x338.jpg",
            "sizes": {"Medium": 18.95, "Large": 20.95, "Xlarge": 22.95},
            "toppings": ["Philly Steak", "Cheese", "Peppers"],
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Deluxe Pizza",
            "description": "Loaded with pepperoni, sausage, peppers, mushrooms and onions",
            "category": "specialty",
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Deluxe_Pizza-scaled-1-600x338.jpg",
            "sizes": {"Medium": 19.95, "Large": 21.95, "Xlarge": 23.95},
            "toppings": ["Pepperoni", "Sausage", "Peppers", "Mushrooms", "Onions"],
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Hawaiian Pizza",
            "description": "Ham and pineapple with mozzarella cheese",
            "category": "specialty",
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Hawaiian_Pizza-scaled-1-600x338.jpg",
            "sizes": {"Medium": 17.95, "Large": 19.95, "Xlarge": 21.95},
            "toppings": ["Ham", "Pineapple", "Mozzarella"],
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "BBQ Chicken Pizza",
            "description": "Grilled chicken with BBQ sauce and red onions",
            "category": "specialty",
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/BBQ_Pizza-scaled-1-600x338.jpg",
            "sizes": {"Medium": 18.95, "Large": 20.95, "Xlarge": 22.95},
            "toppings": ["BBQ Chicken", "BBQ Sauce", "Red Onions"],
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Meat Lovers Pizza",
            "description": "Pepperoni, ham & bacon",
            "category": "specialty",
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Meat_Lovers-scaled-2-600x338.jpg",
            "sizes": {"Medium": 20.95, "Large": 22.95, "Xlarge": 24.95},
            "toppings": ["Pepperoni", "Ham", "Bacon"],
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "NY White Pizza",
            "description": "White sauce with ricotta and mozzarella cheese",
            "category": "specialty",
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/NY_White_Pizza-scaled-1-600x338.jpg",
            "sizes": {"Medium": 17.95, "Large": 19.95, "Xlarge": 21.95},
            "toppings": ["Ricotta", "Mozzarella", "White Sauce"],
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Roma Spinach Pizza",
            "description": "Fresh spinach with garlic and olive oil",
            "category": "specialty",
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Roma_Spinach-scaled-1-600x338.jpg",
            "sizes": {"Medium": 18.95, "Large": 20.95, "Xlarge": 22.95},
            "toppings": ["Spinach", "Garlic", "Olive Oil"],
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Primavera Pizza",
            "description": "Fresh vegetables with mozzarella cheese",
            "category": "specialty",
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Primevera_Pizza-scaled-1.jpg",
            "sizes": {"Medium": 18.95, "Large": 20.95, "Xlarge": 22.95},
            "toppings": ["Fresh Vegetables", "Mozzarella"],
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Italian Chicken Pizza",
            "description": "Grilled chicken with Italian herbs and spices",
            "category": "specialty",
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Italian_Chicken-scaled-1-600x338.jpg",
            "sizes": {"Medium": 18.95, "Large": 20.95, "Xlarge": 22.95},
            "toppings": ["Grilled Chicken", "Italian Herbs"],
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "The Greek Pizza",
            "description": "Feta cheese, olives, tomatoes and oregano",
            "category": "specialty",
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Greek_Pizza-scaled-1.jpg",
            "sizes": {"Medium": 19.95, "Large": 21.95, "Xlarge": 23.95},
            "toppings": ["Feta Cheese", "Olives", "Tomatoes", "Oregano"],
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Lasagna Pizza",
            "description": "Pizza topped like a lasagna with ricotta and meat sauce",
            "category": "specialty",
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Lasgna_Pizza-scaled-1-600x338.jpg",
            "sizes": {"Medium": 19.95, "Large": 21.95, "Xlarge": 23.95},
            "toppings": ["Ricotta", "Meat Sauce", "Mozzarella"],
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Eggplant Parmigiana Pizza",
            "description": "Breaded eggplant with marinara and mozzarella",
            "category": "specialty",
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Eggplant_Pizza-2048x1152-1-600x338.jpg",
            "sizes": {"Medium": 18.95, "Large": 20.95, "Xlarge": 22.95},
            "toppings": ["Eggplant", "Marinara", "Mozzarella"],
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Stuffed Meat Pizza",
            "description": "Double crust pizza stuffed with meat and cheese",
            "category": "specialty",
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Stuffed_Meat-scaled-2-600x338.jpg",
            "sizes": {"Medium": 22.95, "Large": 24.95, "Xlarge": 26.95},
            "toppings": ["Meat", "Cheese", "Double Crust"],
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Stuffed Veggie Pizza",
            "description": "Double crust pizza stuffed with vegetables and cheese",
            "category": "specialty",
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Stuffed_Meat-scaled-2-600x338.jpg",
            "sizes": {"Medium": 21.95, "Large": 23.95, "Xlarge": 25.95},
            "toppings": ["Vegetables", "Cheese", "Double Crust"],
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Stuffed Chicken Pizza",
            "description": "Double crust pizza stuffed with chicken and cheese",
            "category": "specialty",
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Stuffed_Meat-scaled-2-600x338.jpg",
            "sizes": {"Medium": 22.95, "Large": 24.95, "Xlarge": 26.95},
            "toppings": ["Chicken", "Cheese", "Double Crust"],
            "is_available": True
        }
    ]
    
    # Complete Menu Items List
    menu_items = [
        # PASTA DISHES
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
            "name": "Homemade Veggie Lasagna",
            "description": "Vegetarian lasagna with fresh vegetables",
            "category": "pasta",
            "price": 13.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/veggie-lasagna-600x450.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Homemade Baked Ziti",
            "description": "Classic baked ziti with marinara and mozzarella",
            "category": "pasta",
            "price": 12.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/baked-ziti-600x450.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Baked Ziti Sicilian",
            "description": "Baked ziti Sicilian style with ricotta",
            "category": "pasta",
            "price": 12.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Baked-Ziti-Sicilian-600x450.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Baked Ziti Anna Maria",
            "description": "Special baked ziti with meat and ricotta",
            "category": "pasta",
            "price": 14.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Baked-Ziti-Anna-Maria-600x450.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Baked Ziti Blanco",
            "description": "White sauce baked ziti with cheese",
            "category": "pasta",
            "price": 12.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Baked-Ziti-Blanco-1-600x450.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Baked Spaghetti",
            "description": "Oven-baked spaghetti with cheese",
            "category": "pasta",
            "price": 12.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Baked-Spaghetti-1-600x400.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Spaghetti or Ziti Marinara",
            "description": "Classic marinara sauce with your choice of pasta",
            "category": "pasta",
            "price": 12.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Spaghetti-or-Ziti-Marinara-1-600x450.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Spaghetti or Ziti Meat Sauce",
            "description": "Rich meat sauce with your choice of pasta",
            "category": "pasta",
            "price": 14.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Spaghetti-or-Ziti-Meat-Sauce-1-600x450.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Spaghetti Meatball or Sausage",
            "description": "Spaghetti with homemade meatballs or sausage",
            "category": "pasta",
            "price": 14.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/spaghetti-meatballs.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Ziti Meatball or Sausage",
            "description": "Ziti with homemade meatballs or sausage",
            "category": "pasta",
            "price": 14.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Ziti-Meatball-or-Sausage-600x450.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Chicken Parmigiana Pasta",
            "description": "Breaded chicken cutlet with pasta",
            "category": "pasta",
            "price": 15.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Chicken-Parmigiana-Pasta-600x450.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Eggplant Parmigiana Pasta",
            "description": "Breaded eggplant with marinara and pasta",
            "category": "pasta",
            "price": 14.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/eGGPLANT-PARMIGIANA-600x400.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Eggplant Rollantini Pasta",
            "description": "Eggplant rolled with ricotta and herbs",
            "category": "pasta",
            "price": 14.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Eggplant-Rollatini.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Stuffed Shells",
            "description": "Large shells stuffed with ricotta cheese",
            "category": "pasta",
            "price": 14.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/stuffed-shells-1.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Ravioli (Cheese, Meat, or Spinach)",
            "description": "Homemade ravioli with your choice of filling",
            "category": "pasta",
            "price": 12.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/ravioli-with-garlic-red-pepper-olive-oil-sauce-Barbara-Bakes.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Manicotti",
            "description": "Pasta tubes stuffed with ricotta cheese",
            "category": "pasta",
            "price": 12.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/manicotti-2-600x401.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Penne Alla Vodka",
            "description": "Penne pasta in creamy vodka sauce",
            "category": "pasta",
            "price": 14.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/penne-alla-vodka-10-e1654656600244.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Fettuccine Alfredo",
            "description": "Classic fettuccine in creamy Alfredo sauce",
            "category": "pasta",
            "price": 14.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/fettucine-alfredo-scaled-1-600x900.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Fettuccine Alfredo w/Chicken",
            "description": "Fettuccine Alfredo with grilled chicken",
            "category": "pasta",
            "price": 18.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/shrimp-alfredo-IG-600x600.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Fettuccine Alfredo w/Shrimp",
            "description": "Fettuccine Alfredo with grilled shrimp",
            "category": "pasta",
            "price": 18.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/shrimp-alfredo-IG-600x600.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Chicken Francese",
            "description": "Chicken in white wine and lemon sauce",
            "category": "pasta",
            "price": 17.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/chicken-francese-recipe-1-600x900.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Chicken Marsala",
            "description": "Chicken in Marsala wine sauce with mushrooms",
            "category": "pasta",
            "price": 18.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Marsala.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Shrimp Scampi",
            "description": "Shrimp in garlic and white wine sauce",
            "category": "pasta",
            "price": 19.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/easy-shrimp-scampi-featured.jpg",
            "is_available": True
        },
        
        # CALZONES
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
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Meatball Calzone",
            "description": "Calzone with meatballs, ricotta and mozzarella",
            "category": "calzone",
            "price": 12.75,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Calzone-scaled-1.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Ham Calzone",
            "description": "Calzone with ham, ricotta and mozzarella",
            "category": "calzone",
            "price": 12.75,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Calzone-scaled-1.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Spinach Calzone",
            "description": "Calzone with spinach, ricotta and mozzarella",
            "category": "calzone",
            "price": 12.75,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Calzone-scaled-1.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Create Your Own Calzone",
            "description": "Build your own calzone with your favorite toppings",
            "category": "calzone",
            "price": 12.75,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Calzone-scaled-1.jpg",
            "is_available": True
        },
        # APPETIZERS (8 items)
        {
            "id": str(uuid.uuid4()),
            "name": "Bread Sticks",
            "description": "Fresh baked bread sticks with marinara sauce",
            "category": "appetizers",
            "price": 9.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Bread-Sticks-600x400-1-300x300.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Chicken Strips",
            "description": "Crispy chicken strips with fries",
            "category": "appetizers",
            "price": 9.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Chicken_Tenders_and_Fries-2048x1152-1-300x300.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Fried Pickles",
            "description": "Golden fried pickle spears with ranch",
            "category": "appetizers",
            "price": 7.50,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Mozzarella_Sticks-1-2048x1152-1-300x300.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Fried Ravioli",
            "description": "Crispy fried cheese ravioli with marinara",
            "category": "appetizers",
            "price": 7.50,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Cheese_Ravioli-scaled-1-300x300.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "I ❤️ NY Fries",
            "description": "Our special seasoned fries",
            "category": "appetizers",
            "price": 7.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Ilovenyfries-600x400-1-300x300.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Jalapeno Poppers",
            "description": "Cream cheese stuffed jalapenos",
            "category": "appetizers",
            "price": 7.50,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Jalapeno_Poppers-1-scaled-1-300x300.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Mozzarella Sticks",
            "description": "Golden fried mozzarella with marinara",
            "category": "appetizers",
            "price": 7.50,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Mozzarella_Sticks-1-2048x1152-1-300x300.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Zuke Shoots",
            "description": "Crispy fried zucchini sticks",
            "category": "appetizers",
            "price": 7.50,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Zucchini_Sticks-1-scaled-1-300x300.jpg",
            "is_available": True
        },
        
        # WINGS (4 flavors with multiple sizes)
        {
            "id": str(uuid.uuid4()),
            "name": "BBQ Wings",
            "description": "With ranch or blue cheese",
            "category": "wings",
            "price": 8.95,  # 6pc price (multiple sizes available)
            "sizes": {"6pc": 8.95, "12pc": 15.95, "20pc": 26.95, "50pc": 59.95},
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/BBQ_Wings-scaled-1-300x300.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Buffalo Wings (Medium, Mild or Hot)",
            "description": "Classic buffalo wings with ranch or blue cheese",
            "category": "wings",
            "price": 8.95,
            "sizes": {"6pc": 8.95, "12pc": 15.95, "20pc": 26.95, "50pc": 59.95},
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Medium_Wings-scaled-2-300x300.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Lemon Pepper Wings",
            "description": "Seasoned with lemon pepper spice",
            "category": "wings",
            "price": 8.95,
            "sizes": {"6pc": 8.95, "12pc": 15.95, "20pc": 26.95, "50pc": 59.95},
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Sweet_Chilli_Wings-scaled-1-300x300.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Sweet Chili Wings",
            "description": "Sweet and spicy chili glaze",
            "category": "wings",
            "price": 8.95,
            "sizes": {"6pc": 8.95, "12pc": 15.95, "20pc": 26.95, "50pc": 59.95},
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Sweet_Chilli_Wings-scaled-1-300x300.jpg",
            "is_available": True
        },
        
        # SALADS (6 items)
        {
            "id": str(uuid.uuid4()),
            "name": "Antipasto Salad",
            "description": "Mixed greens with Italian meats and cheese",
            "category": "salads",
            "price": 12.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Antipasto_Salad-2-2048x1152-1-300x300.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Chef Salad",
            "description": "Mixed greens with turkey, ham and cheese",
            "category": "salads",
            "price": 12.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Antipasto_Salad-2-2048x1152-1-300x300.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Garden Salad",
            "description": "Fresh mixed greens with vegetables",
            "category": "salads",
            "price": 9.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Garden_Salad-2048x1152-1-300x300.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Greek Salad",
            "description": "Mixed greens with feta, olives and Greek dressing",
            "category": "salads",
            "price": 11.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Greek_Salad-1-2048x1152-1-300x300.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Grilled Chicken Salad",
            "description": "Mixed greens topped with grilled chicken",
            "category": "salads",
            "price": 13.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Chicken_Salad-2048x1152-1-300x300.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Gyro Salad",
            "description": "Mixed greens with gyro meat and tzatziki",
            "category": "salads",
            "price": 14.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/GyrosGreekSalad-600x400-1-300x300.jpg",
            "is_available": True
        },
        
        # BURGERS (3 items)
        {
            "id": str(uuid.uuid4()),
            "name": "Hamburger",
            "description": "Classic beef burger with lettuce and tomato",
            "category": "burgers",
            "price": 11.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Burger_and_Fries-1-2048x1152-1-300x300.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Cheeseburger",
            "description": "Beef burger with cheese, lettuce and tomato",
            "category": "burgers",
            "price": 12.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Burger_and_Fries-1-2048x1152-1-300x300.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Double Burger",
            "description": "Double beef patty with cheese and fixings",
            "category": "burgers",
            "price": 15.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Burger_and_Fries-1-2048x1152-1-300x300.jpg",
            "is_available": True
        },
        
        # STROMBOLI (2 items)
        {
            "id": str(uuid.uuid4()),
            "name": "Cheese Steak Stromboli",
            "description": "Rolled pizza dough with steak and cheese",
            "category": "stromboli",
            "price": 12.75,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Stromboli-2-scaled-1-600x338.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Italian Meatball Stromboli",
            "description": "Rolled pizza dough with meatballs and cheese",
            "category": "stromboli",
            "price": 12.75,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Stromboli-2-scaled-1-600x338.jpg",
            "is_available": True
        },
        
        # HOT SUBS (8 items total)
        {
            "id": str(uuid.uuid4()),
            "name": "Chicken Parmigiana Sub",
            "description": "Breaded chicken with marinara and mozzarella",
            "category": "hot_subs",
            "price": 12.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Chicken-Parmigiana-Pasta-600x450.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Meatball Sub",
            "description": "Homemade meatballs with marinara and cheese",
            "category": "hot_subs",
            "price": 11.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/spaghetti-meatballs.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Sausage Sub",
            "description": "Italian sausage with peppers and onions",
            "category": "hot_subs",
            "price": 11.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Stromboli-2-scaled-1-600x338.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Philly Cheese Steak",
            "description": "Sliced steak with peppers, onions and cheese",
            "category": "hot_subs",
            "price": 12.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2019/11/Steak_and_Cheese-scaled-1-600x338.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Chicken Cheese Steak",
            "description": "Grilled chicken with peppers, onions and cheese",
            "category": "hot_subs",
            "price": 12.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Italian_Chicken-scaled-1-600x338.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Eggplant Parmigiana Sub",
            "description": "Breaded eggplant with marinara and cheese",
            "category": "hot_subs",
            "price": 11.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/eGGPLANT-PARMIGIANA-600x400.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Sausage & Peppers Sub",
            "description": "Italian sausage with bell peppers",
            "category": "hot_subs",
            "price": 12.50,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Stromboli-2-scaled-1-600x338.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Buffalo Chicken Sub",
            "description": "Buffalo chicken with ranch and lettuce",
            "category": "hot_subs",
            "price": 12.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2019/11/Buffalo_Pizza-scaled-2-600x338.jpg",
            "is_available": True
        },

        # COLD SUBS (8 items total)
        {
            "id": str(uuid.uuid4()),
            "name": "Italian Sub",
            "description": "Ham, salami, capicola with cheese and vegetables",
            "category": "cold_subs",
            "price": 11.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Hot-Sub-Sandwiches-3-pmg-cs-150x150.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Ham & Cheese Sub",
            "description": "Sliced ham with provolone cheese",
            "category": "cold_subs",
            "price": 10.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Hot-Sub-Sandwiches-3-pmg-cs-150x150.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Turkey Sub",
            "description": "Sliced turkey with cheese and vegetables",
            "category": "cold_subs",
            "price": 10.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Hot-Sub-Sandwiches-3-pmg-cs-150x150.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Tuna Sub",
            "description": "Tuna salad with lettuce and tomato",
            "category": "cold_subs",
            "price": 10.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Hot-Sub-Sandwiches-3-pmg-cs-150x150.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Roast Beef Sub",
            "description": "Sliced roast beef with cheese",
            "category": "cold_subs",
            "price": 11.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Hot-Sub-Sandwiches-3-pmg-cs-150x150.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Veggie Sub",
            "description": "Fresh vegetables with cheese",
            "category": "cold_subs",
            "price": 9.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Hot-Sub-Sandwiches-3-pmg-cs-150x150.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Club Sub",
            "description": "Turkey, ham, bacon with cheese",
            "category": "cold_subs",
            "price": 12.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Hot-Sub-Sandwiches-3-pmg-cs-150x150.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Chicken Salad Sub",
            "description": "Homemade chicken salad with lettuce",
            "category": "cold_subs",
            "price": 11.50,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Hot-Sub-Sandwiches-3-pmg-cs-150x150.png",
            "is_available": True
        },

        # GYROS (6 items total)
        {
            "id": str(uuid.uuid4()),
            "name": "Gyro Platter",
            "description": "Gyro meat with tzatziki, pita and fries",
            "category": "gyros",
            "price": 13.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/gyross-150x150.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Chicken Gyro",
            "description": "Grilled chicken with tzatziki and vegetables",
            "category": "gyros",
            "price": 12.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/gyross-150x150.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Gyro Sandwich",
            "description": "Traditional gyro meat in pita bread",
            "category": "gyros",
            "price": 9.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/gyross-150x150.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Chicken Gyro Sandwich",
            "description": "Grilled chicken in pita with tzatziki",
            "category": "gyros",
            "price": 9.50,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/gyross-150x150.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Lamb Gyro",
            "description": "Seasoned lamb with vegetables and tzatziki",
            "category": "gyros",
            "price": 11.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/gyross-150x150.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Gyro Combo",
            "description": "Gyro sandwich with fries and drink",
            "category": "gyros",
            "price": 14.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/gyross-150x150.png",
            "is_available": True
        },

        # SIDES (10 items total)
        {
            "id": str(uuid.uuid4()),
            "name": "French Fries",
            "description": "Golden crispy french fries",
            "category": "sides",
            "price": 4.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/sides-png-3-150x150.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Onion Rings",
            "description": "Beer battered onion rings",
            "category": "sides",
            "price": 5.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/sides-png-3-150x150.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Garlic Bread",
            "description": "Toasted bread with garlic butter",
            "category": "sides",
            "price": 3.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Bread-Sticks-600x400-1-300x300.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Garlic Knots",
            "description": "Fresh baked garlic knots",
            "category": "sides",
            "price": 4.50,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Bread-Sticks-600x400-1-300x300.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Marinara Sauce",
            "description": "Side of marinara dipping sauce",
            "category": "sides",
            "price": 1.50,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/sides-png-3-150x150.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Ranch Dressing",
            "description": "Side of ranch dressing",
            "category": "sides",
            "price": 1.50,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/sides-png-3-150x150.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Blue Cheese",
            "description": "Side of blue cheese dressing",
            "category": "sides",
            "price": 1.50,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/sides-png-3-150x150.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Sweet Potato Fries",
            "description": "Crispy sweet potato fries",
            "category": "sides",
            "price": 6.50,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/sides-png-3-150x150.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Side Salad",
            "description": "Small mixed green salad",
            "category": "sides",
            "price": 4.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Garden_Salad-2048x1152-1-300x300.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Caesar Side Salad",
            "description": "Small Caesar salad",
            "category": "sides",
            "price": 5.50,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Garden_Salad-2048x1152-1-300x300.jpg",
            "is_available": True
        },

        # BEVERAGES (12 items total)
        {
            "id": str(uuid.uuid4()),
            "name": "Coca Cola",
            "description": "Classic Coca Cola soft drink",
            "category": "beverages",
            "price": 2.95,
            "image_url": "https://via.placeholder.com/300x300/dc2626/white?text=Beverages",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Pepsi",
            "description": "Pepsi soft drink",
            "category": "beverages",
            "price": 2.95,
            "image_url": "https://via.placeholder.com/300x300/dc2626/white?text=Beverages",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Sprite",
            "description": "Lemon-lime soda",
            "category": "beverages",
            "price": 2.95,
            "image_url": "https://via.placeholder.com/300x300/dc2626/white?text=Beverages",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Orange Soda",
            "description": "Orange flavored soda",
            "category": "beverages",
            "price": 2.95,
            "image_url": "https://via.placeholder.com/300x300/dc2626/white?text=Beverages",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Dr Pepper",
            "description": "Classic Dr Pepper soda",
            "category": "beverages",
            "price": 2.95,
            "image_url": "https://via.placeholder.com/300x300/dc2626/white?text=Beverages",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Diet Coke",
            "description": "Diet Coca Cola",
            "category": "beverages",
            "price": 2.95,
            "image_url": "https://via.placeholder.com/300x300/dc2626/white?text=Beverages",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Water Bottle",
            "description": "Bottled water",
            "category": "beverages",
            "price": 1.95,
            "image_url": "https://via.placeholder.com/300x300/dc2626/white?text=Beverages",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Iced Tea",
            "description": "Fresh brewed iced tea",
            "category": "beverages",
            "price": 2.50,
            "image_url": "https://via.placeholder.com/300x300/dc2626/white?text=Beverages",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Lemonade",
            "description": "Fresh squeezed lemonade",
            "category": "beverages",
            "price": 2.95,
            "image_url": "https://via.placeholder.com/300x300/dc2626/white?text=Beverages",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Coffee",
            "description": "Hot brewed coffee",
            "category": "beverages",
            "price": 2.25,
            "image_url": "https://via.placeholder.com/300x300/dc2626/white?text=Beverages",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Hot Tea",
            "description": "Hot herbal tea selection",
            "category": "beverages",
            "price": 2.25,
            "image_url": "https://via.placeholder.com/300x300/dc2626/white?text=Beverages",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Apple Juice",
            "description": "Fresh apple juice",
            "category": "beverages",
            "price": 2.75,
            "image_url": "https://via.placeholder.com/300x300/dc2626/white?text=Beverages",
            "is_available": True
        },

        # DESSERTS (8 items total)
        {
            "id": str(uuid.uuid4()),
            "name": "Tiramisu",
            "description": "Classic Italian tiramisu dessert",
            "category": "desserts",
            "price": 6.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/dessert-png-1-150x150.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Cannoli",
            "description": "Sicilian cannoli with ricotta filling",
            "category": "desserts",
            "price": 4.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/dessert-png-1-150x150.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Cheesecake",
            "description": "New York style cheesecake",
            "category": "desserts",
            "price": 5.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/dessert-png-1-150x150.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Chocolate Cake",
            "description": "Rich chocolate layer cake",
            "category": "desserts",
            "price": 5.50,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/dessert-png-1-150x150.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Gelato",
            "description": "Italian gelato - vanilla or chocolate",
            "category": "desserts",
            "price": 4.50,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/dessert-png-1-150x150.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Zeppoli",
            "description": "Fried Italian doughnuts with powdered sugar",
            "category": "desserts",
            "price": 6.50,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/dessert-png-1-150x150.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Chocolate Cannoli",
            "description": "Chocolate dipped cannoli",
            "category": "desserts",
            "price": 5.50,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/dessert-png-1-150x150.png",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Spumoni",
            "description": "Traditional Italian ice cream",
            "category": "desserts",
            "price": 4.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/dessert-png-1-150x150.png",
            "is_available": True
        },

        # SLICE (6 items total)
        {
            "id": str(uuid.uuid4()),
            "name": "Cheese Slice",
            "description": "Single slice of NY cheese pizza",
            "category": "slice",
            "price": 3.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Cheese-Pizza-1-600x400.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Pepperoni Slice",
            "description": "Single slice of pepperoni pizza",
            "category": "slice",
            "price": 4.50,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Meat_Lovers-scaled-2-600x338.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Specialty Slice",
            "description": "Single slice of daily specialty pizza",
            "category": "slice",
            "price": 5.25,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2019/11/Buffalo_Pizza-scaled-2-600x338.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Sicilian Slice",
            "description": "Thick crust Sicilian pizza slice",
            "category": "slice",
            "price": 4.95,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/Sicilian-1-600x450.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "White Slice",
            "description": "White pizza slice with ricotta",
            "category": "slice",
            "price": 4.75,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2023/07/NY_White_Pizza-scaled-1-600x338.jpg",
            "is_available": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Buffalo Chicken Slice",
            "description": "Buffalo chicken pizza slice",
            "category": "slice",
            "price": 5.50,
            "image_url": "https://www.nypizzawoodstock.com/wp-content/uploads/2019/11/Buffalo_Pizza-scaled-2-600x338.jpg",
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
    
    logger.info("Complete NY Pizza Woodstock menu initialized successfully!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)