import os
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models.product_model import Product
from app.decorators import roles_required
from uuid import uuid4
from status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR

product_bp = Blueprint("product_bp", __name__, url_prefix="/api/v1/products")

UPLOAD_FOLDER = "static/uploads/products"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ------------------ CREATE PRODUCT ------------------ #
@product_bp.route("/create", methods=["POST"])
@jwt_required()
@roles_required("admin")
def create_product():
    try:
        title = request.form["title"]
        description = request.form.get("description")
        category = request.form.get("category")
        price = request.form.get("price")
        user_id = get_jwt_identity()  # <-- FIXED

        file = request.files.get("image")
        image_path = None

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid4().hex}_{filename}"
            save_folder = os.path.join(current_app.root_path, "..", UPLOAD_FOLDER)
            os.makedirs(save_folder, exist_ok=True)
            file.save(os.path.join(save_folder, unique_filename))
            image_path = f"{UPLOAD_FOLDER}/{unique_filename}"

        product = Product(
            title=title,
            description=description,
            category=category,
            price=price,
            user_id=user_id,
            image=image_path
        )

        db.session.add(product)
        db.session.commit()
        return jsonify({"message": "Product created", "id": product.id}), HTTP_200_OK
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR


# ------------------ GET ALL PRODUCTS ------------------ #
@product_bp.route("/", methods=["GET"])
@jwt_required()
def get_products():
    products = Product.query.all()
    return jsonify([p.to_dict() for p in products]), HTTP_200_OK

# ------------------ GET PRODUCT BY ID ------------------ #
@product_bp.route("/<int:product_id>", methods=["GET"])
@jwt_required()
def get_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), HTTP_404_NOT_FOUND
    return jsonify(product.to_dict()), HTTP_200_OK

# ------------------ UPDATE PRODUCT ------------------ #
@product_bp.route("/update/<int:product_id>", methods=["PUT", "PATCH"])
@jwt_required()
@roles_required("admin")
def update_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), HTTP_404_NOT_FOUND

    try:
        # Update fields if provided in the request
        product.title = request.form.get("title", product.title)
        product.description = request.form.get("description", product.description)
        product.category = request.form.get("category", product.category)
        product.price = request.form.get("price", product.price)

        # Optional: update image
        file = request.files.get("image")
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid4().hex}_{filename}"
            save_folder = os.path.join(current_app.root_path, "..", UPLOAD_FOLDER)
            os.makedirs(save_folder, exist_ok=True)
            file.save(os.path.join(save_folder, unique_filename))
            product.image = f"{UPLOAD_FOLDER}/{unique_filename}"

        # Ensure the user_id is never null (optional: assign current user if needed)
        if not product.user_id:
            product.user_id = get_jwt_identity()

        db.session.commit()
        return jsonify({"message": "Product updated"}), HTTP_200_OK

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR

# ------------------ DELETE PRODUCT ------------------ #
@product_bp.route("/delete/<int:product_id>", methods=["DELETE"])
@jwt_required()
@roles_required("admin")
def delete_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), HTTP_404_NOT_FOUND
    try:
        db.session.delete(product)
        db.session.commit()
        return jsonify({"message": "Product deleted"}), HTTP_200_OK
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR

# ------------------ PUBLIC PRODUCTS ------------------ #
@product_bp.route("/public", methods=["GET"])
def get_public_products():
    products = Product.query.all()
    return jsonify([
        {
            "id": p.id,
            "title": p.title,
            "description": p.description,
            "category": p.category,
            "price": p.price,
            "image": p.image  # keep relative path
        } for p in products
    ])

