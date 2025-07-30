from app.extensions import db, bcrypt
from datetime import datetime

class User(db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    contact = db.Column(db.String(50), nullable=False, unique=True)
    image = db.Column(db.String(255), nullable=True)
    password = db.Column(db.Text(), nullable=False)
    biography = db.Column(db.Text, nullable=False)
    user_type = db.Column(db.String(20), default='staff')  # only 'admin' or 'staff'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def __init__(self, first_name, last_name, email, contact, password, biography, user_type='staff', image=None):
        super(User, self).__init__()
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.contact = contact
        self.set_password(password)  # hashes password here
        self.biography = biography
        self.user_type = user_type
        self.image = image

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

    def get_full_name(self):
        return f"{self.last_name} {self.first_name}"
