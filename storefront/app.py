import json
import os
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from mirage.logger import HoneypotLogger

basedir = os.path.abspath(os.path.dirname(__file__))

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "login"


def create_shared_app(test_config=None):
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config["SECRET_KEY"] = os.environ.get("STOREFRONT_SECRET", "dev-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(basedir, 'storefront.db')}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MIRAGE_ADMIN_PATH"] = "/hidden-ops"

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    login_manager.login_view = "login"
    login_manager.init_app(app)
    app.login_manager.login_view = "login"

    log_dir = app.config.get("MIRAGE_LOG_DIR", os.environ.get("MIRAGE_LOG_DIR", "logs"))
    logger = HoneypotLogger(log_dir=log_dir)
    app.extensions["honeypot_logger"] = logger
    app.config["HONEYPOT_LOG_DIR"] = log_dir

    from .models import User, Product

    @app.before_request
    def log_http_request():
        forwarded_for = request.headers.get("X-Forwarded-For", "")
        source_ip = forwarded_for.split(",")[0].strip() or request.headers.get("X-Real-IP", "") or request.remote_addr or "unknown"
        logger.record_event(
            "http_request",
            source_ip=source_ip,
            method=request.method,
            path=request.path,
            user_agent=request.headers.get("User-Agent", ""),
            query_string=request.query_string.decode("utf-8", "ignore"),
            referrer=request.headers.get("Referer", ""),
            accept_language=request.headers.get("Accept-Language", ""),
        )
        if not request.path.startswith("/static"):
            print(f"[HTTP] IP={source_ip} | {request.method} {request.path}")

    # Blueprints / simple routes
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.before_request
    def ensure_db():
        db.create_all()
        if Product.query.count() == 0:
            seed_products()

    def seed_products():
        sample = [
            Product(name="RTX 4090 Super", description="Flagship GPU, 24GB GDDR6X", price=1999.99, stock=5),
            Product(name="Ryzen 9 7950X3D", description="Top-tier CPU for gaming and content creation", price=699.0, stock=10),
            Product(name="ASUS ROG Strix Z790", description="High-end motherboard with PCIe5", price=379.99, stock=7),
            Product(name="Corsair Vengeance 32GB", description="DDR5 RAM kit", price=159.99, stock=20),
        ]
        db.session.bulk_save_objects(sample)
        admin = User(username="admin", email="admin@example.com", is_admin=True)
        admin.set_password("adminpass")
        db.session.add(admin)
        db.session.commit()

    @app.route("/")
    def index():
        products = Product.query.order_by(Product.id.desc()).all()
        return render_template("index.html", products=products)

    @app.route("/product/<int:product_id>")
    def product_detail(product_id):
        product = Product.query.get_or_404(product_id)
        return render_template("product.html", product=product)

    @app.route("/cart")
    def cart():
        cart = session.get("cart", {})
        items = []
        total = 0.0
        for pid, qty in cart.items():
            p = Product.query.get(int(pid))
            if p:
                items.append((p, qty))
                total += p.price * qty
        return render_template("cart.html", items=items, total=total)

    @app.route("/cart/add/<int:product_id>")
    def add_to_cart(product_id):
        cart = session.get("cart", {})
        cart[str(product_id)] = cart.get(str(product_id), 0) + 1
        session["cart"] = cart
        flash("Added to cart", "success")
        return redirect(request.referrer or url_for("index"))

    @app.route("/checkout", methods=["GET", "POST"])
    def checkout():
        if request.method == "POST":
            # mock checkout
            session.pop("cart", None)
            flash("Order placed (mock). Thank you!", "success")
            return redirect(url_for("index"))
        return render_template("checkout.html")

    # Auth blueprint-like handlers
    @app.route("/login", methods=["GET", "POST"])
    def login():
        from .models import User

        if request.method == "POST":
            email = request.form.get("email")
            password = request.form.get("password")
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                login_user(user)
                flash("Logged in successfully", "success")
                return redirect(url_for("dashboard"))
            flash("Invalid credentials", "danger")
        return render_template("login.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        from .models import User

        if request.method == "POST":
            username = request.form.get("username")
            email = request.form.get("email")
            password = request.form.get("password")
            if User.query.filter((User.email == email) | (User.username == username)).first():
                flash("User already exists", "warning")
                return redirect(url_for("register"))
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Account created — please log in", "success")
            return redirect(url_for("login"))
        return render_template("register.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Logged out", "info")
        return redirect(url_for("index"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        if current_user.is_authenticated and getattr(current_user, "is_admin", False):
            admin_path = app.config.get("MIRAGE_ADMIN_PATH", "/hidden-ops")
            admin_base = app.config.get("MIRAGE_ADMIN_BASE_URL")
            target = f"{admin_base}{admin_path}/attacks" if admin_base else f"{admin_path}/attacks"
            return redirect(target)
        return render_template("dashboard.html")

    return app


def create_app(test_config=None):
    app = create_shared_app(test_config)
    return app


def create_admin_app(test_config=None):
    app = create_shared_app(test_config)
    admin_path = app.config.get("MIRAGE_ADMIN_PATH", "/hidden-ops")
    app.config["PREFERRED_URL_SCHEME"] = "https"
    login_manager.login_view = "admin_login"
    app.login_manager.login_view = "admin_login"

    @app.route(f"{admin_path}/login", methods=["GET", "POST"])
    def admin_login():
        from .models import User

        if request.method == "POST":
            email = request.form.get("email")
            password = request.form.get("password")
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password) and user.is_admin:
                login_user(user)
                flash("Access granted", "success")
                return redirect(f"{admin_path}/attacks")
            flash("Invalid credentials", "danger")
        return render_template("admin_login.html")

    @app.route(f"{admin_path}/logout")
    @login_required
    def admin_logout():
        logout_user()
        flash("Session closed", "info")
        return redirect(f"{admin_path}/login")

    @app.route(f"{admin_path}/products")
    @login_required
    def admin_products():
        if not current_user.is_admin:
            flash("Admin only", "danger")
            return redirect(f"{admin_path}/login")
        from .models import Product

        products = Product.query.all()
        return render_template("admin_products.html", products=products)

    @app.route(f"{admin_path}/clear", methods=["POST"])
    @login_required
    def admin_clear_activity():
        if not current_user.is_admin:
            flash("Admin only", "danger")
            return redirect(f"{admin_path}/login")

        log_path = os.path.join(app.config["HONEYPOT_LOG_DIR"], "events.jsonl")
        log_file = os.path.join(app.config["HONEYPOT_LOG_DIR"], "mirage.log")
        for path in [log_path, log_file]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

        os.makedirs(app.config["HONEYPOT_LOG_DIR"], exist_ok=True)
        open(log_path, "a", encoding="utf-8").close()
        app.extensions["honeypot_logger"] = HoneypotLogger(log_dir=app.config["HONEYPOT_LOG_DIR"])
        flash("Activity log cleared", "success")
        return render_template(
            "attacker_dashboard.html",
            attacks=[],
            sessions=[],
            summary={
                "total_requests": 0,
                "unique_ips": 0,
                "top_paths": [],
                "top_ips": [],
                "suspicious_ips": 0,
                "top_methods": [],
                "top_user_agents": [],
                "suspicious_targets": [],
                "avg_requests_per_ip": 0,
                "most_active_ip": "None",
            },
            admin_path=admin_path,
            as_of=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        )

    @app.route(f"{admin_path}/export")
    @login_required
    def admin_export():
        if not current_user.is_admin:
            flash("Admin only", "danger")
            return redirect(f"{admin_path}/login")

        log_path = os.path.join(app.config["HONEYPOT_LOG_DIR"], "events.jsonl")
        attacks: List[Dict[str, Any]] = []
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if payload.get("event") == "http_request":
                        attacks.append(payload)
        return jsonify({"captured": len(attacks), "events": attacks[-200:]})

    @app.route(f"{admin_path}/attacks")
    @login_required
    def admin_attacks():
        if not current_user.is_admin:
            flash("Admin only", "danger")
            return redirect(f"{admin_path}/login")

        log_path = os.path.join(app.config["HONEYPOT_LOG_DIR"], "events.jsonl")
        attacks: List[Dict[str, Any]] = []
        sessions: Dict[str, Dict[str, Any]] = {}
        path_counter: Counter[str] = Counter()
        ip_counter: Counter[str] = Counter()
        method_counter: Counter[str] = Counter()
        user_agent_counter: Counter[str] = Counter()
        suspicious_path_counter: Counter[str] = Counter()
        suspicious_patterns = ["/wp-admin", "/phpmyadmin", "/admin", "/login", "/setup", ".env", "robots.txt", "/shell", "/api"]

        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if payload.get("event") != "http_request":
                        continue

                    source_ip = payload.get("source_ip", "unknown")
                    path = payload.get("path", "")
                    timestamp = payload.get("timestamp", "")
                    method = payload.get("method", "")
                    user_agent = payload.get("user_agent", "")
                    attacks.append(
                        {
                            "source_ip": source_ip,
                            "method": method,
                            "path": path,
                            "user_agent": user_agent,
                            "query_string": payload.get("query_string", ""),
                            "timestamp": timestamp,
                            "referrer": payload.get("referrer", ""),
                            "accept_language": payload.get("accept_language", ""),
                        }
                    )
                    path_counter[path] += 1
                    ip_counter[source_ip] += 1
                    method_counter[method] += 1
                    if user_agent:
                        user_agent_counter[user_agent] += 1
                    lowered_path = path.lower()
                    if any(pattern in lowered_path for pattern in suspicious_patterns):
                        suspicious_path_counter[path] += 1

                    session = sessions.setdefault(
                        source_ip,
                        {
                            "ip": source_ip,
                            "requests": 0,
                            "paths": [],
                            "user_agents": [],
                            "last_seen": timestamp,
                            "threat_score": 0,
                            "threat_level": "Low",
                        },
                    )
                    session["requests"] += 1
                    session["paths"].append(path)
                    if user_agent:
                        session["user_agents"].append(user_agent)
                    if time := timestamp:
                        if time > session["last_seen"]:
                            session["last_seen"] = time

        attacks = sorted(attacks, key=lambda item: item.get("timestamp", ""), reverse=True)
        sessions_list = sorted(sessions.values(), key=lambda item: item["requests"], reverse=True)
        for session in sessions_list:
            score = session["requests"] + len(set(session["paths"]))
            if session["requests"] >= 6:
                score += 3
            if any(path.lower().startswith("/wp") or path.lower().startswith("/admin") for path in session["paths"]):
                score += 2
            if score >= 10:
                session["threat_level"] = "Critical"
            elif score >= 6:
                session["threat_level"] = "High"
            elif score >= 3:
                session["threat_level"] = "Medium"
            else:
                session["threat_level"] = "Low"
            session["threat_score"] = score

        suspicious_ips = [session for session in sessions_list if session["requests"] >= 3]
        summary = {
            "total_requests": len(attacks),
            "unique_ips": len(ip_counter),
            "top_paths": path_counter.most_common(5),
            "top_ips": ip_counter.most_common(5),
            "suspicious_ips": len(suspicious_ips),
            "top_methods": method_counter.most_common(5),
            "top_user_agents": user_agent_counter.most_common(5),
            "suspicious_targets": suspicious_path_counter.most_common(5),
            "avg_requests_per_ip": round(len(attacks) / len(ip_counter), 2) if ip_counter else 0,
            "most_active_ip": sessions_list[0]["ip"] if sessions_list else "None",
        }
        return render_template(
            "attacker_dashboard.html",
            attacks=attacks[:200],
            sessions=sessions_list[:20],
            summary=summary,
            admin_path=admin_path,
            as_of=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        )

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
