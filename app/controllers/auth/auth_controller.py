from flask import Blueprint, request, jsonify, current_app
from status_codes import (
    HTTP_400_BAD_REQUEST, HTTP_409_CONFLICT, HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_201_CREATED, HTTP_401_UNAUTHORIZED, HTTP_200_OK
)
import validators
from app.models.user_model import User
from app.models.client_model import Client
from app.extensions import mail, db, bcrypt, cors
from flask_mail import Message
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)
from datetime import datetime

# Define the blueprint only once
auth = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

# ------------------ REGISTER ------------------ #
@auth.route("/register", methods=["POST"])
def register_user():
    data = request.get_json()
    
    # Required fields
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    email = data.get("email")
    contact = data.get("contact")
    password = data.get("password")
    user_type = data.get("user_type", "client")  # Default to client
    
    # Optional fields
    company_name = data.get("company_name", "")
    address = data.get("address", "")
    super_key = data.get("super_key")  # Only required for admin registration

    # Validation
    if not all([first_name, last_name, email, contact, password]):
        return jsonify({"error": "All required fields must be provided"}), HTTP_400_BAD_REQUEST

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), HTTP_400_BAD_REQUEST

    if not validators.email(email):
        return jsonify({"error": "Invalid email format"}), HTTP_400_BAD_REQUEST

    # Check for existing user
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already in use"}), HTTP_409_CONFLICT

    if User.query.filter_by(contact=contact).first():
        return jsonify({"error": "Phone number already in use"}), HTTP_409_CONFLICT

    # Admin registration validation
    if user_type == "admin":
        if not super_key:
            return jsonify({"error": "Super key required for admin registration"}), HTTP_400_BAD_REQUEST
        if super_key != current_app.config.get("SUPER_KEY"):
            return jsonify({"error": "Invalid super key"}), HTTP_401_UNAUTHORIZED

    try:
        # Hash password before storin
       ## hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        ## hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        hashed_password = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
        
        # Create user with hashed password
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            contact=contact,
            password=hashed_password,  # Store hashed password
            user_type=user_type
        )
        db.session.add(new_user)
        db.session.commit()

        # Create client record if user is client
        if user_type == "client":
            new_client = Client(
                user_id=new_user.user_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                contact=contact,
                company_name=company_name,
                address=address,
                created_at=datetime.utcnow()
            )
            db.session.add(new_client)
            db.session.commit()

        return jsonify({
            "message": f"{new_user.first_name} {new_user.last_name} registered successfully as {user_type}",
            "user": {
                "id": new_user.user_id,
                "name": f"{new_user.first_name} {new_user.last_name}",
                "email": new_user.email,
                "user_type": new_user.user_type,
                "created_at": new_user.created_at.isoformat()
            }
        }), HTTP_201_CREATED

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Registration error: {str(e)}")
        return jsonify({"error": "An error occurred during registration"}), HTTP_500_INTERNAL_SERVER_ERROR


# ------------------ LOGIN ------------------ #
@auth.route("/login", methods=["POST"])
def login():
    email = request.json.get("email")
    password = request.json.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), HTTP_400_BAD_REQUEST

    try:
        user = User.query.filter_by(email=email).first()

        if not user:
            return jsonify({"error": "Invalid credentials"}), HTTP_401_UNAUTHORIZED

        if not bcrypt.check_password_hash(user.password, password):
            return jsonify({"error": "Invalid credentials"}), HTTP_401_UNAUTHORIZED

        # Create tokens
        access_token = create_access_token(identity=str(user.user_id))
        refresh_token = create_refresh_token(identity=str(user.user_id))

        return jsonify({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user.user_id,
                "name": f"{user.first_name} {user.last_name}",
                "email": user.email,
                "user_type": user.user_type
            }
        }), HTTP_200_OK

    except Exception as e:
        current_app.logger.error(f"Login error: {str(e)}")
        return jsonify({"error": "An error occurred during login"}), HTTP_500_INTERNAL_SERVER_ERROR


# ------------------ TOKEN REFRESH ------------------ #
@auth.route("/token/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    try:
        identity = get_jwt_identity()
        access_token = create_access_token(identity=identity)
        return jsonify({"access_token": access_token}), HTTP_200_OK
    except Exception as e:
        current_app.logger.error(f"Token refresh error: {str(e)}")
        return jsonify({"error": "Unable to refresh token"}), HTTP_500_INTERNAL_SERVER_ERROR