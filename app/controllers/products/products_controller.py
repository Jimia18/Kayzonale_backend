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

# Constants
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_upload_folder():
    """Helper function to get the upload folder path"""
    return os.path.join(current_app.root_path, 'static', 'uploads', 'products')

def save_uploaded_file(file):
    """Helper function to handle file uploads"""
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        upload_folder = get_upload_folder()
        os.makedirs(upload_folder, exist_ok=True)  # Ensure directory exists
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        return f"/static/uploads/products/{filename}"
    return None

# ------------------ CREATE PRODUCT ------------------ #
@product_bp.route('/', methods=['POST'])
@jwt_required()
@roles_required("admin")
def create_product():
    try:
        data = request.form
        required_fields = ['title', 'description', 'price', 'category']
        
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), HTTP_400_BAD_REQUEST

        image_url = save_uploaded_file(request.files.get('image')) if 'image' in request.files else None

        new_product = Product(
            title=data['title'],
            description=data['description'],
            price=float(data['price']),
            category=data['category'],
            image=image_url
        )

        db.session.add(new_product)
        db.session.commit()
        
        return jsonify({
            "message": "Product created successfully",
            "product": new_product.to_dict()
        }), HTTP_200_OK

    except ValueError as e:
        db.session.rollback()
        return jsonify({"error": "Invalid price value"}), HTTP_400_BAD_REQUEST
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating product: {str(e)}")
        return jsonify({"error": "Internal server error"}), HTTP_500_INTERNAL_SERVER_ERROR

# ------------------ GET ALL PRODUCTS ------------------ #
@product_bp.route('/', methods=['GET'])
def get_all_products():
    try:
        products = Product.query.all()
        return jsonify([p.to_dict() for p in products]), HTTP_200_OK
    except Exception as e:
        current_app.logger.error(f"Error fetching products: {str(e)}")
        return jsonify({"error": "Internal server error"}), HTTP_500_INTERNAL_SERVER_ERROR

# ------------------ GET PRODUCT BY ID ------------------ #
@product_bp.route('/<int:product_id>', methods=['GET'])
def get_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        return jsonify(product.to_dict()), HTTP_200_OK
    except Exception as e:
        current_app.logger.error(f"Error fetching product {product_id}: {str(e)}")
        return jsonify({"error": "Product not found"}), HTTP_404_NOT_FOUND

# ------------------ UPDATE PRODUCT ------------------ #
@product_bp.route('/<int:product_id>', methods=['PUT', 'PATCH'])
@jwt_required()
@roles_required("admin")
def update_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        data = request.form
        
        if not data:
            return jsonify({"error": "No data provided"}), HTTP_400_BAD_REQUEST

        # Update fields if provided
        if 'title' in data: product.title = data['title']
        if 'description' in data: product.description = data['description']
        if 'price' in data: product.price = float(data['price'])
        if 'category' in data: product.category = data['category']
        
        # Handle image update
        if 'image' in request.files:
            new_image = save_uploaded_file(request.files['image'])
            if new_image:
                product.image = new_image

        db.session.commit()
        return jsonify({
            "message": "Product updated successfully",
            "product": product.to_dict()
        }), HTTP_200_OK

    except ValueError as e:
        db.session.rollback()
        return jsonify({"error": "Invalid price value"}), HTTP_400_BAD_REQUEST
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating product {product_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), HTTP_500_INTERNAL_SERVER_ERROR

# ------------------ DELETE PRODUCT ------------------ #
@product_bp.route('/<int:product_id>', methods=['DELETE'])
@jwt_required()
@roles_required("admin")
def delete_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        
        # Optional: Delete associated image file
        if product.image:
            try:
                image_path = os.path.join(current_app.root_path, product.image.lstrip('/'))
                if os.path.exists(image_path):
                    os.remove(image_path)
            except Exception as e:
                current_app.logger.warning(f"Could not delete image file: {str(e)}")

        db.session.delete(product)
        db.session.commit()
        return jsonify({"message": "Product deleted successfully"}), HTTP_200_OK
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting product {product_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), HTTP_500_INTERNAL_SERVER_ERROR

# ------------------ Serve Uploaded Images ------------------ #
@product_bp.route('/images/<filename>', methods=['GET'])
def get_uploaded_image(filename):
    try:
        upload_folder = get_upload_folder()
        return send_from_directory(upload_folder, filename)
    except FileNotFoundError:
        return jsonify({"error": "Image not found"}), HTTP_404_NOT_FOUND