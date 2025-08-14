from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.decorators import roles_required
from app.extensions import db
from app.models.file_upload_model import FileUpload
from status_codes import HTTP_201_CREATED, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR, HTTP_400_BAD_REQUEST

file_upload_bp = Blueprint("file_upload_bp", __name__, url_prefix="/api/v1/files")

# CREATE file upload
@file_upload_bp.route("/", methods=["POST"])
@jwt_required()
@roles_required("admin")
def create_file_upload():
    data = request.get_json()
    filename = data.get("filename")
    file_url = data.get("file_url")
    project_id = data.get("project_id")
    order_id = data.get("order_id")

    if not filename or not file_url:
        return jsonify({"error": "filename and file_url are required"}), HTTP_400_BAD_REQUEST

    try:
        file_upload = FileUpload(filename=filename, file_url=file_url,
                                 project_id=project_id, order_id=order_id)
        db.session.add(file_upload)
        db.session.commit()
        return jsonify({"message": "File uploaded successfully", "file_id": file_upload.file_id}), HTTP_201_CREATED
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR

# GET all files (optionally filter by project_id or order_id)
@file_upload_bp.route("/", methods=["GET"])
@jwt_required()
def get_files():
    project_id = request.args.get("project_id")
    order_id = request.args.get("order_id")

    query = FileUpload.query
    if project_id:
        query = query.filter_by(project_id=project_id)
    if order_id:
        query = query.filter_by(order_id=order_id)

    files = query.order_by(FileUpload.uploaded_at.desc()).all()
    return jsonify([
        {
            "file_id": f.file_id,
            "filename": f.filename,
            "file_url": f.file_url,
            "project_id": f.project_id,
            "order_id": f.order_id,
            "uploaded_at": f.uploaded_at.isoformat()
        }
        for f in files
    ]), 200

# GET file by id
@file_upload_bp.route("/<int:file_id>", methods=["GET"])
@jwt_required()
def get_file(file_id):
    file_upload = FileUpload.query.get(file_id)
    if not file_upload:
        return jsonify({"error": "File not found"}), 404

    return jsonify({
        "file_id": file_upload.file_id,
        "filename": file_upload.filename,
        "file_url": file_upload.file_url,
        "project_id": file_upload.project_id,
        "order_id": file_upload.order_id,
        "uploaded_at": file_upload.uploaded_at.isoformat()
    }), 200

# UPDATE file metadata
@file_upload_bp.route("/<int:file_id>", methods=["PUT"])
@jwt_required()
@roles_required("admin")
def update_file(file_id):
    file_upload = FileUpload.query.get(file_id)
    if not file_upload:
        return jsonify({"error": "File not found"}), HTTP_404_NOT_FOUND

    data = request.get_json()
    file_upload.filename = data.get("filename", file_upload.filename)
    file_upload.file_url = data.get("file_url", file_upload.file_url)
    file_upload.project_id = data.get("project_id", file_upload.project_id)
    file_upload.order_id = data.get("order_id", file_upload.order_id)

    try:
        db.session.commit()
        return jsonify({"message": "File updated successfully"}), HTTP_201_CREATED
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR

# DELETE file upload
@file_upload_bp.route("/<int:file_id>", methods=["DELETE"])
@jwt_required()
@roles_required("admin")
def delete_file(file_id):
    file_upload = FileUpload.query.get(file_id)
    if not file_upload:
        return jsonify({"error": "File not found"}), HTTP_404_NOT_FOUND

    try:
        db.session.delete(file_upload)
        db.session.commit()
        return jsonify({"message": "File deleted successfully"}), HTTP_201_CREATED
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR
