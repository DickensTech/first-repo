import sqlite3

conn = sqlite3.connect('database.db')

foods = [
    ('Chicken Pizza', 'Pizza',
     'Chicken, cheese and fresh toppings', 600, 'chicken.jpg'),

    ('Beef Pizza', 'Pizza',
     'Beef, cheese and fresh toppings', 650, 'beef.jpg'),

    ('Fried Chicken', 'Chicken',
     'Crispy fried chicken', 350, 'fried.jpg'),

    ('Chicken & Chips', 'Chicken',
     'Chicken served with crispy chips', 500, 'chips.jpg'),

    ('Fish & Ugali', 'Fish',
     'Fresh fish served with ugali', 400, 'fish.jpg'),

    ('Fresh Juice', 'Drinks',
     'Freshly prepared fruit juice', 150, 'soda.jpg'),

    ('Soda', 'Drinks',
     'Refreshing soft drink', 80, 'pizza.jpg')
]
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    address TEXT,
    instructions TEXT, 
    quantity INTEGER NOT NULL,
    total_price REAL NOT NULL,
    order_status TEXT  NULL DEFAULT 'Pending',
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS order_items (
    order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    menu_item_id INTEGER NOT NULL,
    item_name TEXT NOT NULL,
    unit_price REAL NOT NULL,
    quantity INTEGER NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (menu_item_id) REFERENCES (menu_items_id)
)
""")

for food in foods:
    name, category, description, price, image = food
    existing = cursor.execute(
        'SELECT id FROM menu_items WHERE name = ? ORDER BY id LIMIT 1',
        (name,)
    ).fetchone()

    if existing:
        keep_id = existing[0]
        cursor.execute(
            'UPDATE order_items SET menu_item_id = ?, item_name = ?, unit_price = ? '
            'WHERE menu_item_id IN (SELECT id FROM menu_items WHERE name = ?)',
            (keep_id, name, price, name)
        )
        cursor.execute(
            'DELETE FROM menu_items WHERE name = ? AND id != ?',
            (name, keep_id)
        )
    else:
        cursor.execute('''
            INSERT INTO menu_items
            (name, category, description, price, image)
            VALUES (?, ?, ?, ?, ?)
        ''', food)

cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS menu_items_name_unique ON menu_items(name)')

conn.commit()
conn.close()

print("Food items added successfully!")