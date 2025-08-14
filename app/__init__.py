import os
from flask import Flask, send_from_directory
from dotenv import load_dotenv
from flask_cors import CORS
from flask_mail import Mail
from app.extensions import db, migrate, bcrypt, jwt
from app.controllers.auth.auth_controller import auth
from app.controllers.users.users_controller import users
from app.controllers.client.client_controller import client_bp
from app.controllers.Projects.projects_controller import projects
from app.controllers.orders.order_controller import order_bp
from app.controllers.services.service_controller import service_bp
from app.controllers.payments.payments_controller import payment_bp
from app.controllers.fileuploads.fileUpload_controller import file_upload_bp
from app.controllers.products.products_controller import product_bp

mail = Mail()

def create_app():
    load_dotenv()

    # Paths
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))  # FIXED HERE
    STATIC_FOLDER = os.path.join(BASE_DIR, '..', 'static')
    UPLOAD_FOLDER = os.path.join(STATIC_FOLDER, 'uploads', 'products')

    app = Flask(__name__)
    app.config.from_object('config.Config')
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    # Serve uploaded product images
    @app.route('/uploads/products/<filename>')
    def uploaded_file(filename):
        return send_from_directory(os.path.join(app.static_folder, 'uploads/products'), filename)
    
    CORS(
        app,
        resources={r"/api/*": {"origins": "http://localhost:3000"}},
        supports_credentials=True,
        allow_headers=['content-Type', 'Authorization']
    )

    app.config["JWT_TOKEN_LOCATION"] = "headers"
    app.config["JWT_SECRET_KEY"] = "admin"

    # Flask mail
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.getenv('EMAIL_ADDRESS')
    app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = 'Kayzonaledesigns@gmail.com'

    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)

    # Import models
    from app.models import user_model, service_model, project_model, payment_model, order_model
    from app.models import file_upload_model, client_model, product_model, orderItem_model

    # Register blueprints
    app.register_blueprint(auth, url_prefix='/api/v1/auth')
    app.register_blueprint(users, url_prefix='/api/v1/users')
    app.register_blueprint(client_bp, url_prefix='/api/v1/clients')
    app.register_blueprint(projects, url_prefix='/api/v1/projects')
    app.register_blueprint(order_bp, url_prefix='/api/v1/orders')
    app.register_blueprint(service_bp, url_prefix='/api/v1/services')
    app.register_blueprint(payment_bp, url_prefix='/api/v1/payments')
    app.register_blueprint(file_upload_bp, url_prefix='/api/v1/file_uploads')
    app.register_blueprint(product_bp, url_prefix='/api/v1/products')

    @app.route('/')
    def home():
        return 'Kayzonale Prints and Designs Backend API is running 🚀'

    return app
