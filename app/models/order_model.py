from app.extensions import db
from datetime import datetime

class Order(db.Model):
    __tablename__ = "orders"

    order_id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.client_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)  # staff handling the order

    status = db.Column(db.String(50), default='Pending')  # Pending, Processing, Completed
    total_amount = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    client = db.relationship('Client', backref='orders', lazy=True)
    user = db.relationship('User', backref='orders', lazy=True)
    payments = db.relationship('Payment', backref='order', lazy=True)
    total_paid = db.Column(db.Float, default=0.0)
    balance_due = db.Column(db.Float, default=0.0)



