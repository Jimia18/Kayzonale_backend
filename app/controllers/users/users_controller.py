from flask import Blueprint, request, jsonify
from status_codes import (
    HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND, HTTP_409_CONFLICT, HTTP_500_INTERNAL_SERVER_ERROR
)
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.user_model import User
from app.extensions import db, bcrypt
from sqlalchemy import or_

users = Blueprint('users', __name__, url_prefix='/api/v1/users')


# ------------------ GET ALL USERS ------------------ #
@users.get('/')
@jwt_required()
def get_all_users():
    try:
        query = User.query

        # Optional filters
        user_type = request.args.get("type")
        email = request.args.get("email")
        name = request.args.get("name")
        sort = request.args.get("sort", "asc")  # 'asc' or 'desc'

        if user_type:
            query = query.filter_by(user_type=user_type)

        if email:
            query = query.filter(User.email.ilike(f"%{email}%"))

        if name:
            query = query.filter(or_(
                User.first_name.ilike(f"%{name}%"),
                User.last_name.ilike(f"%{name}%")
            ))
        # Sorting
        if sort == "desc":
            query = query.order_by(User.created_at.desc())
        else:
            query = query.order_by(User.created_at.asc())

        users_data = [
            {
                'id': user.user_id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.get_full_name(),
                'email': user.email,
                'contact': user.contact,
                'type': user.user_type,
                'created_at': user.created_at
            } for user in query.all()
        ]

        return jsonify({
            'message': 'Users retrieved successfully',
            'total_users': len(users_data),
            'users': users_data
        }), HTTP_200_OK

    except Exception as e:
        return jsonify({'error': str(e)}), HTTP_500_INTERNAL_SERVER_ERROR


# ------------------ GET USER BY ID ------------------ #
@users.get('/<int:id>')
@jwt_required()
def get_user_by_id(id):
    try:
        user = User.query.filter_by(user_id=id).first()
        if not user:
            return jsonify({'error': 'User not found'}), HTTP_404_NOT_FOUND

        return jsonify({
            'message': 'User retrieved successfully',
            'user': {
                'id': user.user_id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.get_full_name(),
                'email': user.email,
                'contact': user.contact,
                'type': user.user_type,
                'created_at': user.created_at
            }
        }), HTTP_200_OK

    except Exception as e:
        return jsonify({'error': str(e)}), HTTP_500_INTERNAL_SERVER_ERROR


# ------------------ UPDATE USER ------------------ #
@users.route('/edit/<int:id>', methods=['PUT', 'PATCH'])
@jwt_required()
def update_user(id):
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.filter_by(user_id=current_user_id).first()
        user = User.query.filter_by(user_id=id).first()

        if not user:
            return jsonify({'error': 'User not found'}), HTTP_404_NOT_FOUND

        # Admins can update anyone, users can only update themselves
        if current_user.user_type != 'admin' and current_user.user_id != user.user_id:
            return jsonify({'error': 'You are not authorized to update this user'}), HTTP_403_FORBIDDEN

        data = request.get_json()

        # Update fields
        if data.get('first_name'):
            user.first_name = data['first_name']
        if data.get('last_name'):
            user.last_name = data['last_name']
        if data.get('user_type') and current_user.user_type == 'admin':
            user.user_type = data['user_type']

        # Email conflict check
        if data.get('email') and data['email'] != user.email:
            if User.query.filter_by(email=data['email']).first():
                return jsonify({'error': 'Email already in use'}), HTTP_409_CONFLICT
            user.email = data['email']

        # Contact conflict check
        if data.get('contact') and data['contact'] != user.contact:
            if User.query.filter_by(contact=data['contact']).first():
                return jsonify({'error': 'Contact already in use'}), HTTP_409_CONFLICT
            user.contact = data['contact']

        # Password update
        if data.get('password'):
            user.password = bcrypt.generate_password_hash(data['password']).decode('utf-8')

        db.session.commit()

        return jsonify({
            'message': f"{user.get_full_name()}'s details updated successfully",
            'user': {
                'id': user.user_id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'contact': user.contact,
                'type': user.user_type,
                    }
        }), HTTP_200_OK

    except Exception as e:
        return jsonify({'error': str(e)}), HTTP_500_INTERNAL_SERVER_ERROR


# ------------------ DELETE USER (ADMIN ONLY) ------------------ #
@users.route('/delete/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_user(id):
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.filter_by(user_id=current_user_id).first()

        if current_user.user_type != 'admin':
            return jsonify({'error': 'Only admins can delete users'}), HTTP_403_FORBIDDEN

        user = User.query.filter_by(user_id=id).first()
        if not user:
            return jsonify({'error': 'User not found'}), HTTP_404_NOT_FOUND

        db.session.delete(user)
        db.session.commit()

        return jsonify({'message': f'{user.get_full_name()} has been deleted successfully'}), HTTP_200_OK

    except Exception as e:
        return jsonify({'error': str(e)}), HTTP_500_INTERNAL_SERVER_ERROR
