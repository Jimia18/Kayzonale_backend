import os
from flask import Flask, send_from_directory,render_template_string
from dotenv import load_dotenv
from flask_cors import CORS
from flask_mail import Mail

from app.extensions import db, migrate, bcrypt, jwt,cors
from app.controllers.auth.auth_controller import auth
from app.controllers.users.users_controller import users
from app.controllers.client.client_controller import client_bp
from app.controllers.orders.order_controller import order_bp
from app.controllers.services.service_controller import service_bp
from app.controllers.payments.payments_controller import payment_bp
from app.controllers.products.products_controller import product_bp

mail = Mail()

def create_app():
    load_dotenv()

    # --- Paths ---
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    STATIC_FOLDER = os.path.join(BASE_DIR, '..', 'static')
    UPLOAD_FOLDER = os.path.join(STATIC_FOLDER, 'uploads', 'products','services')
    

    app = Flask(__name__, static_url_path='/static', static_folder=STATIC_FOLDER)
    app.config.from_object('config.Config')
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    # Serve uploaded product images
    @app.route('/uploads/products/<filename>')
    def uploaded_file(filename):
        return send_from_directory(os.path.join(app.static_folder, 'uploads/products'), filename)
    
    # Serve uploaded service images
    @app.route('/uploads/services/<filename>')
    def uploaded_service_file(filename):
        return send_from_directory(os.path.join(app.static_folder, 'uploads/services'), filename)


    # ---------------- CORS ----------------
    CORS(
        app,
        resources={r"/api/*": {"origins": "http://localhost:3000"}},
        methods=["GET","POST","PUT","PATCH","DELETE"], 
        supports_credentials=True,
        allow_headers=['Content-Type', 'Authorization']
    )

    # ---------------- Mail ----------------
    app.config.update(
        MAIL_SERVER='smtp.gmail.com',
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME=os.getenv('EMAIL_ADDRESS'),
        MAIL_PASSWORD=os.getenv('EMAIL_PASSWORD'),
        MAIL_DEFAULT_SENDER=os.getenv('MAIL_DEFAULT_SENDER', 'Kayzonaledesigns@gmail.com')
    )
    mail.init_app(app)

    # ---------------- Extensions ----------------
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)
    # Note: you already used CORS above; no need for `cors.init_app(app)`

    # ---------------- Models ----------------
    from app.models import (
        user_model, service_model,payment_model, order_model, 
        client_model, product_model, orderItem_model
    )

    # ---------------- Blueprints ----------------
    blueprints = [
        (auth, '/api/v1/auth'),
        (users, '/api/v1/users'),
        (client_bp, '/api/v1/clients'),
        (order_bp, '/api/v1/orders'),
        (service_bp, '/api/v1/services'),
        (payment_bp, '/api/v1/payments'),
        (product_bp, '/api/v1/products')
    ]
    for blueprint, url_prefix in blueprints:
        app.register_blueprint(blueprint, url_prefix=url_prefix)

    # ---------------- Home ----------------
    @app.route('/')
    def home():
        return 'Kayzonale Prints and Designs Backend API is running 🚀'

    return app
