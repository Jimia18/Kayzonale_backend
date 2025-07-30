from app.extensions import db,migrate


class Service(db.Model):
    __tablename__ = "services"

    service_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)  # price per unit

    def __init__(self, name, price, description=None):
        self.name = name
        self.price = price
        self.description = description

    def __repr__(self):
        return f"<Service {self.name} - {self.price}>"
