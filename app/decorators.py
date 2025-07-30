from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask import jsonify
from app.models.user_model import User

def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Ensure JWT is present and valid
            verify_jwt_in_request()
            user_id = get_jwt_identity()

            # Fetch user from DB
            user = User.query.get(user_id)

            # Check if user exists and role is allowed
            if not user or user.user_type not in roles:
                return jsonify({"error": "Access denied: insufficient privileges"}), 401

            return fn(*args, **kwargs)
        return wrapper
    return decorator
