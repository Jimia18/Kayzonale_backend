from flask import Blueprint, request, jsonify, current_app, url_for
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, jwt_required
from functools import wraps
from flask_cors import cross_origin
from marshmallow import ValidationError, Schema, fields, pre_load
from status_codes import (
    HTTP_400_BAD_REQUEST,
    HTTP_409_CONFLICT,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_201_CREATED,
    HTTP_404_NOT_FOUND,
    HTTP_403_FORBIDDEN,
    HTTP_200_OK,
    HTTP_401_UNAUTHORIZED,
)
from app.models.product_model import Product
from app.models.user_model import User
from app.extensions import db
from werkzeug.utils import secure_filename
from sqlalchemy.orm import joinedload
from uuid import uuid4
import os

# Blueprint
product_bp = Blueprint("product_bp", __name__, url_prefix="/api/v1/products")

# Configuration
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif",'webp'}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  

def get_current_user():
    identity = get_jwt_identity()
    if not identity:
        return None
    return User.query.get(identity)


def role_required(required_role):
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                return error_response("Unauthorized user.", HTTP_401_UNAUTHORIZED)
            if user.role != required_role:
                return error_response("Access denied. Insufficient role.", HTTP_403_FORBIDDEN)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def owner_or_admin_required(get_resource_user_id):
    """
    get_resource_user_id: a callable that receives args, kwargs and returns the owner user_id
    """
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                return error_response("Unauthorized user.", HTTP_401_UNAUTHORIZED)
            owner_id = get_resource_user_id(*args, **kwargs)
            if user.role not in ("admin", "super_admin") and user.id != owner_id:
                return error_response("Access denied.", HTTP_403_FORBIDDEN)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower()
    return "." in filename and ext in ALLOWED_IMAGE_EXTENSIONS


def iso(dt):
    return dt.isoformat() if hasattr(dt, "isoformat") else dt


def success_response(data=None, message=None, code=HTTP_200_OK):
    payload = {"success": True}
    if message:
        payload["message"] = message
    if data is not None:
        payload["data"] = data
    return jsonify(payload), code


def error_response(msg, code=HTTP_400_BAD_REQUEST, details=None):
    payload = {"success": False, "error": msg}
    if details:
        payload["details"] = details
    return jsonify(payload), code


class ProductBaseSchema(Schema):
    title = fields.Str(required=True)
    description = fields.Str(required=True)
    category = fields.Str(required=True)
    price = fields.Int(allow_none=True)

    @pre_load
    def coerce_and_trim(self, data, **kwargs):
        if "title" in data and isinstance(data["title"], str):
            data["title"] = data["title"].strip()
        if "description" in data and isinstance(data["description"], str):
            data["description"] = data["description"].strip()
        # convert empty strings to None for price
        if "price" in data and data["price"] in ("", "null", None):
            data["price"] = None
        return data


class ProductUpdateSchema(Schema):
    title = fields.Str()
    description = fields.Str()
    category = fields.Str()
    price = fields.Float(allow_none=True)

    @pre_load
    def coerce_and_trim(self, data, **kwargs):
        if "title" in data and isinstance(data["title"], str):
            data["title"] = data["title"].strip()
        if "description" in data and isinstance(data["description"], str):
            data["description"] = data["description"].strip()
        if "price" in data:
            if data["price"] in ("", "null", None):
              data["price"] = None
            else:
                try:
                    data['price'] = float(data['price'])
                except (ValueError,TypeError):
                    pass    
        return data


@product_bp.route("/create", methods=["POST", "OPTIONS"])
@cross_origin(origins="http://localhost:3000", supports_credentials=True)
@jwt_required()
def create_product():
    print("FORM DATA:", request.form)
    print("FILES:", request.files)

    input_data = request.form.to_dict()
    image_file = request.files.get("image")

    schema = ProductBaseSchema()
    try:
        validated_data = schema.load(input_data)
    except ValidationError as err:
        current_app.logger.error(f'Product validation failed:{err.messages}')
        return jsonify({"error": "Validation failed", "details": err.messages}), HTTP_400_BAD_REQUEST

    if not validated_data.get("title") or not validated_data.get("description") or validated_data.get("category") is None:
        return jsonify({"error": "Title, description, and category are required"}), HTTP_400_BAD_REQUEST

    image_filename = None
    if image_file:
        filename = secure_filename(image_file.filename)
        unique_filename = f"{uuid4().hex}_{filename}"
        upload_folder = os.path.join(current_app.root_path, "..", "static", "uploads", "products")
        os.makedirs(upload_folder, exist_ok=True)
        image_path = os.path.join(upload_folder, unique_filename)
        image_file.save(image_path)
        image_filename = unique_filename

        # Add to create_product function
    if image_file:

      if not allowed_file(image_file.filename):
          
    
       return jsonify({
        "error": "Invalid image format",
        "allowed_formats": list(ALLOWED_IMAGE_EXTENSIONS)
    }), HTTP_400_BAD_REQUEST
      

      if image_file.content_length > MAX_IMAGE_SIZE_BYTES:
       return jsonify({
        "error": "Image too large",
        "max_size_mb": MAX_IMAGE_SIZE_BYTES // (1024 * 1024)
    }), HTTP_400_BAD_REQUEST

    user_id = get_jwt_identity()

    product = Product(
        title=validated_data["title"],
        price=validated_data.get("price"),
        description=validated_data["description"],
        category=validated_data["category"],
        image=image_filename,
        user_id=user_id,
    )

    db.session.add(product)
    db.session.commit()

    return jsonify({"message": "Product created successfully"}), HTTP_201_CREATED


@product_bp.get("/")
def get_all_products():
    try:
        print("Request args:", request.args)
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("limit", 10, type=int)
        print(f"Pagination page={page}, limit={per_page}")

        user_id = None
        try:
            verify_jwt_in_request(optional=True)
            user_id = get_jwt_identity()
        except Exception:
            user_id = None

        query = Product.query.options(joinedload(Product.user))
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        products_data = []
        for product in paginated.items:
            owner = getattr(product, "user", None)
            product_info = {
                "id": product.id,
                "title": product.title,
                "price": product.price,
                "description": product.description,
                "category": product.category,
                "image": product.image,
                "created_at": iso(product.created_at),
            }

            if user_id:
                product_info["owner"] = {
                    "id": owner.id if owner else None,
                    "first_name": owner.first_name if owner else None,
                    "last_name": owner.last_name if owner else None,
                    "email": owner.email if owner else None,
                    "role": owner.role if owner else None,
                }

            products_data.append(product_info)

        meta = {
            "total": paginated.total,
            "pages": paginated.pages,
            "current_page": paginated.page,
            "per_page": per_page,
        }

        return success_response(
            data={"products": products_data, "meta": meta},
            message="Products retrieved successfully",
        )

    except Exception:
        current_app.logger.exception("Error fetching products")
        return error_response("Failed to retrieve products.", HTTP_500_INTERNAL_SERVER_ERROR)


@product_bp.get("/product/<int:id>")
@jwt_required()
def get_product(id):
    try:
        product = Product.query.options(joinedload(Product.user)).get(id)
        if not product:
            return error_response("Product not found.", HTTP_404_NOT_FOUND)

        owner = getattr(product, "user", None)
        product_data = {
            "id": product.id,
            "title": product.title,
            "price": product.price,
            "description": product.description,
            "category": product.category,
            "image": product.image,
            "owner": {
                "id": owner.id if owner else None,
                "first_name": owner.first_name if owner else None,
                "last_name": owner.last_name if owner else None,
                "email": owner.email if owner else None,
                "role": owner.role if owner else None,
            },
            "created_at": iso(product.created_at),
        }

        return success_response(
            data={"product": product_data},
            message="Product details retrieved successfully",
        )
    except Exception:
        current_app.logger.exception("Error fetching product id=%s", id)
        return error_response("Failed to retrieve product.", HTTP_500_INTERNAL_SERVER_ERROR)


@product_bp.route("/edit/<int:id>", methods=["PUT", "PATCH"])
@jwt_required()
def update_product(id):
    try:
        current_user = get_current_user()
        if not current_user:
            return error_response("Unauthorized user.", HTTP_401_UNAUTHORIZED)

        product = Product.query.get(id)
        if not product:
            return error_response("Product not found.", HTTP_404_NOT_FOUND)

        if current_user.role not in ("super_admin", "admin") and product.user_id != current_user.id:
            return error_response("You are not authorized to update this product.", HTTP_403_FORBIDDEN)

        title = request.form.get("title")
        price = request.form.get("price")
        description = request.form.get("description")
        category = request.form.get("category")
        image_file = request.files.get("image")

        if title:
            product.title = title

        if description:
            product.description = description

        if category:
            product.category = category

        if price:
            product.price = price

        if image_file:
            filename = secure_filename(image_file.filename)
            unique_filename = f"{uuid4().hex}_{filename}"
            upload_folder = os.path.join(current_app.root_path, "..", "static", "uploads", "products")
            os.makedirs(upload_folder, exist_ok=True)
            image_path = os.path.join(upload_folder, unique_filename)
            image_file.save(image_path)
            product.image = unique_filename

        db.session.commit()

        return success_response(
            data={
                "product": {
                    "id": product.id,
                    "title": product.title,
                    "price": product.price,
                    "category": product.category,
                    "description": product.description,
                    "image": product.image,
                    "updated_at": iso(product.updated_at),
                }
            },
            message=f"{product.title} updated successfully",
        )

    except Exception:
        current_app.logger.exception("Error updating product")
        db.session.rollback()
        return error_response("Failed to update product.", HTTP_500_INTERNAL_SERVER_ERROR)


@product_bp.route("/delete/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_product(id):
    try:
        current_user = get_current_user()
        if not current_user:
            return error_response("Unauthorized user.", HTTP_401_UNAUTHORIZED)

        product = Product.query.get(id)
        if not product:
            return error_response("Product not found.", HTTP_404_NOT_FOUND)

        if current_user.role not in ("super_admin", "admin") and product.user_id != current_user.id:
            return error_response("You are not authorized to delete this product.", HTTP_403_FORBIDDEN)

        db.session.delete(product)
        db.session.commit()
        return success_response(message="Product has been deleted successfully")
    except Exception:
        current_app.logger.exception("Error deleting product id=%s by user_id=%s", id, get_jwt_identity())
        return error_response("Failed to delete product.", HTTP_500_INTERNAL_SERVER_ERROR)
