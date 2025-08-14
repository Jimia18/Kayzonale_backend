import os
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models.product_model import Product
from app.decorators import roles_required
from status_codes import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

product_bp = Blueprint("product_bp", __name__, url_prefix="/api/v1/products")

UPLOAD_FOLDER = os.path.join(os.getcwd(), "static", "uploads", "products")  # absolute path
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # create folder if it doesn't exist

# ------------------ CREATE PRODUCT ------------------ #
@product_bp.route('/create', methods=['POST'])
@jwt_required()
@roles_required("admin")
def create_product():
    try:
        title = request.form.get('title')
        description = request.form.get('description')
        price = request.form.get('price')
        category = request.form.get('category')
        image_file = request.files.get('image')

        if not title or not description or not price or not category:
            return jsonify({"error": "All fields are required"}), HTTP_400_BAD_REQUEST

        image_url = None
        if image_file:
            if not allowed_file(image_file.filename):
                return jsonify({"error": "Invalid image type"}), HTTP_400_BAD_REQUEST
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(UPLOAD_FOLDER, filename)
            image_file.save(image_path)
            # Use relative path from static folder for serving
            image_url = f"/static/uploads/products/{filename}"

        new_product = Product(
            title=title,
            description=description,
            price=price,
            category=category,
            image=image_url
        )
        db.session.add(new_product)
        db.session.commit()
        return jsonify(new_product.to_dict()), HTTP_200_OK

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR


# ------------------ GET ALL PRODUCTS ------------------ #
@product_bp.route('/', methods=['GET'])
def get_all_products():
    products = Product.query.all()
    return jsonify([p.to_dict() for p in products]), HTTP_200_OK


# ------------------ GET PRODUCT BY ID ------------------ #
@product_bp.route('/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), HTTP_404_NOT_FOUND
    return jsonify(product.to_dict()), HTTP_200_OK


# ------------------ UPDATE PRODUCT ------------------ #
@product_bp.route('/update/<int:product_id>', methods=['PUT', 'PATCH'])
@jwt_required()
@roles_required("admin")
def update_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), HTTP_404_NOT_FOUND

    try:
        title = request.form.get('title')
        description = request.form.get('description')
        price = request.form.get('price')
        category = request.form.get('category')
        image_file = request.files.get('image')

        if title: product.title = title
        if description: product.description = description
        if price: product.price = price
        if category: product.category = category

        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(UPLOAD_FOLDER, filename)
            image_file.save(image_path)
            product.image = f"/{image_path}"

        db.session.commit()
        return jsonify(product.to_dict()), HTTP_200_OK

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR


# ------------------ DELETE PRODUCT ------------------ #
@product_bp.route('/<int:product_id>', methods=['DELETE'])
@jwt_required()
@roles_required("admin")
def delete_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), HTTP_404_NOT_FOUND

    try:
        db.session.delete(product)
        db.session.commit()
        return jsonify({"message": "Product deleted successfully"}), HTTP_200_OK
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR


# ------------------ Serve Uploaded Images ------------------ #
@product_bp.route('/image/<filename>', methods=['GET'])
def get_uploaded_image(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)
