from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.decorators import roles_required
from app.extensions import db
from app.models.order_model import Order
from app.models.payment_model import Payment
from app.models.user_model import User
from app.models.project_model import Project
from datetime import datetime, date
from sqlalchemy import func # it helps with date filtering
from status_codes import HTTP_400_BAD_REQUEST, HTTP_200_OK, HTTP_404_NOT_FOUND,HTTP_403_FORBIDDEN, HTTP_500_INTERNAL_SERVER_ERROR

order_bp = Blueprint("order_bp", __name__, url_prefix="/api/v1/orders")

# ------------------ CREATE ORDER ------------------ #
@order_bp.route("/create", methods=["POST"])
@jwt_required()
@roles_required("admin")
def create_order():
    try:
        data = request.get_json()
        current_user_id = get_jwt_identity()

        project_id = data.get("project_id")
        client_id = data.get("client_id")
        notes = data.get("notes")

        total_amount = 0

        if project_id:
            order.balance_due = order.total_amount  # initialize balance due
            # Check if project exists
            project = Project.query.get(project_id)
            if not project:
                return jsonify({"error": "Invalid project ID"}), HTTP_404_NOT_FOUND
            total_amount = project.price if hasattr(project, "price") else 0

        order = Order(
            project_id=project_id,
            client_id=client_id,
            user_id=current_user_id,
            notes=notes,
            total_amount=total_amount,
            created_at=datetime.utcnow()
        )

        db.session.add(order)
        db.session.commit()

        return jsonify({"message": "Order created successfully", "order_id": order.order_id}), HTTP_200_OK

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR


# ------------------ GET ALL ORDERS ------------------ #
@order_bp.route("/", methods=["GET"])
@jwt_required()
def get_orders():
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)

    if current_user.user_type == "admin":
        orders = Order.query.all()
    else:
        orders = Order.query.filter_by(user_id=current_user_id).all()

    return jsonify([
        {
            "order_id": o.order_id,
            "project_id": o.project_id,
            "client_id": o.client_id,
            "user_id": o.user_id,
            "status": o.status,
            "total_amount": o.total_amount,
            "notes": o.notes,
            "created_at": o.created_at.isoformat()
        } for o in orders
    ]), 200

# ------------------ GET ORDER BY ID ------------------ #
@order_bp.route("/<int:id>", methods=["GET"])
@jwt_required()
def get_order(id):
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)

    order = Order.query.get(id)
    if not order:
        return jsonify({"error": "Order not found"}), HTTP_404_NOT_FOUND

    if current_user.user_type != "admin" and order.user_id != current_user_id:
        return jsonify({"error": "Unauthorized access"}), HTTP_403_FORBIDDEN

    return jsonify({
        "order_id": order.order_id,
        "project_id": order.project_id,
        "client_id": order.client_id,
        "user_id": order.user_id,
        "status": order.status,
        "total_amount": order.total_amount,
        "notes": order.notes,
        "created_at": order.created_at.isoformat()
    }), HTTP_200_OK



# ------------------ UPDATE ORDER ------------------ #
@order_bp.route("/update/<int:order_id>", methods=["PUT", "PATCH"])
@jwt_required()
@roles_required("admin")
def update_order(order_id):
    try:
        order = Order.query.get(order_id)
        if not order:
            return jsonify({"error": "Order not found"}), HTTP_404_NOT_FOUND

        data = request.get_json()

        if data.get("status"):
            order.status = data["status"]
        if data.get("notes"):
            order.notes = data["notes"]
        if data.get("total_amount"):
            order.total_amount = data["total_amount"]

        db.session.commit()

        return jsonify({"message": "Order updated successfully"}), HTTP_200_OK

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR


# ------------------ DELETE ORDER ------------------ #
@order_bp.route("/delete/<int:order_id>", methods=["DELETE"])
@jwt_required()
@roles_required("admin")
def delete_order(order_id):
    try:
        order = Order.query.get(order_id)
        if not order:
            return jsonify({"error": "Order not found"}), HTTP_404_NOT_FOUND

        db.session.delete(order)
        db.session.commit()

        return jsonify({"message": "Order deleted successfully"}), HTTP_200_OK

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR


# ------------------ FILTER ORDERS ------------------ #
@order_bp.route("/filter", methods=["GET"])
@jwt_required()
def filter_orders():
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)

    status = request.args.get("status")
    start_date = request.args.get("start")
    end_date = request.args.get("end")

    query = Order.query

    if current_user.user_type == "staff":
        query = query.filter_by(user_id=current_user_id)

    if status:
        query = query.filter_by(status=status)

    if start_date:
        query = query.filter(Order.created_at >= start_date)
    if end_date:
        query = query.filter(Order.created_at <= end_date)

    orders = query.order_by(Order.created_at.desc()).all()

    return jsonify([
        {
            "order_id": o.order_id,
            "project_id": o.project_id,
            "client_id": o.client_id,
            "user_id": o.user_id,
            "status": o.status,
            "total_amount": o.total_amount,
            "notes": o.notes,
            "created_at": o.created_at.isoformat()
        } for o in orders
    ]), HTTP_200_OK


# ------------------ DASHBOARD STATS ------------------ #
@order_bp.route("/stats", methods=["GET"])
@jwt_required()
@roles_required("admin")
def get_dashboard_stats():
    try:
        total_orders = Order.query.count()
        pending_orders = Order.query.filter_by(status="Pending").count()
        completed_orders = Order.query.filter_by(status="Completed").count()

        today = date.today()
        today_orders = Order.query.filter(func.date(Order.created_at) == today).count()

        total_revenue = db.session.query(func.coalesce(func.sum(Payment.amount), 0.0)).scalar()

        current_month = datetime.today().month
        current_year = datetime.today().year
        monthly_revenue = db.session.query(
            func.coalesce(func.sum(Payment.amount), 0.0)
        ).filter(
            func.extract('month', Payment.created_at) == current_month,
            func.extract('year', Payment.created_at) == current_year
        ).scalar()

        return jsonify({
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "completed_orders": completed_orders,
            "today_orders": today_orders,
            "total_revenue": total_revenue,
            "monthly_revenue": monthly_revenue
        }), HTTP_200_OK

    except Exception as e:
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR

# ------------------ GET ORDER WITH PAYMENTS ------------------ #
@order_bp.route("/<int:order_id>", methods=["GET"])
@jwt_required()
def get_order_with_payments(order_id):
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        order = Order.query.get(order_id)

        if not order:
            return jsonify({"error": "Order not found"}), 404

        if current_user.user_type == "staff" and order.user_id != current_user_id:
            return jsonify({"error": "Unauthorized access to this order"}), 403

        payments = [
            {
                "payment_id": p.payment_id,
                "amount": p.amount,
                "method": p.method,
                "reference": p.reference,
                "paid_at": p.paid_at.isoformat()
            } for p in order.payments
        ]

        return jsonify({
            "order_id": order.order_id,
            "project_id": order.project_id,
            "client_id": order.client_id,
            "user_id": order.user_id,
            "status": order.status,
            "total_amount": order.total_amount,
            "total_paid": order.total_paid,
            "balance_due": order.balance_due,
            "notes": order.notes,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "payments": payments
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------ CLIENT ORDER HISTORY ------------------ #
@order_bp.route("/client/<int:client_id>", methods=["GET"])
@jwt_required()
@roles_required("admin")
def get_client_order_history(client_id):
    try:
        orders = Order.query.filter_by(client_id=client_id).order_by(Order.created_at.desc()).all()
        result = []
        for order in orders:
            payments = [
                {
                    "payment_id": p.payment_id,
                    "amount": p.amount,
                    "method": p.method,
                    "reference": p.reference,
                    "paid_at": p.paid_at.isoformat()
                } for p in order.payments
            ]
            result.append({
                "order_id": order.order_id,
                "status": order.status,
                "total_amount": order.total_amount,
                "total_paid": order.total_paid,
                "balance_due": order.balance_due,
                "created_at": order.created_at.isoformat(),
                "payments": payments
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------ FINANCIAL REPORT ------------------ #
@order_bp.route("/report/financial", methods=["GET"])
@jwt_required()
@roles_required("admin")
def get_financial_report():
    try:
        payments = Payment.query.order_by(Payment.paid_at.desc()).all()
        report = [
            {
                "payment_id": p.payment_id,
                "order_id": p.order_id,
                "amount": p.amount,
                "method": p.method,
                "reference": p.reference,
                "paid_at": p.paid_at.isoformat()
            } for p in payments
        ]
        return jsonify({"report": report, "count": len(report)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

