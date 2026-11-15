"""Business logic, kept separate from routes so it is easy to unit test."""
from . import db
from .models import MenuItem, Order, OrderItem

MIN_ORDER_VALUE = 100
DELIVERY_FEE = 30
FREE_DELIVERY_ABOVE = 499


class OrderError(Exception):
    pass


def cart_details(cart):
    """Turn a session cart {item_id: qty} into rows + bill breakdown."""
    rows, subtotal = [], 0
    for item_id, qty in cart.items():
        item = db.session.get(MenuItem, int(item_id))
        if item is None:
            continue
        line = item.price * qty
        subtotal += line
        rows.append({"item": item, "qty": qty, "line_total": line})
    delivery = 0 if subtotal == 0 or subtotal >= FREE_DELIVERY_ABOVE else DELIVERY_FEE
    return rows, subtotal, delivery, subtotal + delivery


def place_order(user, cart, address):
    if not cart:
        raise OrderError("Your cart is empty.")
    if not address or len(address.strip()) < 10:
        raise OrderError("Please enter a full delivery address.")

    rows, subtotal, delivery, total = cart_details(cart)
    unavailable = [r["item"].name for r in rows if not r["item"].available]
    if unavailable:
        raise OrderError(f"Currently unavailable: {', '.join(unavailable)}. Remove it from your cart.")
    if subtotal < MIN_ORDER_VALUE:
        raise OrderError(f"Minimum order value is ₹{MIN_ORDER_VALUE}.")

    order = Order(user_id=user.id, address=address.strip(), total=total)
    for r in rows:
        order.items.append(OrderItem(menu_item_id=r["item"].id, name=r["item"].name,
                                     price=r["item"].price, quantity=r["qty"]))
    db.session.add(order)
    db.session.commit()
    return order


def cancel_order(order, user):
    if order.user_id != user.id:
        raise OrderError("You can only cancel your own orders.")
    if order.status != "Placed":
        raise OrderError("This order is already being prepared and can't be cancelled.")
    order.status = "Cancelled"
    db.session.commit()
