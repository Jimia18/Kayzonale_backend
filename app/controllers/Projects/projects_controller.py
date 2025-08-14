from flask import Blueprint, request, jsonify
from datetime import datetime
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_cors import cross_origin
from app.decorators import roles_required
from app.extensions import db
from app.models.project_model import Project
from app.models.user_model import User
from status_codes import (
    HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_403_FORBIDDEN,
    HTTP_200_OK, HTTP_201_CREATED
)

# Blueprint setup
projects = Blueprint('projects', __name__, url_prefix='/api/v1/projects')

# -------------------- CREATE PROJECT -------------------- #
@projects.route('/', methods=['POST'])
@jwt_required()
@cross_origin()
def create_project():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if user.user_type not in ["admin", "staff"]:
            return jsonify({"error": "Access denied"}), HTTP_403_FORBIDDEN

        data = request.get_json()
        
        # Validate required fields
        if not data.get('title') or not data.get('client_id'):
            return jsonify({"error": "Title and client_id are required"}), HTTP_400_BAD_REQUEST

        # Parse deadline if provided
        deadline = None
        if data.get('deadline'):
            try:
                deadline = datetime.strptime(data['deadline'], "%Y-%m-%d")
            except ValueError:
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), HTTP_400_BAD_REQUEST

        project = Project(
            client_id=data['client_id'],
            user_id=data.get('user_id', current_user_id),
            title=data['title'],
            description=data.get('description', ''),
            category=data.get('category', 'General'),
            status=data.get('status', 'Concept'),
            deadline=deadline,
            price=data.get('price', 0),
            payment_status=data.get('payment_status', 'Unpaid'),
            delivery_status=data.get('delivery_status', 'Pending'),
            created_at=datetime.utcnow()
        )
        
        db.session.add(project)
        db.session.commit()
        return jsonify({
            "message": "Project created",
            "project_id": project.project_id,
            "project": project.to_dict()
        }), HTTP_201_CREATED

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_400_BAD_REQUEST

# -------------------- GET ALL PROJECTS -------------------- #
@projects.route('/', methods=['GET'])
@jwt_required()
@cross_origin()
def get_all_projects():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if user.user_type == "admin":
            projects = Project.query.all()
        elif user.user_type == "staff":
            projects = Project.query.filter_by(user_id=current_user_id).all()
        else:
            return jsonify({"error": "Access denied"}), HTTP_403_FORBIDDEN

        return jsonify([p.to_dict() for p in projects]), HTTP_200_OK
    except Exception as e:
        return jsonify({"error": str(e)}), HTTP_400_BAD_REQUEST

# -------------------- GET PROJECT BY ID -------------------- #
@projects.route('/<int:project_id>', methods=['GET'])
@jwt_required()
@cross_origin()
def get_project(project_id):
    try:
        project = Project.query.get_or_404(project_id)
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        # Check access rights
        if user.user_type not in ["admin"] and project.user_id != current_user_id:
            return jsonify({"error": "Access denied"}), HTTP_403_FORBIDDEN

        return jsonify(project.to_dict()), HTTP_200_OK
    except Exception as e:
        return jsonify({"error": str(e)}), HTTP_400_BAD_REQUEST

# -------------------- UPDATE PROJECT -------------------- #
@projects.route('/<int:project_id>', methods=['PUT'])
@jwt_required()
@cross_origin()
def update_project(project_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        project = Project.query.get_or_404(project_id)

        # Check permissions
        if user.user_type != "admin" and project.user_id != current_user_id:
            return jsonify({"error": "Unauthorized access"}), HTTP_403_FORBIDDEN

        data = request.get_json()
        
        # Update fields
        updatable_fields = [
            'title', 'description', 'status', 'category',
            'payment_status', 'delivery_status', 'price'
        ]
        
        for field in updatable_fields:
            if field in data:
                setattr(project, field, data[field])

        if 'deadline' in data:
            try:
                project.deadline = datetime.strptime(data['deadline'], "%Y-%m-%d")
            except ValueError:
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), HTTP_400_BAD_REQUEST

        project.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            "message": "Project updated successfully",
            "project": project.to_dict()
        }), HTTP_200_OK
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_400_BAD_REQUEST

# -------------------- DELETE PROJECT -------------------- #
@projects.route('/<int:project_id>', methods=['DELETE'])
@jwt_required()
@roles_required('admin')
@cross_origin()
def delete_project(project_id):
    try:
        project = Project.query.get_or_404(project_id)
        db.session.delete(project)
        db.session.commit()
        return jsonify({"message": "Project deleted successfully"}), HTTP_200_OK
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_400_BAD_REQUEST