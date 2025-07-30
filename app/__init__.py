from flask import Flask
from app.extensions import db, migrate, bcrypt,jwt
from app.controllers.auth.auth_controller import auth
from app.controllers.users.users_controller import users
from app.controllers.client.client_controller import client_bp
from app.controllers.Projects.projects_controller import projects
from app.controllers.orders.order_controller import order_bp
from app.controllers.services.service_controller import service_bp
from app.controllers.payments.payments_controller import payment_bp
from app.controllers.fileuploads.fileUpload_controller import file_upload_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    app.config["JWT_TOKEN_LOCATION"] = "headers"
    app.config["JWT_SECRET_KEY"] = "admin" 
    



    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)


    #importing models
    from app.models import user_model
    from app.models import service_model
    from app.models import project_model
    from app.models import payment_model
    from app.models import order_model
    from app.models import file_upload_model
    from app.models import client_model



    # Register blueprints here if needed
    app.register_blueprint(auth)
    app.register_blueprint(users)
    app.register_blueprint(client_bp)
    app.register_blueprint(projects)
    app.register_blueprint(order_bp)
    app.register_blueprint(service_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(file_upload_bp)



    @app.route('/')
    def home():
     return 'Kayzonale Prnits and Designs Backend API is running 🚀'

    return app


