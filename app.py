from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = "change-this-secret-key"  # needed for session

# Simple in-memory menu (no database needed)
MENU = [
    {"id": "burger", "name": "Chicken Burger", "price": 450},
    {"id": "pizza", "name": "Cheese Pizza", "price": 900},
    {"id": "fried_rice", "name": "Fried Rice", "price": 700},
    {"id": "noodles", "name": "Spicy Noodles", "price": 650},
    {"id": "coffee", "name": "Iced Coffee", "price": 350},
    {"id": "juice", "name": "Orange Juice", "price": 300},
]

def get_menu_item(item_id: str):
    return next((x for x in MENU if x["id"] == item_id), None)

def get_cart():
    # cart format: { "burger": 2, "pizza": 1 }
    return session.get("cart", {})

def save_cart(cart):
    session["cart"] = cart

def cart_summary():
    cart = get_cart()
    items = []
    subtotal = 0

    for item_id, qty in cart.items():
        item = get_menu_item(item_id)
        if not item:
            continue
        qty = int(qty)
        line_total = item["price"] * qty
        subtotal += line_total
        items.append({
            "id": item_id,
            "name": item["name"],
            "price": item["price"],
            "qty": qty,
            "line_total": line_total
        })

    return items, subtotal

@app.route("/")
def index():
    items, subtotal = cart_summary()
    cart_count = sum(x["qty"] for x in items) if items else 0
    return render_template("index.html", menu=MENU, cart_count=cart_count)

@app.post("/add-to-cart")
def add_to_cart():
    item_id = request.form.get("item_id")
    qty_str = request.form.get("qty", "1")

    item = get_menu_item(item_id)
    if not item:
        flash("Item not found.", "error")
        return redirect(url_for("index"))

    try:
        qty = int(qty_str)
        if qty < 1:
            raise ValueError()
    except ValueError:
        flash("Quantity must be a positive number.", "error")
        return redirect(url_for("index"))

    cart = get_cart()
    cart[item_id] = int(cart.get(item_id, 0)) + qty
    save_cart(cart)

    flash(f"Added {qty} × {item['name']} to cart.", "success")
    return redirect(url_for("index"))

@app.route("/cart")
def cart():
    items, subtotal = cart_summary()
    delivery_fee = 150 if subtotal > 0 else 0
    total = subtotal + delivery_fee
    return render_template("cart.html", items=items, subtotal=subtotal, delivery_fee=delivery_fee, total=total)

@app.post("/update-cart")
def update_cart():
    cart = get_cart()
    # quantities come as qty_<itemid>
    for key in list(cart.keys()):
        form_key = f"qty_{key}"
        if form_key in request.form:
            try:
                new_qty = int(request.form.get(form_key, "0"))
            except ValueError:
                new_qty = 0

            if new_qty <= 0:
                cart.pop(key, None)
            else:
                cart[key] = new_qty

    save_cart(cart)
    flash("Cart updated.", "success")
    return redirect(url_for("cart"))

@app.post("/clear-cart")
def clear_cart():
    session["cart"] = {}
    flash("Cart cleared.", "success")
    return redirect(url_for("cart"))

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    items, subtotal = cart_summary()
    if subtotal == 0:
        flash("Your cart is empty. Add items first.", "error")
        return redirect(url_for("index"))

    delivery_fee = 150
    total = subtotal + delivery_fee

    if request.method == "POST":
        customer_name = request.form.get("name", "").strip()
        student_id = request.form.get("student_id", "").strip()
        address = request.form.get("address", "").strip()
        payment = request.form.get("payment", "Cash")

        if len(customer_name) < 2 or len(student_id) < 2 or len(address) < 5:
            flash("Please fill in all fields correctly.", "error")
            return render_template(
                "checkout.html",
                items=items, subtotal=subtotal, delivery_fee=delivery_fee, total=total
            )

        order_id = str(uuid.uuid4())[:8].upper()
        order_time = datetime.now().strftime("%Y-%m-%d %H:%M")

        receipt_data = {
            "order_id": order_id,
            "order_time": order_time,
            "name": customer_name,
            "student_id": student_id,
            "address": address,
            "payment": payment,
            "items": items,
            "subtotal": subtotal,
            "delivery_fee": delivery_fee,
            "total": total
        }

        # store receipt in session temporarily
        session["last_receipt"] = receipt_data
        session["cart"] = {}  # clear cart after order

        return redirect(url_for("receipt"))

    return render_template("checkout.html", items=items, subtotal=subtotal, delivery_fee=delivery_fee, total=total)

@app.route("/receipt")
def receipt():
    data = session.get("last_receipt")
    if not data:
        flash("No recent order found.", "error")
        return redirect(url_for("index"))
    return render_template("receipt.html", r=data)

if __name__ == "__main__":
    app.run(debug=True)
