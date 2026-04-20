"""
ShopEasy V2 - AWT College Project (Enhanced)
Technique : Flask Framework (Experiment 12)
New Features:
  - Wishlist (add/remove)
  - Product ratings (1-5 stars, stored in DB)
  - Order history page
  - Product stock badge
  - Search + category + sort combined
  - Order saved with items detail
"""

from flask import Flask, render_template, redirect, url_for, session, request, flash
import sqlite3, json
from datetime import datetime

app = Flask(__name__)
app.secret_key = "shopeasy_v2_awt_2024"
DB = "shop.db"

# ───────────────────────────────────────────
#  DB HELPERS
# ───────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT    NOT NULL,
        price       REAL    NOT NULL,
        orig_price  REAL,
        category    TEXT    NOT NULL,
        emoji       TEXT    NOT NULL,
        description TEXT    NOT NULL,
        stock       INTEGER NOT NULL DEFAULT 10,
        rating      REAL    NOT NULL DEFAULT 4.0,
        rating_count INTEGER NOT NULL DEFAULT 0,
        badge       TEXT    DEFAULT ''
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS orders (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        name       TEXT NOT NULL,
        email      TEXT NOT NULL,
        address    TEXT NOT NULL,
        total      REAL NOT NULL,
        items_json TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS reviews (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        rating     INTEGER NOT NULL,
        comment    TEXT,
        reviewer   TEXT NOT NULL DEFAULT 'Anonymous',
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
    )""")

    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        products = [
            # name, price, orig_price, category, emoji, description, stock, rating, rating_count, badge
            ("Wireless Earbuds",      1299, 1799, "Electronics","🎧","Bluetooth 5.0 | 24-hr battery | Active noise cancellation",15,4.5,128,"Best Seller"),
            ("Mechanical Keyboard",   2499, 3199, "Electronics","⌨️","RGB backlit | Tactile switches | USB-C detachable cable",8, 4.3,74, ""),
            ("USB-C Hub 7-in-1",       899, 1199, "Electronics","🔌","HDMI 4K | 3×USB-A | SD+MicroSD | 100W PD charging",20,4.1,56, ""),
            ("Smartwatch Pro",        3499, 4499, "Electronics","⌚","Heart rate | SpO2 | Sleep tracking | 7-day battery",12,4.7,203,"Top Rated"),
            ("Classic White Shirt",    599,  799, "Clothing",   "👔","100% cotton | Slim fit | Machine washable | All sizes",30,4.2,89, ""),
            ("Denim Jeans",            999, 1499, "Clothing",   "👖","Stretch denim | Regular fit | 5 pockets | Sizes 28–38",25,4.0,61, ""),
            ("Running Shoes",         1799, 2299, "Clothing",   "👟","Lightweight mesh upper | Anti-slip sole | EVA midsole",18,4.6,147,"Best Seller"),
            ("Hoodie Sweatshirt",      849, 1099, "Clothing",   "🧥","300 GSM fleece | Kangaroo pocket | Unisex | 5 colours",22,4.4,93, ""),
            ("Python Crash Course",    499,  599, "Books",      "📗","Eric Matthes | Beginner-friendly | 3rd edition | 560 pages",40,4.8,312,"Top Rated"),
            ("Clean Code",             599,  699, "Books",      "📘","Robert Martin | Best practices | Software design patterns",35,4.6,189,""),
            ("The Alchemist",          299,  349, "Books",      "📙","Paulo Coelho | Translated in 80 languages | Inspirational",50,4.9,445,"Top Rated"),
            ("DSA — Algorithms",       649,  799, "Books",      "📕","College-level | Time & space complexity | Interview prep",30,4.5,102,""),
            ("Steel Water Bottle",     349,  499, "Kitchen",    "🍶","1 litre | Cold 24hr | Hot 12hr | BPA-free | Leakproof",40,4.3,78, ""),
            ("Air Fryer 4L",          2999, 3999, "Kitchen",    "🍳","1500W | 8 presets | Digital display | Dishwasher safe basket",10,4.7,234,"Best Seller"),
            ("Bamboo Chopping Set",    399,  549, "Kitchen",    "🥗","3-piece | Antibacterial bamboo | Non-slip feet | Food safe",35,4.2,67, ""),
            ("Coffee Mug 350ml",       199,  249, "Kitchen",    "☕","Double-wall ceramic | Microwave safe | Keeps hot 3hr",60,4.4,156,""),
        ]
        c.executemany("""INSERT INTO products
            (name,price,orig_price,category,emoji,description,stock,rating,rating_count,badge)
            VALUES (?,?,?,?,?,?,?,?,?,?)""", products)

        # Seed some sample reviews
        reviews = [
            (1,5,"Amazing sound quality! The noise cancellation is great.","Arjun S."),
            (1,4,"Good earbuds but the case could be better.","Priya M."),
            (9,5,"Best Python book for beginners. Highly recommended!","Dev K."),
            (9,5,"Cleared all my doubts. Love the projects at the end.","Sneha R."),
            (11,5,"A must read. Changed my perspective on life.","Rahul V."),
            (14,5,"Cooks everything crispy! Best kitchen purchase.","Anita P."),
            (4,5,"The health tracking is incredibly accurate.","Vikram N."),
        ]
        c.executemany("INSERT INTO reviews (product_id,rating,comment,reviewer) VALUES (?,?,?,?)", reviews)

        conn.commit()
    conn.close()

# ───────────────────────────────────────────
#  ROUTES
# ───────────────────────────────────────────

@app.route("/")
def home():
    category = request.args.get("category", "All")
    search   = request.args.get("search", "").strip()
    sort     = request.args.get("sort", "default")

    conn = get_db()
    cats = [r["category"] for r in
            conn.execute("SELECT DISTINCT category FROM products ORDER BY category").fetchall()]

    q = "SELECT * FROM products WHERE 1=1"
    params = []
    if category != "All":
        q += " AND category=?"; params.append(category)
    if search:
        q += " AND (name LIKE ? OR description LIKE ?)"; params += [f"%{search}%"]*2

    order_map = {
        "price_asc":  "price ASC",
        "price_desc": "price DESC",
        "rating":     "rating DESC",
        "name":       "name ASC",
    }
    q += f" ORDER BY {order_map.get(sort, 'id ASC')}"
    products = conn.execute(q, params).fetchall()

    # Stats for hero
    total_products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    conn.close()

    cart_count  = sum(session.get("cart", {}).values())
    wish_count  = len(session.get("wishlist", []))
    return render_template("index.html",
        products=products, categories=cats,
        selected_cat=category, search=search, sort=sort,
        cart_count=cart_count, wish_count=wish_count,
        wishlist=session.get("wishlist",[]),
        total_products=total_products)

@app.route("/product/<int:pid>")
def product_detail(pid):
    conn    = get_db()
    product = conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    reviews = conn.execute("SELECT * FROM reviews WHERE product_id=? ORDER BY id DESC", (pid,)).fetchall()
    related = conn.execute(
        "SELECT * FROM products WHERE category=? AND id!=? LIMIT 4",
        (product["category"], pid)
    ).fetchall()
    conn.close()
    cart_count = sum(session.get("cart", {}).values())
    wish_count = len(session.get("wishlist", []))
    in_wishlist = str(pid) in [str(w) for w in session.get("wishlist", [])]
    return render_template("product.html",
        product=product, reviews=reviews, related=related,
        cart_count=cart_count, wish_count=wish_count, in_wishlist=in_wishlist)

@app.route("/add_to_cart/<int:pid>")
def add_to_cart(pid):
    cart = session.get("cart", {})
    cart[str(pid)] = cart.get(str(pid), 0) + 1
    session["cart"] = cart
    flash("Added to cart!", "success")
    return redirect(request.referrer or url_for("home"))

@app.route("/remove/<int:pid>")
def remove_from_cart(pid):
    cart = session.get("cart", {})
    cart.pop(str(pid), None)
    session["cart"] = cart
    flash("Item removed.", "info")
    return redirect(url_for("cart"))

@app.route("/update_cart/<int:pid>/<action>")
def update_cart(pid, action):
    cart = session.get("cart", {})
    key  = str(pid)
    if action == "inc":
        cart[key] = cart.get(key, 0) + 1
    elif action == "dec":
        cart[key] = cart.get(key, 1) - 1
        if cart[key] <= 0:
            cart.pop(key, None)
    session["cart"] = cart
    return redirect(url_for("cart"))

@app.route("/wishlist/toggle/<int:pid>")
def toggle_wishlist(pid):
    wl = session.get("wishlist", [])
    if pid in wl:
        wl.remove(pid)
        flash("Removed from wishlist.", "info")
    else:
        wl.append(pid)
        flash("Added to wishlist!", "success")
    session["wishlist"] = wl
    return redirect(request.referrer or url_for("home"))

@app.route("/wishlist")
def wishlist():
    wl = session.get("wishlist", [])
    products = []
    if wl:
        conn = get_db()
        placeholders = ",".join("?" * len(wl))
        products = conn.execute(
            f"SELECT * FROM products WHERE id IN ({placeholders})", wl
        ).fetchall()
        conn.close()
    cart_count = sum(session.get("cart", {}).values())
    wish_count = len(wl)
    return render_template("wishlist.html",
        products=products, cart_count=cart_count, wish_count=wish_count)

@app.route("/cart")
def cart():
    cart_data = session.get("cart", {})
    items, total = [], 0
    conn = get_db()
    for pid, qty in cart_data.items():
        p = conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
        if p:
            sub = p["price"] * qty
            total += sub
            items.append({"product": p, "qty": qty, "subtotal": sub})
    conn.close()
    cart_count = sum(cart_data.values())
    wish_count = len(session.get("wishlist", []))
    return render_template("cart.html",
        items=items, total=total,
        cart_count=cart_count, wish_count=wish_count)

@app.route("/checkout", methods=["GET","POST"])
def checkout():
    cart_data = session.get("cart", {})
    if not cart_data:
        flash("Your cart is empty!", "error")
        return redirect(url_for("home"))

    items, total = [], 0
    conn = get_db()
    for pid, qty in cart_data.items():
        p = conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
        if p:
            sub = p["price"] * qty
            total += sub
            items.append({"name": p["name"], "qty": qty, "price": p["price"], "subtotal": sub})

    if request.method == "POST":
        name    = request.form.get("name","").strip()
        email   = request.form.get("email","").strip()
        address = request.form.get("address","").strip()
        if not all([name, email, address]):
            flash("Please fill all fields.", "error")
            conn.close()
            return render_template("checkout.html",
                items=items, total=total,
                cart_count=sum(cart_data.values()),
                wish_count=len(session.get("wishlist",[])))

        conn.execute(
            "INSERT INTO orders (name,email,address,total,items_json) VALUES (?,?,?,?,?)",
            (name, email, address, total, json.dumps(items))
        )
        conn.commit()
        conn.close()
        session["cart"] = {}
        flash(f"Order placed successfully! Thank you, {name}.", "success")
        return redirect(url_for("orders"))

    conn.close()
    return render_template("checkout.html",
        items=items, total=total,
        cart_count=sum(cart_data.values()),
        wish_count=len(session.get("wishlist",[])))

@app.route("/orders")
def orders():
    conn  = get_db()
    all_orders = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    conn.close()
    cart_count = sum(session.get("cart", {}).values())
    wish_count = len(session.get("wishlist", []))
    parsed = []
    for o in all_orders:
        parsed.append({
            "id":         o["id"],
            "name":       o["name"],
            "email":      o["email"],
            "address":    o["address"],
            "total":      o["total"],
            "created_at": o["created_at"],
            "items":      json.loads(o["items_json"])
        })
    return render_template("orders.html",
        orders=parsed, cart_count=cart_count, wish_count=wish_count)

@app.route("/review/<int:pid>", methods=["POST"])
def add_review(pid):
    reviewer = request.form.get("reviewer","Anonymous").strip() or "Anonymous"
    rating   = int(request.form.get("rating", 5))
    comment  = request.form.get("comment","").strip()
    conn = get_db()
    conn.execute(
        "INSERT INTO reviews (product_id,rating,comment,reviewer) VALUES (?,?,?,?)",
        (pid, rating, comment, reviewer)
    )
    # Recalculate product rating
    row = conn.execute(
        "SELECT AVG(rating) as avg, COUNT(*) as cnt FROM reviews WHERE product_id=?", (pid,)
    ).fetchone()
    conn.execute(
        "UPDATE products SET rating=?, rating_count=? WHERE id=?",
        (round(row["avg"], 1), row["cnt"], pid)
    )
    conn.commit()
    conn.close()
    flash("Review submitted! Thank you.", "success")
    return redirect(url_for("product_detail", pid=pid))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
