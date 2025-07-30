from app.extensions import db
from datetime import datetime


class Project(db.Model):
    __tablename__ = "projects"

    project_id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.client_id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(50), default="Concept")  # Concept, In Progress, Completed
    deadline = db.Column(db.DateTime, nullable=True)
    price = db.Column(db.Float, nullable=True)
    payment_status = db.Column(db.String(50), default="Unpaid")
    delivery_status = db.Column(db.String(50), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    client = db.relationship('Client', backref='projects', lazy=True)
    files = db.relationship('FileUpload', backref='project', lazy=True)

    def __init__(self, client_id, title, description=None, category=None, status="Concept", deadline=None, price=None, payment_status="Unpaid", delivery_status="Pending"):
        self.client_id = client_id
        self.title = title
        self.description = description
        self.category = category
        self.status = status
        self.deadline = deadline
        self.price = price
        self.payment_status = payment_status
        self.delivery_status = delivery_status
