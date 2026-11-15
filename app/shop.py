from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from sqlalchemy import text

from . import db
from .models import MenuItem, Order
from .services import (DELIVERY_FEE, FREE_DELIVERY_ABOVE, OrderError, cancel_order,
                       cart_details, place_order)

bp = Blueprint("shop", __name__)


@bp.route("/health")
def health():
    """Used by Jenkins after deployment to confirm the app and database are up."""
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify(status="ok", database="ok")
    except Exception:
        return jsonify(status="error", database="unreachable"), 500


@bp.route("/")
def menu():
    category = request.args.get("category")
    query = MenuItem.query.order_by(MenuItem.category, MenuItem.name)
    if category:
        query = query.filter_by(category=category)
    categories = [c[0] for c in db.session.query(MenuItem.category).distinct().order_by(MenuItem.category)]
    return render_template("menu.html", items=query.all(), categories=categories, active=category)


@bp.route("/cart/add/<int:item_id>", methods=["POST"])
def add_to_cart(item_id):
    item = db.get_or_404(MenuItem, item_id)
    if not item.available:
        flash(f"{item.name} is currently unavailable.", "error")
        return redirect(url_for("shop.menu"))
    cart = session.get("cart", {})
    cart[str(item_id)] = min(cart.get(str(item_id), 0) + 1, 10)
    session["cart"] = cart
    flash(f"Added {item.name} to cart.", "success")
    return redirect(request.referrer or url_for("shop.menu"))


@bp.route("/cart/update/<int:item_id>", methods=["POST"])
def update_cart(item_id):
    cart = session.get("cart", {})
    try:
        qty = int(request.form.get("qty", 0))
    except ValueError:
        qty = 0
    if qty <= 0:
        cart.pop(str(item_id), None)
    else:
        cart[str(item_id)] = min(qty, 10)
    session["cart"] = cart
    return redirect(url_for("shop.cart"))


@bp.route("/cart")
def cart():
    rows, subtotal, delivery, total = cart_details(session.get("cart", {}))
    return render_template("cart.html", rows=rows, subtotal=subtotal, delivery=delivery,
                           total=total, free_above=FREE_DELIVERY_ABOVE, fee=DELIVERY_FEE)


@bp.route("/checkout", methods=["POST"])
@login_required
def checkout():
    try:
        order = place_order(current_user, session.get("cart", {}), request.form.get("address", ""))
    except OrderError as e:
        flash(str(e), "error")
        return redirect(url_for("shop.cart"))
    session["cart"] = {}
    flash(f"Order #{order.id} placed! Total ₹{order.total}.", "success")
    return redirect(url_for("shop.my_orders"))


@bp.route("/orders")
@login_required
def my_orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template("orders.html", orders=orders)


@bp.route("/orders/<int:order_id>/cancel", methods=["POST"])
@login_required
def cancel(order_id):
    order = db.get_or_404(Order, order_id)
    if order.user_id != current_user.id:
        abort(403)
    try:
        cancel_order(order, current_user)
        flash(f"Order #{order.id} cancelled.", "info")
    except OrderError as e:
        flash(str(e), "error")
    return redirect(url_for("shop.my_orders"))
