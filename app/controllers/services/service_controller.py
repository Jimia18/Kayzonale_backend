from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models.service_model import Service
from app.decorators import roles_required
from status_codes import HTTP_400_BAD_REQUEST, HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR

service_bp = Blueprint("service_bp", __name__, url_prefix="/api/v1/services")

# ------------------ CREATE SERVICE ------------------ #
@service_bp.route("/create", methods=["POST"])
@jwt_required()
@roles_required("admin")
def create_service():
    data = request.get_json()
    try:
        new_service = Service(
            name=data["name"],
            price=data["price"],
            description=data.get("description")
        )
        db.session.add(new_service)
        db.session.commit()
        return jsonify({"message": "Service created", "id": new_service.service_id}), HTTP_200_OK
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR
    
    # ------------------ GET ALL SERVICES ------------------ #
@service_bp.route("/", methods=["GET"])
@jwt_required()
def get_services():
    services = Service.query.all()
    return jsonify([
        {
            "id": s.service_id,
            "name": s.name,
            "description": s.description,
            "price": s.price
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
        "price": service.price
    }), HTTP_200_OK

# ------------------ UPDATE SERVICE ------------------ #
@service_bp.route("/update/<int:service_id>", methods=["PUT", "PATCH"])
@jwt_required()
@roles_required("admin")
def update_service(service_id):
    data = request.get_json()
    service = Service.query.get(service_id)
    if not service:
        return jsonify({"error": "Service not found"}), HTTP_404_NOT_FOUND
    try:
        if data.get("name"):
            service.name = data["name"]
        if data.get("description"):
            service.description = data["description"]
        if data.get("price") is not None:
            service.price = data["price"]

        db.session.commit()
        return jsonify({"message": "Service updated"}), HTTP_200_OK
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR

# ------------------ DELETE SERVICE ------------------ #
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
