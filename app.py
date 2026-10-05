from flask import Flask, redirect, url_for, render_template, request, session
import json
import os
import re
import secrets
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash


app=Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY') or secrets.token_hex(32)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'


def ensure_database_schema():
    conn = sqlite3.connect('database.db')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL COLLATE NOCASE UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    columns = [row[1] for row in conn.execute('PRAGMA table_info(orders)').fetchall()]
    if 'order_type' not in columns:
        conn.execute("ALTER TABLE orders ADD COLUMN order_type TEXT DEFAULT 'Delivery'")
        conn.commit()
    conn.close()


ensure_database_schema()


def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/menu')
def menu():
    conn = get_db_connection()
    items = conn.execute('SELECT * FROM menu_items ORDER BY category, name').fetchall()
    conn.close()
    return render_template('menu.html', menu_items=items)


@app.route('/menu.html')
def menu_html():
    return redirect(url_for('menu'))


@app.route('/')
def home():
    return render_template('template.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json(silent=True)
        data = data if isinstance(data, dict) else request.form
        email = str(data.get('email', '')).strip().lower()
        password = str(data.get('password', ''))

        if not email or not password:
            return {'error': 'Enter your email address and password.'}, 400

        conn = get_db_connection()
        user = conn.execute(
            'SELECT user_id, name, password_hash FROM users WHERE email = ?',
            (email,),
        ).fetchone()
        conn.close()

        if user is None or not check_password_hash(user['password_hash'], password):
            return {'error': 'Email or password is incorrect.'}, 401

        session.clear()
        session['user_id'] = user['user_id']
        session['user_name'] = user['name']
        return {'message': f'Welcome back, {user["name"]}.'}

    return render_template('login.html')


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else request.form
    name = str(data.get('name', '')).strip()
    email = str(data.get('email', '')).strip().lower()
    password = str(data.get('password', ''))
    confirm_password = str(data.get('confirm_password', ''))

    if not name or len(name) > 120:
        return {'error': 'Enter a name between 1 and 120 characters.'}, 400
    if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email) or len(email) > 254:
        return {'error': 'Enter a valid email address.'}, 400
    if len(password) < 8 or len(password) > 128:
        return {'error': 'Your password must be between 8 and 128 characters.'}, 400
    if password != confirm_password:
        return {'error': 'Passwords do not match.'}, 400

    conn = get_db_connection()
    try:
        cursor = conn.execute(
            'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
            (name, email, generate_password_hash(password)),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        return {'error': 'An account with that email already exists.'}, 409
    finally:
        conn.close()

    session.clear()
    session['user_id'] = cursor.lastrowid
    session['user_name'] = name
    return {'message': f'Account created. Welcome, {name}.'}, 201


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/order', methods=['GET', 'POST'])
def order():
    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form

        customer_name = str(data.get('name', '')).strip()
        phone = str(data.get('phone', '')).strip()
        address = str(data.get('address', '')).strip()
        instructions = str(data.get('instructions', '')).strip()
        order_type = str(data.get('service', 'Delivery')).strip() or 'Delivery'

        try:
            requested_items = data.get('items', [])
            if isinstance(requested_items, str):
                requested_items = json.loads(requested_items)
            requested_items = [
                {'id': int(item['id']), 'quantity': int(item['quantity'])}
                for item in requested_items
                if int(item['quantity']) > 0
            ]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return {'error': 'Please select valid food items and quantities.'}, 400

        if not customer_name or not phone or not requested_items:
            return {'error': 'Please provide customer details and select at least one item.'}, 400

        conn = get_db_connection()
        menu_ids = [item['id'] for item in requested_items]
        placeholders = ','.join('?' for _ in menu_ids)
        menu_items = conn.execute(
            f'SELECT id, name, price FROM menu_items WHERE id IN ({placeholders})',
            menu_ids
        ).fetchall()
        menu_by_id = {item['id']: item for item in menu_items}

        if len(menu_by_id) != len(set(menu_ids)):
            conn.close()
            return {'error': 'One or more selected food items are unavailable.'}, 400

        quantity = sum(item['quantity'] for item in requested_items)
        total_price = sum(
            menu_by_id[item['id']]['price'] * item['quantity']
            for item in requested_items
        )
        cursor = conn.execute(
            '''INSERT INTO orders
               (customer_name, phone, address, instructions, quantity, total_price, order_type)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (customer_name, phone, address, instructions, quantity, total_price, order_type)
        )
        order_id = cursor.lastrowid
        conn.executemany(
            '''INSERT INTO order_items (order_id, menu_item_id, item_name, unit_price, quantity)
               VALUES (?, ?, ?, ?, ?)''',
            [
                (order_id, item['id'], menu_by_id[item['id']]['name'],
                 menu_by_id[item['id']]['price'], item['quantity'])
                for item in requested_items
            ]
        )
        conn.commit()
        conn.close()

        return {'message': 'Order received successfully.', 'order_id': order_id}, 201

    conn = get_db_connection()
    menu_items = conn.execute(
        'SELECT id, name, price FROM menu_items WHERE available = 1 ORDER BY category, name'
    ).fetchall()
    conn.close()
    return render_template(
        'order.html',
        menu_items=menu_items,
        selected_food=request.args.get('food', '')
    )


@app.route("/admin/orders")
def admin_orders():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM orders
        ORDER BY order_id DESC
    """)

    orders = cursor.fetchall()

    conn.close()

    return render_template("admin_orders.html", orders=orders)


@app.route("/admin/orders/<int:order_id>/status", methods=["POST"])
def update_order_status(order_id):
    status = request.form.get("status")
    allowed_statuses = ["Pending", "Preparing", "Ready", "Completed"]

    if status not in allowed_statuses:
        return {"error": "Invalid order status"}, 400

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE orders SET order_status = ? WHERE order_id = ?",
        (status, order_id),
    )
    conn.commit()
    conn.close()

    return redirect(url_for('admin_orders'))


@app.route("/order/confirmation/<int:order_id>")
def order_confirmation(order_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM orders
        WHERE order_id = ?
    """, (order_id,))

    order = cursor.fetchone()
    conn.close()

    if order is None:
        return "Order not found", 404

    return render_template("confirmation.html", order=order)


@app.route("/orders/confirmation/<int:order_id>")
def orders_confirmation(order_id):
    return order_confirmation(order_id)

@app.route("/track-order", methods=["GET", "POST"])
@app.route("/track_order", methods=["GET", "POST"])
def track_order():
    order = None
    error = None

    if request.method == "POST":
        order_id = request.form.get("order_id", "").strip()
        phone = request.form.get("phone", "").strip()

        if order_id:
            try:
                order_id = int(order_id)
            except ValueError:
                error = "Please enter a valid order number."
            else:
                conn = get_db_connection()
                order = conn.execute(
                    "SELECT * FROM orders WHERE order_id = ?",
                    (order_id,),
                ).fetchone()
                conn.close()

                if order is None:
                    error = "Order not found. Please check your order number."
        elif phone:
            conn = get_db_connection()
            order = conn.execute(
                "SELECT * FROM orders WHERE phone = ? ORDER BY order_id DESC LIMIT 1",
                (phone,),
            ).fetchone()
            conn.close()

            if order is None:
                error = "No order found for this phone number."
        else:
            error = "Please enter either an order number or a phone number."

    return render_template(
        "track_order.html",
        order=order,
        error=error
    )



@app.route("/admin/dashboard")
def admin_dashboard():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM orders")
    total_orders = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM orders WHERE order_status = 'Pending' OR order_status IS NULL")
    pending_orders = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM orders WHERE order_status = 'Preparing'")
    preparing_orders = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM orders WHERE order_status = 'Completed'")
    completed_orders = cursor.fetchone()[0]

    cursor.execute("SELECT * FROM orders ORDER BY order_id DESC LIMIT 10")
    recent_orders = cursor.fetchall()

    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_orders=total_orders,
        pending_orders=pending_orders,
        preparing_orders=preparing_orders,
        completed_orders=completed_orders,
        recent_orders=recent_orders
    )

if __name__ == '__main__':
    app.run(debug=True)