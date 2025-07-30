from flask import Blueprint, request, jsonify,current_app
from status_codes import HTTP_400_BAD_REQUEST,HTTP_409_CONFLICT,HTTP_500_INTERNAL_SERVER_ERROR,HTTP_201_CREATED,HTTP_401_UNAUTHORIZED,HTTP_200_OK,HTTP_404_NOT_FOUND,HTTP_403_FORBIDDEN
import validators
from app.models.user_model import User
from app.extensions import db, bcrypt
from flask_jwt_extended import create_access_token,create_refresh_token,jwt_required,get_jwt_identity

auth = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

# ------------------ REGISTER ------------------ #
@auth.route("/register", methods=["POST"])
def register_user():
    data = request.json
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    contact = data.get("contact")
    email = data.get("email")
    user_type = data.get("user_type", "staff")
    password = data.get("password")
    super_key = data.get("super_key")  # for admin
    biography = data.get("biography", "") if user_type == "staff" else ""

    if not first_name or not last_name or not contact or not password or not email:
        return jsonify({"error": "All fields are required"}), HTTP_400_BAD_REQUEST

    if user_type == "staff" and not biography:
        return jsonify({"error": "Enter your biography"}), HTTP_400_BAD_REQUEST

    if len(password) < 8:
        return jsonify({"error": "Password is too short"}), HTTP_400_BAD_REQUEST

    if not validators.email(email):
        return jsonify({"error": "Email is invalid"}), HTTP_400_BAD_REQUEST

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email address already in use"}), HTTP_409_CONFLICT

    if User.query.filter_by(contact=contact).first():
        return jsonify({"error": "Contact already in use"}), HTTP_409_CONFLICT

    if user_type == "admin":
        if not super_key:
            return jsonify({"error": "Super key is required to create an admin account"}), HTTP_400_BAD_REQUEST
        if super_key != current_app.config.get("SUPER_KEY"):
            return jsonify({"error": "Invalid super key"}), HTTP_401_UNAUTHORIZED

    try:
        # Pass raw password, hashing happens in User model
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            password=password,
            email=email,
            contact=contact,
            biography=biography,
            user_type=user_type
        )

        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            "message": f"{new_user.get_full_name()} has been registered as a {new_user.user_type}.",
            "user": {
                "id": new_user.user_id,
                "first_name": new_user.first_name,
                "last_name": new_user.last_name,
                "email": new_user.email,
                "contact": new_user.contact,
                "type": new_user.user_type,
                "biography": new_user.biography,
                "created_at": new_user.created_at.isoformat()
            }
        }), HTTP_201_CREATED

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR


# ------------------ LOGIN ------------------ #
@auth.route("/login", methods=["POST"])
def login():
    email = request.json.get("email")
    password = request.json.get("password")

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), HTTP_400_BAD_REQUEST

    try:
        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            access_token = create_access_token(identity=str(user.user_id))
            refresh_token = create_refresh_token(identity=str(user.user_id)) 


            return jsonify({
                "user": {
                    "id": user.user_id,
                    "username": user.get_full_name(),
                    "email": user.email,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "type": user.user_type
                },
                "message": "You have successfully logged into your account"
            }), HTTP_200_OK
        else:
            return jsonify({"message": "Invalid email or password"}), HTTP_401_UNAUTHORIZED

    except Exception as e:
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR


# ------------------ TOKEN REFRESH ------------------ #
@auth.route("/token/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    try:
        identity = get_jwt_identity()
        access_token = create_access_token(identity=identity)
        return jsonify({"access_token": access_token})
    except Exception as e:
        print(f"Refresh token error: {str(e)}")
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR
