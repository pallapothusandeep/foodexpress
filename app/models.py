from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from . import db, login_manager

ORDER_STATUSES = ["Placed", "Preparing", "Out for Delivery", "Delivered", "Cancelled"]


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(15))
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    orders = db.relationship("Order", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    price = db.Column(db.Integer, nullable=False)  # in rupees
    category = db.Column(db.String(50), nullable=False)
    is_veg = db.Column(db.Boolean, default=True)
    image_url = db.Column(db.String(500))
    available = db.Column(db.Boolean, default=True)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.String(30), default="Placed")
    address = db.Column(db.String(255), nullable=False)
    total = db.Column(db.Integer, nullable=False)
    items = db.relationship("OrderItem", backref="order", lazy=True, cascade="all, delete-orphan")


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey("menu_item.id"))
    name = db.Column(db.String(100), nullable=False)   # copied so old orders keep the name
    price = db.Column(db.Integer, nullable=False)      # price at time of order
    quantity = db.Column(db.Integer, nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


SAMPLE_MENU = [
    ("Chicken Biryani", "Hyderabadi dum biryani with raita", 249, "Biryani", False),
    ("Veg Biryani", "Fragrant basmati rice with vegetables", 189, "Biryani", True),
    ("Masala Dosa", "Crispy dosa with potato masala, chutney and sambar", 99, "South Indian", True),
    ("Idli (2 pcs)", "Soft idlis with chutney and sambar", 59, "South Indian", True),
    ("Paneer Butter Masala", "Cottage cheese in rich tomato gravy", 219, "North Indian", True),
    ("Butter Naan", "Tandoor-baked naan with butter", 45, "North Indian", True),
    ("Chicken 65", "Spicy deep-fried chicken starter", 199, "Starters", False),
    ("Gobi Manchurian", "Indo-Chinese cauliflower fry", 149, "Starters", True),
    ("Filter Coffee", "Classic South Indian filter coffee", 40, "Beverages", True),
    ("Gulab Jamun (2 pcs)", "Warm syrup-soaked dumplings", 69, "Desserts", True),
]


def seed(app):
    """Create the first admin and a starter menu if the database is empty."""
    try:
        if not User.query.filter_by(email=app.config["ADMIN_EMAIL"]).first():
            admin = User(name="Admin", email=app.config["ADMIN_EMAIL"], is_admin=True)
            admin.set_password(app.config["ADMIN_PASSWORD"])
            db.session.add(admin)
        if MenuItem.query.count() == 0:
            for name, desc, price, cat, veg in SAMPLE_MENU:
                db.session.add(MenuItem(name=name, description=desc, price=price,
                                        category=cat, is_veg=veg))
        db.session.commit()
    except Exception:
        db.session.rollback()
