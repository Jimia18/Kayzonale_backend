import os
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models.service_model import Service
from app.decorators import roles_required
from uuid import uuid4
from status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR

service_bp = Blueprint("service_bp", __name__, url_prefix="/api/v1/services")

UPLOAD_FOLDER = os.path.join("static", "uploads", "services")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif",'avif'}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ------------------ CREATE SERVICE (ADMIN) ------------------ #
@service_bp.route("/create", methods=["POST"])
@jwt_required()
@roles_required("admin")
def create_service():
    try:
        name = request.form["name"]
        description = request.form.get("description")
        file = request.files.get("image")

        image_url = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid4().hex}_{filename}"
            upload_folder = os.path.join(current_app.root_path, "..", UPLOAD_FOLDER)
            os.makedirs(upload_folder, exist_ok=True)
            save_path = os.path.join(upload_folder, unique_filename)
            file.save(save_path)
            image_url = f"/{UPLOAD_FOLDER}/{unique_filename}".replace("\\", "/")

        new_service = Service(name=name, description=description, image_url=image_url)
        db.session.add(new_service)
        db.session.commit()

        return jsonify({"message": "Service created", "id": new_service.service_id}), HTTP_200_OK
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR


# ------------------ GET ALL SERVICES (DASHBOARD) ------------------ #
@service_bp.route("/", methods=["GET"])
@jwt_required()
def get_services():
    services = Service.query.all()
    return jsonify([
        {
            "id": s.service_id,
            "name": s.name,
            "description": s.description,
            "image_url": s.image_url
        } for s in services
    ]), HTTP_200_OK


# ------------------ GET SERVICE BY ID ------------------ #
@service_bp.route("/<int:service_id>", methods=["GET"])
@jwt_required()
def get_service(service_id):
    service = Service.query.get(service_id)
    if not service:
        return jsonify({"error": "Service not found"}), HTTP_404_NOT_FOUND
    return jsonify({
        "id": service.service_id,
        "name": service.name,
        "description": service.description,
        "image_url": service.image_url
    }), HTTP_200_OK


# ------------------ UPDATE SERVICE (ADMIN) ------------------ #
@service_bp.route("/update/<int:service_id>", methods=["PUT", "PATCH"])
@jwt_required()
@roles_required("admin")
def update_service(service_id):
    service = Service.query.get(service_id)
    if not service:
        return jsonify({"error": "Service not found"}), HTTP_404_NOT_FOUND
    try:
        service.name = request.form.get("name", service.name)
        service.description = request.form.get("description", service.description)

        file = request.files.get("image")
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid4().hex}_{filename}"
            upload_folder = os.path.join(current_app.root_path, "..", UPLOAD_FOLDER)
            os.makedirs(upload_folder, exist_ok=True)
            save_path = os.path.join(upload_folder, unique_filename)
            file.save(save_path)
            service.image_url = f"/{UPLOAD_FOLDER}/{unique_filename}".replace("\\", "/")

        db.session.commit()
        return jsonify({"message": "Service updated"}), HTTP_200_OK
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR


# ------------------ DELETE SERVICE (ADMIN) ------------------ #
@service_bp.route("/delete/<int:service_id>", methods=["DELETE"])
@jwt_required()
@roles_required("admin")
def delete_service(service_id):
    service = Service.query.get(service_id)
    if not service:
        return jsonify({"error": "Service not found"}), HTTP_404_NOT_FOUND
    try:
        db.session.delete(service)
        db.session.commit()
        return jsonify({"message": "Service deleted"}), HTTP_200_OK
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR


# ------------------ PUBLIC SERVICES (FRONTEND) ------------------ #
@service_bp.route("/public", methods=["GET"])
def get_public_services():
    services = Service.query.all()
    return jsonify([
        {
            "id": s.service_id,
            "title": s.name,
            "description": s.description,
            "src": s.image_url,
            "alt": s.name
        } for s in services
    ]), HTTP_200_OK
