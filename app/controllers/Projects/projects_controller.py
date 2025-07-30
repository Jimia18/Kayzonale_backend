
from flask import Blueprint,request,jsonify
from datetime import datetime
from app.decorators import roles_required
from status_codes import HTTP_400_BAD_REQUEST,HTTP_409_CONFLICT,HTTP_500_INTERNAL_SERVER_ERROR,HTTP_201_CREATED,HTTP_401_UNAUTHORIZED,HTTP_200_OK,HTTP_404_NOT_FOUND,HTTP_403_FORBIDDEN
import validators
from app.models.project_model import Project
from app.models.client_model import Client
from app.extensions import db,bcrypt
from flask_jwt_extended import create_access_token,create_refresh_token,jwt_required,get_jwt_identity

# project blueprint
projects= Blueprint('projects', __name__,url_prefix='/api/v1/projects')

#creating projects
@projects.route('/create', methods=['POST'])
@jwt_required()
def create_project():
    data = request.get_json()
    try:
        project = Project(
            client_id=data['client_id'],
            title=data['title'],
            description=data.get('description'),
            category=data.get('category'),
            status=data.get('status', 'Concept'),
            deadline=datetime.strptime(data['deadline'], "%Y-%m-%d") if data.get('deadline') else None,
            price=data.get('price'),
            payment_status=data.get('payment_status', 'Unpaid'),
            delivery_status=data.get('delivery_status', 'Pending'),
            created_at=datetime.utcnow()
        )
        db.session.add(project)
        db.session.commit()
        return jsonify({"message": "Project created", "project_id": project.project_id}), HTTP_200_OK
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_400_BAD_REQUEST

# getting all projects
@projects.route('/', methods=['GET'])
@jwt_required()
def get_all_projects():
    projects = Project.query.all()
    return jsonify([
        {
            "id": p.project_id,
            "title": p.title,
            "status": p.status,
            "client_id": p.client_id,
            "deadline": p.deadline.isoformat() if p.deadline else None
        } for p in projects
    ]), HTTP_200_OK

# getting a specific project by ID
@projects.route('/<int:id>', methods=['GET'])
@jwt_required()
def get_project(id):
    project = Project.query.get(id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    return jsonify({
        "id": project.project_id,
        "title": project.title,
        "description": project.description,
        "status": project.status,
        "client_id": project.client_id,
        "deadline": project.deadline.isoformat() if project.deadline else None,
        "created_at": project.created_at.isoformat()
    }), HTTP_200_OK

# updating a specific project by ID
@projects.route('/edit/<int:id>', methods=['PUT'])
@jwt_required()
def update_project(id):
    project = Project.query.get(id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    data = request.get_json()

    project.title = data.get('title', project.title)
    project.description = data.get('description', project.description)
    project.status = data.get('status', project.status)
    if data.get('deadline'):
        project.deadline = datetime.strptime(data['deadline'], "%Y-%m-%d")
    project.updated_at = datetime.utcnow()

    db.session.commit()
    return jsonify({"message": "Project updated successfully"}), HTTP_200_OK

# deleting a specific project by ID
@projects.route('/delete/<int:id>', methods=['DELETE'])
@jwt_required()
@roles_required('admin')
def delete_project(id):
    project = Project.query.get(id)
    if not project:
        return jsonify({"error": "Project not found"}), HTTP_404_NOT_FOUND

    db.session.delete(project)
    db.session.commit()
    return jsonify({"message": "Project deleted"}), HTTP_200_OK

