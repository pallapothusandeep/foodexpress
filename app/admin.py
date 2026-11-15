from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from . import db
from .models import ORDER_STATUSES, MenuItem, Order
from .storage import save_image

bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


@bp.route("/")
@admin_required
def dashboard():
    status = request.args.get("status")
    query = Order.query.order_by(Order.created_at.desc())
    if status:
        query = query.filter_by(status=status)
    stats = {
        "orders": Order.query.count(),
        "pending": Order.query.filter(Order.status.in_(["Placed", "Preparing", "Out for Delivery"])).count(),
        "revenue": db.session.query(func.coalesce(func.sum(Order.total), 0))
                     .filter(Order.status == "Delivered").scalar(),
        "items": MenuItem.query.count(),
    }
    return render_template("admin/dashboard.html", orders=query.all(), stats=stats,
                           statuses=ORDER_STATUSES, active=status)


@bp.route("/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def update_status(order_id):
    order = db.get_or_404(Order, order_id)
    new_status = request.form.get("status")
    if new_status not in ORDER_STATUSES:
        abort(400)
    order.status = new_status
    db.session.commit()
    flash(f"Order #{order.id} marked as {new_status}.", "success")
    return redirect(request.referrer or url_for("admin.dashboard"))


@bp.route("/menu")
@admin_required
def menu_list():
    items = MenuItem.query.order_by(MenuItem.category, MenuItem.name).all()
    return render_template("admin/menu.html", items=items)


@bp.route("/menu/new", methods=["GET", "POST"])
@bp.route("/menu/<int:item_id>/edit", methods=["GET", "POST"])
@admin_required
def menu_form(item_id=None):
    item = db.get_or_404(MenuItem, item_id) if item_id else None
    if request.method == "POST":
        form = request.form
        try:
            price = int(form.get("price", 0))
            if price <= 0 or not form.get("name") or not form.get("category"):
                raise ValueError("Name, category and a positive price are required.")
            image_url = save_image(request.files.get("image"))
        except ValueError as e:
            flash(str(e), "error")
            return render_template("admin/menu_form.html", item=item)

        if item is None:
            item = MenuItem()
            db.session.add(item)
        item.name = form["name"].strip()
        item.description = form.get("description", "").strip()
        item.category = form["category"].strip()
        item.price = price
        item.is_veg = form.get("is_veg") == "on"
        item.available = form.get("available") == "on"
        if image_url:
            item.image_url = image_url
        db.session.commit()
        flash(f"Saved {item.name}.", "success")
        return redirect(url_for("admin.menu_list"))
    return render_template("admin/menu_form.html", item=item)


@bp.route("/menu/<int:item_id>/toggle", methods=["POST"])
@admin_required
def toggle(item_id):
    item = db.get_or_404(MenuItem, item_id)
    item.available = not item.available
    db.session.commit()
    return redirect(url_for("admin.menu_list"))
