from app.extensions import db
from datetime import datetime

class FileUpload(db.Model):
    __tablename__ = "file_uploads"

    file_id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.project_id'), nullable=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'), nullable=True)
    filename = db.Column(db.String(255), nullable=False)
    file_url = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, filename, file_url, project_id=None, order_id=None):
        self.filename = filename
        self.file_url = file_url
        self.project_id = project_id
        self.order_id = order_id

    def __repr__(self):
        return f"<FileUpload {self.filename} (project_id={self.project_id}, order_id={self.order_id})>"
