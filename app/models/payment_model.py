from app.extensions import db
from datetime import datetime

class Payment(db.Model):
    __tablename__ = "payments"

    payment_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(50), nullable=False)  # e.g., Cash, Mobile Money
    reference = db.Column(db.String(100), nullable=True)
    paid_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, order_id, amount, method, reference=None):
        self.order_id = order_id
        self.amount = amount
        self.method = method
        self.reference = reference

    def __repr__(self):
        return f"<Payment {self.amount} via {self.method} on order {self.order_id}>"
