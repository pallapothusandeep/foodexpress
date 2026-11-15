import pytest

from app import create_app, db
from app.models import MenuItem, Order, User


@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "ADMIN_EMAIL": "admin@test.com",
        "ADMIN_PASSWORD": "adminpass",
    })
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def register(client, email="user@test.com", password="secret123"):
    return client.post("/register", data={"name": "Ravi", "email": email,
                                          "phone": "9876543210", "password": password},
                       follow_redirects=True)


def login(client, email, password):
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=True)


def item_id(app, name):
    with app.app_context():
        return MenuItem.query.filter_by(name=name).first().id


ADDRESS = "12, Anna Nagar 2nd Street, Chennai"


# ---------- health & menu ----------
def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json() == {"status": "ok", "database": "ok"}


def test_menu_is_seeded_and_shown(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Chicken Biryani" in res.data


def test_menu_category_filter(client):
    res = client.get("/?category=Beverages")
    assert b"Filter Coffee" in res.data
    assert b"Chicken Biryani" not in res.data


# ---------- auth ----------
def test_register_and_login(client):
    assert b"Welcome, Ravi" in register(client).data
    client.post("/logout")
    assert b"My Orders" in login(client, "user@test.com", "secret123").data


def test_wrong_password_rejected(client):
    register(client)
    client.post("/logout")
    assert b"Invalid email or password" in login(client, "user@test.com", "wrong").data


def test_duplicate_email_rejected(client):
    register(client)
    client.post("/logout")
    assert b"already exists" in register(client).data


def test_passwords_are_hashed(app, client):
    register(client)
    with app.app_context():
        user = User.query.filter_by(email="user@test.com").first()
        assert user.password_hash != "secret123"


# ---------- cart & ordering ----------
def test_checkout_requires_login(client, app):
    client.post(f"/cart/add/{item_id(app, 'Chicken Biryani')}")
    res = client.post("/checkout", data={"address": ADDRESS})
    assert res.status_code == 302 and "/login" in res.headers["Location"]


def test_place_order_calculates_total_with_delivery(client, app):
    register(client)
    biryani = item_id(app, "Chicken Biryani")  # 249
    client.post(f"/cart/add/{biryani}")
    res = client.post("/checkout", data={"address": ADDRESS}, follow_redirects=True)
    assert b"placed" in res.data
    with app.app_context():
        order = Order.query.one()
        assert order.total == 249 + 30  # below 499 -> delivery fee
        assert order.status == "Placed"


def test_free_delivery_above_499(client, app):
    register(client)
    biryani = item_id(app, "Chicken Biryani")
    for _ in range(2):
        client.post(f"/cart/add/{biryani}")  # 498
    client.post(f"/cart/add/{item_id(app, 'Filter Coffee')}")  # +40 = 538
    client.post("/checkout", data={"address": ADDRESS})
    with app.app_context():
        assert Order.query.one().total == 538


def test_minimum_order_value(client, app):
    register(client)
    client.post(f"/cart/add/{item_id(app, 'Filter Coffee')}")  # 40 < 100
    res = client.post("/checkout", data={"address": ADDRESS}, follow_redirects=True)
    assert b"Minimum order value" in res.data
    with app.app_context():
        assert Order.query.count() == 0


def test_empty_cart_cannot_checkout(client):
    register(client)
    res = client.post("/checkout", data={"address": ADDRESS}, follow_redirects=True)
    assert b"cart is empty" in res.data


def test_unavailable_item_blocks_order(client, app):
    register(client)
    biryani = item_id(app, "Chicken Biryani")
    client.post(f"/cart/add/{biryani}")
    with app.app_context():
        db.session.get(MenuItem, biryani).available = False
        db.session.commit()
    res = client.post("/checkout", data={"address": ADDRESS}, follow_redirects=True)
    assert b"Currently unavailable" in res.data


def test_cart_quantity_update_and_remove(client, app):
    biryani = item_id(app, "Chicken Biryani")
    client.post(f"/cart/add/{biryani}")
    client.post(f"/cart/update/{biryani}", data={"qty": "3"})
    assert b"747" in client.get("/cart").data  # 3 x 249
    client.post(f"/cart/update/{biryani}", data={"qty": "0"})
    assert b"cart is empty" in client.get("/cart").data


# ---------- cancellation ----------
def place_one(client, app):
    client.post(f"/cart/add/{item_id(app, 'Chicken Biryani')}")
    client.post("/checkout", data={"address": ADDRESS})
    with app.app_context():
        return Order.query.order_by(Order.id.desc()).first().id


def test_user_can_cancel_placed_order(client, app):
    register(client)
    oid = place_one(client, app)
    client.post(f"/orders/{oid}/cancel")
    with app.app_context():
        assert db.session.get(Order, oid).status == "Cancelled"


def test_cannot_cancel_after_preparing(client, app):
    register(client)
    oid = place_one(client, app)
    with app.app_context():
        db.session.get(Order, oid).status = "Preparing"
        db.session.commit()
    res = client.post(f"/orders/{oid}/cancel", follow_redirects=True)
    assert b"can&#39;t be cancelled" in res.data


def test_user_cannot_cancel_someone_elses_order(client, app):
    register(client, "a@test.com")
    oid = place_one(client, app)
    client.post("/logout")
    register(client, "b@test.com")
    assert client.post(f"/orders/{oid}/cancel").status_code == 403


# ---------- admin ----------
def test_customer_cannot_open_admin(client):
    register(client)
    assert client.get("/admin/").status_code == 403


def test_admin_can_update_order_status(client, app):
    register(client)
    oid = place_one(client, app)
    client.post("/logout")
    login(client, "admin@test.com", "adminpass")
    assert client.get("/admin/").status_code == 200
    client.post(f"/admin/orders/{oid}/status", data={"status": "Delivered"})
    with app.app_context():
        assert db.session.get(Order, oid).status == "Delivered"


def test_admin_can_add_menu_item(client, app):
    login(client, "admin@test.com", "adminpass")
    client.post("/admin/menu/new", data={"name": "Paneer Tikka", "category": "Starters",
                                         "price": "229", "is_veg": "on", "available": "on"})
    with app.app_context():
        assert MenuItem.query.filter_by(name="Paneer Tikka").first().price == 229
