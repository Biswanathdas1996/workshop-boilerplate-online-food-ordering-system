"""Seed script: inserts a venue, categories, and menu items into MongoDB."""
import os
from pathlib import Path
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env')

MONGODB_URI = os.getenv('MONGODB_URI')
if not MONGODB_URI:
    raise RuntimeError('MONGODB_URI not set in .env')

client = MongoClient(MONGODB_URI)
db = client.get_default_database()

VENUE_ID = ObjectId('676f9e0a0b5c8d001f123456')

# ── Venue ──────────────────────────────────────────────────────────────────
if not db.venues.find_one({'_id': VENUE_ID}):
    db.venues.insert_one({
        '_id': VENUE_ID,
        'name': 'The Food Hub',
        'description': 'A cozy place for delicious food',
        'address': '123 Main Street, Downtown',
        'phone': '+1-555-0100',
        'email': 'info@foodhub.com',
        'cuisine_types': ['American', 'Italian', 'Asian'],
        'is_active': True,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
    })
    print('Venue inserted.')
else:
    print('Venue already exists, skipping.')

venue_id_str = str(VENUE_ID)

# ── Categories ─────────────────────────────────────────────────────────────
category_defs = [
    {'name': 'Starters',    'description': 'Light bites to kick things off',  'display_order': 1},
    {'name': 'Main Course', 'description': 'Hearty dishes to satisfy hunger', 'display_order': 2},
    {'name': 'Pizzas',      'description': 'Stone-baked hand-tossed pizzas',  'display_order': 3},
    {'name': 'Burgers',     'description': 'Juicy gourmet burgers',            'display_order': 4},
    {'name': 'Desserts',    'description': 'Sweet treats to finish your meal','display_order': 5},
    {'name': 'Drinks',      'description': 'Refreshing beverages',            'display_order': 6},
]

cat_ids = {}
for cat_def in category_defs:
    existing = db.categories.find_one({'name': cat_def['name'], 'venue_id': venue_id_str})
    if existing:
        cat_ids[cat_def['name']] = str(existing['_id'])
        print(f"Category '{cat_def['name']}' already exists, skipping.")
    else:
        result = db.categories.insert_one({
            **cat_def,
            'venue_id': venue_id_str,
            'created_at': datetime.utcnow(),
        })
        cat_ids[cat_def['name']] = str(result.inserted_id)
        print(f"Category '{cat_def['name']}' inserted.")

# ── Menu Items ──────────────────────────────────────────────────────────────
menu_items = [
    # Starters
    {
        'name': 'Crispy Spring Rolls',
        'description': 'Golden fried spring rolls filled with vegetables and glass noodles, served with sweet chilli sauce.',
        'price': 7.99,
        'category': 'Starters',
        'image_url': 'https://images.unsplash.com/photo-1668236543090-82eba5ee5976?w=400',
        'ingredients': ['cabbage', 'carrots', 'glass noodles', 'mushrooms', 'spring roll wrappers'],
        'dietary_preferences': ['vegan'],
        'add_ons': [],
        'spice_levels_available': ['none', 'mild'],
    },
    {
        'name': 'Chicken Wings',
        'description': 'Crispy buffalo chicken wings tossed in tangy hot sauce, served with ranch dip.',
        'price': 10.99,
        'category': 'Starters',
        'image_url': 'https://images.unsplash.com/photo-1608039829572-78524f79c4c7?w=400',
        'ingredients': ['chicken wings', 'hot sauce', 'butter', 'ranch dressing'],
        'dietary_preferences': ['halal'],
        'add_ons': [{'name': 'Extra sauce', 'price': 0.50}],
        'spice_levels_available': ['mild', 'medium', 'hot', 'extra_hot'],
    },
    # Main Course
    {
        'name': 'Grilled Salmon',
        'description': 'Atlantic salmon fillet grilled to perfection, served with lemon butter sauce, asparagus and mashed potatoes.',
        'price': 18.99,
        'category': 'Main Course',
        'image_url': 'https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=400',
        'ingredients': ['salmon', 'asparagus', 'potatoes', 'lemon', 'butter', 'herbs'],
        'dietary_preferences': ['gluten_free'],
        'add_ons': [{'name': 'Side salad', 'price': 2.50}],
        'spice_levels_available': ['none', 'mild'],
    },
    {
        'name': 'Pasta Alfredo',
        'description': 'Fettuccine pasta in a rich creamy Parmesan Alfredo sauce, topped with fresh basil.',
        'price': 13.99,
        'category': 'Main Course',
        'image_url': 'https://images.unsplash.com/photo-1621996346565-e3dbc646d9a9?w=400',
        'ingredients': ['fettuccine', 'heavy cream', 'Parmesan', 'garlic', 'butter', 'basil'],
        'dietary_preferences': ['vegetarian'],
        'add_ons': [{'name': 'Grilled chicken', 'price': 3.50}, {'name': 'Extra Parmesan', 'price': 1.00}],
        'spice_levels_available': [],
    },
    {
        'name': 'Beef Steak',
        'description': '250g prime sirloin steak cooked to your liking, served with fries and mushroom sauce.',
        'price': 24.99,
        'category': 'Main Course',
        'image_url': 'https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=400',
        'ingredients': ['sirloin steak', 'fries', 'mushrooms', 'cream', 'garlic'],
        'dietary_preferences': ['gluten_free', 'halal'],
        'add_ons': [{'name': 'Extra sauce', 'price': 1.50}, {'name': 'Side vegetables', 'price': 2.00}],
        'spice_levels_available': ['none', 'mild', 'medium'],
    },
    # Pizzas
    {
        'name': 'Margherita Pizza',
        'description': 'Classic Neapolitan pizza with San Marzano tomato sauce, fresh mozzarella and basil on a thin crust.',
        'price': 12.99,
        'category': 'Pizzas',
        'image_url': 'https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=400',
        'ingredients': ['pizza dough', 'tomato sauce', 'mozzarella', 'basil', 'olive oil'],
        'dietary_preferences': ['vegetarian'],
        'add_ons': [{'name': 'Extra cheese', 'price': 1.50}, {'name': 'Olives', 'price': 1.00}],
        'spice_levels_available': [],
    },
    {
        'name': 'BBQ Chicken Pizza',
        'description': 'Smoky BBQ sauce base topped with grilled chicken, red onions, peppers and cheddar cheese.',
        'price': 15.99,
        'category': 'Pizzas',
        'image_url': 'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=400',
        'ingredients': ['pizza dough', 'BBQ sauce', 'chicken', 'red onion', 'peppers', 'cheddar'],
        'dietary_preferences': ['halal'],
        'add_ons': [{'name': 'Jalapeños', 'price': 0.75}, {'name': 'Extra chicken', 'price': 2.00}],
        'spice_levels_available': ['none', 'mild', 'medium', 'hot'],
    },
    # Burgers
    {
        'name': 'Classic Cheeseburger',
        'description': 'Juicy 180g beef patty with cheddar cheese, lettuce, tomato, pickles and our special burger sauce.',
        'price': 11.99,
        'category': 'Burgers',
        'image_url': 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=400',
        'ingredients': ['beef patty', 'cheddar', 'lettuce', 'tomato', 'pickles', 'brioche bun', 'special sauce'],
        'dietary_preferences': ['halal'],
        'add_ons': [{'name': 'Bacon', 'price': 1.50}, {'name': 'Extra patty', 'price': 3.00}, {'name': 'Fries', 'price': 2.50}],
        'spice_levels_available': ['none', 'mild'],
    },
    {
        'name': 'Veggie Burger',
        'description': 'Plant-based patty with avocado, roasted peppers, spinach, and vegan mayo on a toasted sesame bun.',
        'price': 10.99,
        'category': 'Burgers',
        'image_url': 'https://images.unsplash.com/photo-1520072959219-c595dc870360?w=400',
        'ingredients': ['plant-based patty', 'avocado', 'roasted peppers', 'spinach', 'vegan mayo', 'sesame bun'],
        'dietary_preferences': ['vegan'],
        'add_ons': [{'name': 'Fries', 'price': 2.50}, {'name': 'Onion rings', 'price': 2.00}],
        'spice_levels_available': ['none', 'mild', 'medium'],
    },
    # Desserts
    {
        'name': 'Chocolate Lava Cake',
        'description': 'Warm chocolate sponge with a gooey molten centre, served with vanilla ice cream.',
        'price': 7.99,
        'category': 'Desserts',
        'image_url': 'https://images.unsplash.com/photo-1624353365286-3f8d62daad51?w=400',
        'ingredients': ['dark chocolate', 'butter', 'eggs', 'flour', 'sugar', 'vanilla ice cream'],
        'dietary_preferences': ['vegetarian'],
        'add_ons': [{'name': 'Extra ice cream', 'price': 1.50}],
        'spice_levels_available': [],
    },
    {
        'name': 'Cheesecake',
        'description': 'New York-style creamy cheesecake on a buttery graham cracker crust, topped with strawberry compote.',
        'price': 6.99,
        'category': 'Desserts',
        'image_url': 'https://images.unsplash.com/photo-1533134242443-d4fd215305ad?w=400',
        'ingredients': ['cream cheese', 'eggs', 'sugar', 'graham crackers', 'butter', 'strawberries'],
        'dietary_preferences': ['vegetarian'],
        'add_ons': [],
        'spice_levels_available': [],
    },
    # Drinks
    {
        'name': 'Fresh Lemonade',
        'description': 'House-squeezed lemonade with mint and a hint of ginger. Served over ice.',
        'price': 3.99,
        'category': 'Drinks',
        'image_url': 'https://images.unsplash.com/photo-1587840171670-8b850147754e?w=400',
        'ingredients': ['lemon', 'sugar', 'mint', 'ginger', 'sparkling water'],
        'dietary_preferences': ['vegan', 'gluten_free'],
        'add_ons': [],
        'spice_levels_available': [],
    },
    {
        'name': 'Mango Lassi',
        'description': 'Creamy yogurt-based mango drink blended with cardamom. A refreshing Indian classic.',
        'price': 4.49,
        'category': 'Drinks',
        'image_url': 'https://images.unsplash.com/photo-1553361371-9b22f78e8b1d?w=400',
        'ingredients': ['mango', 'yogurt', 'milk', 'sugar', 'cardamom'],
        'dietary_preferences': ['vegetarian', 'gluten_free'],
        'add_ons': [],
        'spice_levels_available': [],
    },
]

inserted = 0
skipped = 0
for item in menu_items:
    category_name = item.pop('category')
    category_id = cat_ids[category_name]
    existing = db.menu_items.find_one({'name': item['name'], 'venue_id': venue_id_str})
    if existing:
        skipped += 1
        print(f"Menu item '{item['name']}' already exists, skipping.")
    else:
        db.menu_items.insert_one({
            **item,
            'category_id': category_id,
            'venue_id': venue_id_str,
            'is_available': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
        })
        inserted += 1
        print(f"Menu item '{item['name']}' inserted.")

print(f'\nDone. {inserted} items inserted, {skipped} skipped.')
