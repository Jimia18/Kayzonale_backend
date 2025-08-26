from app.extensions import db,migrate


class Service(db.Model):
    __tablename__ = "services"

    service_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(255), nullable=True)  # new field

    def __init__(self, name, description=None, image_url=None):
        self.name = name
        self.description = description
        self.image_url = image_url

    def __repr__(self):
        return f"<Service {self.name}>"
