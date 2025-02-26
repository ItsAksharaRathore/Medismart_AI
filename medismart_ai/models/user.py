# from datetime import datetime
# import json
# from flask_sqlalchemy import SQLAlchemy

# db = SQLAlchemy()

# class User(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     username = db.Column(db.String(100), unique=True, nullable=False)
#     email = db.Column(db.String(120), unique=True, nullable=False)
#     password = db.Column(db.String(200), nullable=False)
#     name = db.Column(db.String(100))
#     role = db.Column(db.String(20), default='user')  # 'user', 'pharmacist', 'admin'
#     date_joined = db.Column(db.DateTime, default=datetime.utcnow)

#     # Relationships
#     prescriptions = db.relationship('Prescription', back_populates='user', lazy='dynamic')

#     def __repr__(self):
#         return f'<User {self.username}>'

# class Prescription(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
#     prescription_image = db.Column(db.String(200), nullable=False)  # Path to stored image
#     ocr_text = db.Column(db.Text)  # Extracted text from prescription
#     upload_date = db.Column(db.DateTime, default=datetime.utcnow)
#     status = db.Column(db.String(20), default='processing')  # 'processing', 'completed', 'error'
    
#     # Extracted medicine details (JSON string)
#     medications = db.Column(db.Text, default='[]')  # Ensure it has a valid JSON default
    
#     # Relationships
#     user = db.relationship('User', back_populates='prescriptions')
#     alternatives = db.relationship('AlternativeMedication', back_populates='prescription', lazy='dynamic', cascade="all, delete-orphan")
#     interactions = db.relationship('DrugInteraction', back_populates='prescription', lazy='dynamic', cascade="all, delete-orphan")
    
#     def get_medications(self):
#         """Convert medications JSON string to a Python list"""
#         try:
#             return json.loads(self.medications) if self.medications else []
#         except json.JSONDecodeError:
#             return []

#     def __repr__(self):
#         return f'<Prescription {self.id}>'

# class AlternativeMedication(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     prescription_id = db.Column(db.Integer, db.ForeignKey('prescription.id'), nullable=False)
#     original_medication = db.Column(db.String(200), nullable=False)
#     alternative_medication = db.Column(db.String(200), nullable=False)
#     cost_difference = db.Column(db.Float)  # Negative means cheaper
#     efficacy_rating = db.Column(db.Float)  # 0-1 scale
#     reason = db.Column(db.Text)  # Why this alternative is suggested
    
#     # Relationship
#     prescription = db.relationship('Prescription', back_populates='alternatives')

#     def __repr__(self):
#         return f'<AlternativeMedication {self.alternative_medication}>'

# class DrugInteraction(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     prescription_id = db.Column(db.Integer, db.ForeignKey('prescription.id'), nullable=False)
#     medication1 = db.Column(db.String(200), nullable=False)
#     medication2 = db.Column(db.String(200), nullable=False)
#     severity = db.Column(db.String(20))  # 'mild', 'moderate', 'severe'
#     description = db.Column(db.Text)
#     recommendation = db.Column(db.Text)
    
#     # Relationship
#     prescription = db.relationship('Prescription', back_populates='interactions')

#     def __repr__(self):
#         return f'<DrugInteraction {self.medication1} - {self.medication2}>'


from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from models import db

class User(db.Model):
    """User Model"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100))
    role = db.Column(db.String(20), default='user')  # 'user', 'admin'
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, username, email, password, name=None, role='user'):
        self.username = username
        self.email = email
        self.password_hash = generate_password_hash(password)
        self.name = name
        self.role = role

    def verify_password(self, password):
        """Verify user password"""
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def create_user(username, email, password, name=None, role='user'):
        """Create and save a new user"""
        new_user = User(username=username, email=email, password=password, name=name, role=role)
        db.session.add(new_user)
        db.session.commit()
        return new_user

    @staticmethod
    def get_user_by_id(user_id):
        """Retrieve user by ID"""
        return User.query.get(user_id)

    @staticmethod
    def get_user_by_email(email):
        """Retrieve user by email"""
        return User.query.filter_by(email=email).first()

    @staticmethod
    def get_all_users():
        """Retrieve all users"""
        return User.query.all()

    @staticmethod
    def update_user(user_id, new_data):
        """Update user details"""
        user = User.get_user_by_id(user_id)
        if user:
            for key, value in new_data.items():
                if key == "password":
                    user.password_hash = generate_password_hash(value)
                else:
                    setattr(user, key, value)
            db.session.commit()
            return user
        return None

    @staticmethod
    def delete_user(user_id):
        """Delete user from database"""
        user = User.get_user_by_id(user_id)
        if user:
            db.session.delete(user)
            db.session.commit()
            return True
        return False

    def __repr__(self):
        return f'<User {self.username}>'
