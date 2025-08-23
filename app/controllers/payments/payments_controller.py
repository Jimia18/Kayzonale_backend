from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.decorators import roles_required
from app.extensions import db
from app.models.payment_model import Payment
from app.models.order_model import Order
from app.models.user_model import User
from datetime import datetime
from status_codes import HTTP_400_BAD_REQUEST, HTTP_201_CREATED, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR, HTTP_403_FORBIDDEN



payment_bp = Blueprint("payment_bp", __name__, url_prefix="/api/v1/payments")



# ------------------ CUSTOMER PAYMENT (Checkout) ------------------ #
@payment_bp.route("/checkout", methods=["POST"])
@jwt_required()
def checkout_payment():
    try:
        user_id = get_jwt_identity()
        current_user = User.query.get(user_id)
        data = request.get_json()

        order_id = data.get("order_id")
        amount = data.get("amount")
        method = data.get("method")
        reference = data.get("reference")  # e.g., transaction ID, phone number for mobile money

        if not order_id or not amount or not method:
            return jsonify({"error": "order_id, amount, and method are required"}), HTTP_400_BAD_REQUEST

        # Fetch the order
        order = Order.query.get(order_id)
        if not order:
            return jsonify({"error": "Order not found"}), HTTP_404_NOT_FOUND

        # Verify the order belongs to the current user
        if order.user_id != user_id:
            return jsonify({"error": "Unauthorized access to this order"}), HTTP_403_FORBIDDEN

        # Validate payment amount matches order total
        if amount != order.total_amount:
            return jsonify({"error": "Payment amount does not match order total"}), HTTP_400_BAD_REQUEST

        # Restrict payment methods
        if method not in ["cash", "card", "mobile"]:
            return jsonify({"error": "Invalid payment method"}), HTTP_400_BAD_REQUEST

        # For mobile payments, validate reference (phone number)
        if method == "mobile" and (not reference or len(reference) < 9):
            return jsonify({"error": "Valid phone number required for mobile payments"}), HTTP_400_BAD_REQUEST

        # Create Payment record
        payment = Payment(
            order_id=order_id,
            amount=amount,
            method=method,
            reference=reference or f"{method.upper()}-{datetime.utcnow().timestamp()}"
        )
        db.session.add(payment)

        # Update order payment status
        order.total_paid = amount
        order.balance_due = 0
        order.status = "Completed"

        db.session.commit()

        return jsonify({
            "message": "Payment processed successfully",
            "payment_id": payment.payment_id,
            "method": method,
            "amount": amount,
            "status": order.status
        }), HTTP_201_CREATED

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR



# ------------------ CREATE PAYMENT ------------------ #
@payment_bp.route("/", methods=["POST"])
@jwt_required()
@roles_required("admin")
def create_payment():
    try:
        data = request.get_json()
        order_id = data.get("order_id")
        amount = data.get("amount")
        method = data.get("method")
        reference = data.get("reference")

        if not order_id or not amount or not method:
            return jsonify({"error": "order_id, amount and method are required"}), 400

        order = Order.query.get(order_id)
        if not order:
            return jsonify({"error": "Order not found"}), 404

        payment = Payment(order_id=order_id, amount=amount, method=method, reference=reference)
        db.session.add(payment)

        order.total_paid = (order.total_paid or 0) + amount
        order.balance_due = max((order.total_amount or 0) - order.total_paid, 0)

        db.session.commit()
        return jsonify({"message": "Payment created successfully", "payment_id": payment.payment_id}), HTTP_201_CREATED
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR


# ------------------ GET ALL PAYMENTS ------------------ #
@payment_bp.route("/", methods=["GET"])
@jwt_required()
@roles_required("admin")
def get_all_payments():
    try:
        payments = Payment.query.order_by(Payment.paid_at.desc()).all()
        return jsonify([
            {
                "payment_id": p.payment_id,
                "order_id": p.order_id,
                "amount": p.amount,
                "method": p.method,
                "reference": p.reference,
                "paid_at": p.paid_at.isoformat()
            } for p in payments
        ]), HTTP_201_CREATED
    except Exception as e:
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR


# ------------------ GET PAYMENT BY ID ------------------ #
@payment_bp.route("/<int:payment_id>", methods=["GET"])
@jwt_required()
@roles_required("admin")
def get_payment(payment_id):
    try:
        payment = Payment.query.get(payment_id)
        if not payment:
            return jsonify({"error": "Payment not found"}), HTTP_404_NOT_FOUND

        return jsonify({
            "payment_id": payment.payment_id,
            "order_id": payment.order_id,
            "amount": payment.amount,
            "method": payment.method,
            "reference": payment.reference,
            "paid_at": payment.paid_at.isoformat()
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------ UPDATE PAYMENT ------------------ #
@payment_bp.route("/<int:payment_id>", methods=["PUT"])
@jwt_required()
@roles_required("admin")
def update_payment(payment_id):
    try:
        payment = Payment.query.get(payment_id)
        if not payment:
            return jsonify({"error": "Payment not found"}), HTTP_404_NOT_FOUND

        data = request.get_json()
        old_amount = payment.amount

        payment.amount = data.get("amount", payment.amount)
        payment.method = data.get("method", payment.method)
        payment.reference = data.get("reference", payment.reference)

        order = payment.order
        order.total_paid += payment.amount - old_amount
        order.balance_due = max((order.total_amount or 0) - order.total_paid, 0)

        db.session.commit()
        return jsonify({"message": "Payment updated successfully"}), HTTP_201_CREATED
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR


# ------------------ DELETE PAYMENT ------------------ #
@payment_bp.route("/<int:payment_id>", methods=["DELETE"])
@jwt_required()
@roles_required("admin")
def delete_payment(payment_id):
    try:
        payment = Payment.query.get(payment_id)
        if not payment:
            return jsonify({"error": "Payment not found"}), HTTP_404_NOT_FOUND

        order = payment.order
        order.total_paid -= payment.amount
        order.balance_due = max((order.total_amount or 0) - order.total_paid, 0)

        db.session.delete(payment)
        db.session.commit()

        return jsonify({"message": "Payment deleted and order totals updated"}), HTTP_201_CREATED
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), HTTP_500_INTERNAL_SERVER_ERROR
