from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.decorators import roles_required
from app.extensions import db
from app.models.order_model import Order
from app.models.orderItem_model import OrderItem
from app.models.payment_model import Payment
from app.models.user_model import User
from app.models.project_model import Project
from datetime import datetime, date
from sqlalchemy import func
from status_codes import (
    HTTP_400_BAD_REQUEST,
    HTTP_200_OK,
    HTTP_404_NOT_FOUND,
    HTTP_403_FORBIDDEN,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

order_bp = Blueprint("order_bp", __name__, url_prefix="/api/v1/orders")


# ------------------ CLIENT CHECKOUT (CREATE ORDER) ------------------ #
@order_bp.route("/checkout", methods=["POST"])
@jwt_required()
def checkout_order():
    try:
        data = request.get_json()
        current_user_id = get_jwt_identity()

        items = data.get("items", [])  # [{product_id, quantity, price}, ...]    shhipping", {})
        payment_method = data.get("payment", "cod")

        if not items:
            return jsonify({"error": "No items in order"}), HTTP_400_BAD_REQUEST

        # calculate total
        total_amount = sum(item["price"] * item["quantity"] for item in items)

        # Create order
        order = Order(
            user_id=current_user_id,
            client_id=data.get("client_id"),
            # notes=shipping.get("notes"),
            total_amount=total_amount,
            balance_due=total_amount,
            status="Pending",
            created_at=datetime.utcnow(),
        )
        db.session.add(order)
        db.session.flush()  # make order.order_id available

        # Save order items
        for item in items:
            order_item = OrderItem(
                order_id=order.order_id,
                product_id=item["product_id"],
                quantity=item["quantity"],
                price=item["price"],
            )
            db.session.add(order_item)

        # If payment is immediate, create Payment record
        if payment_method != "cod":
            payment = Payment(
                order_id=order.order_id,
                amount=total_amount,
                method=payment_method,
                reference=f"TXN-{datetime.utcnow().timestamp()}"
            )
            db.session.add(payment)
            order.total_paid = total_amount
            order.balance_due = 0
            order.status = "Completed"

        db.session.commit()

        return jsonify(
            {
                "message": "Order placed successfully",
                "order_id": order.order_id,
                "total_amount": total_amount,
                "status": order.status,
                "items": [
                    {
                        "product_id": i["product_id"],
                        "quantity": i["quantity"],
                        "price": i["price"],
                    }
                    for i in items
                ],
            }
        ), HTTP_200_OK

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR

@order_bp.route('/my-orders', methods=['GET'])
@jwt_required()
def get_my_orders():
    try:
        current_user_id = get_jwt_identity()
        user_orders = Order.query.filter_by(user_id=current_user_id).all()
        
        orders_data = [
            {
                'order_id': order.order_id,
                'total_amount': order.total_amount,
                'status': order.status,
                'created_at': order.created_at
            } for order in user_orders
        ]
        
        return jsonify({
            'orders': orders_data
        }), HTTP_200_OK
        
    except Exception as e:
        return jsonify({'error': str(e)}), HTTP_500_INTERNAL_SERVER_ERROR


# ------------------ CREATE ORDER (ADMIN) ------------------ #
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
            created_at=datetime.utcnow(),
        )

        order.balance_due = total_amount
        db.session.add(order)
        db.session.commit()

        return (
            jsonify(
                {"message": "Order created successfully", "order_id": order.order_id}
            ),
            HTTP_200_OK,
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR


# ------------------ GET ALL ORDERS ------------------ #
@order_bp.route("/", methods=["GET"])
@jwt_required()
@roles_required('admin')
def get_orders():
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)

    if current_user.user_type == "admin":
        orders = Order.query.all()
    else:
        orders = Order.query.filter_by(user_id=current_user_id).all()

    return (
        jsonify(
            [
                {
                    "order_id": o.order_id,
                    "project_id": o.project_id,
                    "client_id": o.client_id,
                    "user_id": o.user_id,
                    "status": o.status,
                    "total_amount": o.total_amount,
                    "notes": o.notes,
                    "created_at": o.created_at.isoformat(),
                    "items": [
                        {
                            "id": i.id,
                            "product_id": i.product_id,
                            "quantity": i.quantity,
                            "price": i.price,
                        }
                        for i in o.items
                    ],
                }
                for o in orders
            ]
        ),
        HTTP_200_OK,
    )


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

    return (
        jsonify(
            {
                "order_id": order.order_id,
                "project_id": order.project_id,
                "client_id": order.client_id,
                "user_id": order.user_id,
                "status": order.status,
                "total_amount": order.total_amount,
                "notes": order.notes,
                "created_at": order.created_at.isoformat(),
                "items": [
                    {
                        "id": i.id,
                        "product_id": i.product_id,
                        "quantity": i.quantity,
                        "price": i.price,
                    }
                    for i in order.items
                ],
            }
        ),
        HTTP_200_OK,
    )


# ------------------ REST OF YOUR ROUTES (payments, update, delete, filter, stats, etc.) ------------------ #
# keep them as they are from your original code





# ------------------ GET ORDER WITH PAYMENTS ------------------ #
@order_bp.route("/<int:order_id>/payments", methods=["GET"])
@jwt_required()
def get_order_with_payments(order_id):
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        order = Order.query.get(order_id)

        if not order:
            return jsonify({"error": "Order not found"}), HTTP_404_NOT_FOUND

        if current_user.user_type == "staff" and order.user_id != current_user_id:
            return jsonify({"error": "Unauthorized access to this order"}), HTTP_403_FORBIDDEN

        payments = [
            {
                "payment_id": p.payment_id,
                "amount": p.amount,
                "method": p.method,
                "reference": p.reference,
            } for p in order.payments
        ]

        return jsonify({
            "order_id": order.order_id,
            "project_id": order.project_id,
            "client_id": order.client_id,
            "user_id": order.user_id,
            "status": order.status,
            "total_amount": order.total_amount or 0.0,
            "balance_due": order.balance_due,
            "total_paid": order.total_paid,
            "notes": order.notes,
            "created_at": order.created_at.isoformat(),
            "payments": payments
        }), HTTP_200_OK

    except Exception as e:
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR


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

        if "status" in data:
            order.status = data["status"]
        if "notes" in data:
            order.notes = data["notes"]
        if "total_amount" in data:
            try:
                total_amount = float(data["total_amount"])
                order.total_amount = total_amount
                # Recalculate balance_due if needed here
            except ValueError:
                return jsonify({"error": "Invalid total_amount"}), HTTP_400_BAD_REQUEST

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
from datetime import datetime

@order_bp.route("/filter", methods=["GET"])
@jwt_required()
def filter_orders():
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    

    status = request.args.get("status")
    start_date = request.args.get("start")
    end_date = request.args.get("end")

    limit = request.args.get('limit', type=int)
    if limit:
        query = query.limit(limit)

    query = Order.query
    

    if current_user.user_type == "staff":
        query = query.filter_by(user_id=current_user_id)

    if status:
        query = query.filter_by(status=status)

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(Order.created_at >= start_dt)
        except ValueError:
            return jsonify({"error": "Invalid start date format, expected YYYY-MM-DD"}), HTTP_400_BAD_REQUEST

    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            query = query.filter(Order.created_at <= end_dt)
        except ValueError:
            return jsonify({"error": "Invalid end date format, expected YYYY-MM-DD"}), HTTP_400_BAD_REQUEST

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
@roles_required('admin')
def get_order_stats():
    try:
        total_orders = db.session.query(func.count(Order.order_id)).scalar()
        pending_orders = db.session.query(func.count(Order.order_id)).filter(Order.status == "pending").scalar()
        completed_orders = db.session.query(func.count(Order.order_id)).filter(Order.status == "completed").scalar()

        today = datetime.utcnow().date()
        today_orders = db.session.query(func.count(Order.order_id)).filter(
            func.date(Order.created_at) == today
        ).scalar()

        total_revenue = db.session.query(func.coalesce(func.sum(Order.total_amount), 0)).scalar()
        monthly_revenue = db.session.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(
            func.extract("month", Order.created_at) == datetime.utcnow().month,
            func.extract("year", Order.created_at) == datetime.utcnow().year
        ).scalar()

        return jsonify({
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "completed_orders": completed_orders,
            "today_orders": today_orders,
            "total_revenue": float(total_revenue),
            "monthly_revenue": float(monthly_revenue),
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR


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
        return jsonify(result), HTTP_200_OK
    except Exception as e:
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR


# ------------------ FINANCIAL REPORT ------------------ #
@order_bp.route("/report/financial", methods=["GET"])
@jwt_required()
@roles_required("admin")
def get_financial_report():
    try:
        payments = Payment.query.order_by(Payment.created_at.desc()).all()
        report = [
            {
                "payment_id": p.payment_id,
                "order_id": p.order_id,
                "amount": p.amount,
                "method": p.method,
                "reference": p.reference,
                 "created_at": p.created_at.isoformat()
            
            } for p in payments
        ]
        return jsonify({"report": report, "count": len(report)}), HTTP_200_OK
    except Exception as e:
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR
