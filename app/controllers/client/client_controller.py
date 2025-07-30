from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.client_model import Client
from app.decorators import roles_required
from flask_jwt_extended import jwt_required
from datetime import datetime
from status_codes import HTTP_400_BAD_REQUEST, HTTP_201_CREATED, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR 

client_bp = Blueprint("client_bp", __name__, url_prefix="/api/v1/clients")


@client_bp.route("/create", methods=["POST"])
@jwt_required()
@roles_required("admin")
def create_client():
    data = request.get_json()

    if not data.get("first_name") or not data.get("last_name") or not data.get("contact"):
        return jsonify({"error": "first_name, last_name, and contact are required"}), HTTP_400_BAD_REQUEST

    try:
        client = Client(
            company_name=data.get("company_name"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            email=data.get("email"),
            contact=data.get("contact"),
            address=data.get("address"),
            created_at=datetime.utcnow(),
        )
        db.session.add(client)
        db.session.commit()
        return jsonify({"message": "Client created successfully", 
                        "client_id": client.client_id,"company_name": client.company_name}), HTTP_201_CREATED
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}),HTTP_400_BAD_REQUEST

##getting all clients
@client_bp.route("/", methods=["GET"])
@jwt_required()
@roles_required("admin", "staff")
def get_clients():
    clients = Client.query.all()
    result = [
        {
            "client_id": c.client_id,
            "full_name": c.get_full_name(),
            "email": c.email,
            "contact": c.contact,
            "company_name": c.company_name,
            "address": c.address,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in clients
    ]
    return jsonify(result)

# getting a specific client by ID
@client_bp.route("/<int:client_id>", methods=["GET"])
@jwt_required()
@roles_required("admin", "staff")
def get_client(client_id):
    client = Client.query.get_or_404(client_id)
    return jsonify(
        {
            "client_id": client.client_id,
            "full_name": client.get_full_name(),
            "email": client.email,
            "contact": client.contact,
            "company_name": client.company_name,
            "address": client.address,
            "created_at": client.created_at.isoformat() if client.created_at else None,
        }
    )

# updating a specific client by ID
@client_bp.route("/<int:client_id>", methods=["PUT, PATCH"])
@jwt_required()
@roles_required("admin")
def update_client(client_id):
    client = Client.query.get_or_404(client_id)
    data = request.get_json()

    client.company_name = data.get("company_name", client.company_name)
    client.first_name = data.get("first_name", client.first_name)
    client.last_name = data.get("last_name", client.last_name)
    client.email = data.get("email", client.email)
    client.contact = data.get("contact", client.contact)
    client.address = data.get("address", client.address)
    client.updated_at = datetime.utcnow()

    try:
        db.session.commit()
        return jsonify({"message": "Client updated successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_400_BAD_REQUEST

#deleting a specific client by ID
@client_bp.route("/<int:client_id>", methods=["DELETE"])
@jwt_required()
@roles_required("admin")
def delete_client(client_id):
    client = Client.query.get_or_404(client_id)
    try:
        db.session.delete(client)
        db.session.commit()
        return jsonify({"message": "Client deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_400_BAD_REQUEST
