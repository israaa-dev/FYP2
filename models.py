from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Hospital(db.Model):
    __tablename__ = "hospital"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    available_beds = db.Column(db.Integer, default=0)
    status = db.Column(db.String(30), default="Open")  # Open / Overloaded / Unavailable

    def __repr__(self):
        return f"<Hospital {self.name}>"

class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # citizen / staff / admin
    hospital_id = db.Column(db.Integer, db.ForeignKey("hospital.id"), nullable=True)

    hospital = db.relationship("Hospital", backref="staff_users", lazy=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"

class EmergencyRequest(db.Model):
    __tablename__ = "emergency_request"
    id = db.Column(db.Integer, primary_key=True)
    emergency_type = db.Column(db.String(80), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), default="Pending")  # Pending / Accepted / Rejected / Cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    citizen_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    hospital_id = db.Column(db.Integer, db.ForeignKey("hospital.id"), nullable=True)

    citizen = db.relationship("User", foreign_keys=[citizen_id])
    hospital = db.relationship("Hospital", foreign_keys=[hospital_id])

    def __repr__(self):
        return f"<Request {self.id} {self.status}>"
