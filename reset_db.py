#!/usr/bin/env python3

import os
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

async def reset_database():
    # MongoDB connection
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ.get('DB_NAME', 'test_database')]
    
    print("Connecting to MongoDB...")
    
    try:
        # Delete all collections
        await db.pizzas.delete_many({})
        await db.menu_items.delete_many({})
        await db.users.delete_many({})
        
        print("✅ Database collections cleared successfully!")
        
        # Check counts
        pizza_count = await db.pizzas.count_documents({})
        menu_count = await db.menu_items.count_documents({})
        user_count = await db.users.count_documents({})
        
        print(f"Pizza count: {pizza_count}")
        print(f"Menu items count: {menu_count}")
        print(f"Users count: {user_count}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(reset_database())