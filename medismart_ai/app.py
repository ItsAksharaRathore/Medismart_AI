from flask import Flask, render_template, request, redirect, url_for, flash, session, Blueprint, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
import pytesseract
from PIL import Image

# Initialize Flask app
app = Flask(__name__, template_folder="frontend/templates", static_folder="frontend/static")
app.config['SECRET_KEY'] = 'medismart_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///medismart.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads/'  # Folder for prescription uploads
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'heic'}  # Allowed file types

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Initialize database
db = SQLAlchemy(app)

# ==============================
# USER MODEL
# ==============================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=True)
    role = db.Column(db.String(20), default='user')
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, username, email, password, name=None, role='user'):
        self.username = username
        self.email = email
        self.password_hash = generate_password_hash(password)
        self.name = name
        self.role = role

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def get_user_by_id(user_id):
        return User.query.get(user_id)

    @staticmethod
    def get_user_by_email(email):
        return User.query.filter_by(email=email).first()

# ==============================
# PRESCRIPTION MODEL
# ==============================
class Prescription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Pending')
    language = db.Column(db.String(50), default='auto')
    find_alternatives = db.Column(db.Boolean, default=True)
    check_interactions = db.Column(db.Boolean, default=True)
    insurance_coverage = db.Column(db.Boolean, default=False)
    patient_name = db.Column(db.String(100), nullable=True)
    doctor_name = db.Column(db.String(100), nullable=True)
    date = db.Column(db.Date, nullable=True)
    is_handwritten = db.Column(db.Boolean, default=False)
    extracted_text = db.Column(db.Text, nullable=True)
    medications = db.relationship('Medication', backref='prescription', lazy=True, cascade="all, delete-orphan")

    def __init__(self, user_id, filename, language='auto', find_alternatives=True, 
                check_interactions=True, insurance_coverage=False, is_handwritten=False):
        self.user_id = user_id
        self.filename = filename
        self.language = language
        self.find_alternatives = find_alternatives
        self.check_interactions = check_interactions
        self.insurance_coverage = insurance_coverage
        self.patient_name = "Self"  # Default value
        self.doctor_name = "Unknown"  # Default value
        self.date = datetime.utcnow().date()  # Default to today
        self.is_handwritten = is_handwritten

# ==============================
# MEDICATION MODEL
# ==============================
class Medication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescription.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    dosage = db.Column(db.String(100), nullable=True)
    frequency = db.Column(db.String(100), nullable=True)
    duration = db.Column(db.String(100), nullable=True)
    
    def __init__(self, prescription_id, name, dosage=None, frequency=None, duration=None):
        self.prescription_id = prescription_id
        self.name = name
        self.dosage = dosage
        self.frequency = frequency
        self.duration = duration

# ==============================
# CONTEXT PROCESSOR (Fixes `current_user` Issue)
# ==============================
@app.context_processor
def inject_user():
    user = None
    if 'user_id' in session:
        user = User.get_user_by_id(session['user_id'])
    return dict(current_user=user)

# ==============================
# CHECK ALLOWED FILE EXTENSIONS
# ==============================
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==============================
# OCR TEXT EXTRACTION FUNCTION
# ==============================
def extract_text(image_path, is_handwritten=False):
    """ Extract text using OCR (with different config for handwritten) """
    try:
        img = Image.open(image_path)
        custom_config = "--oem 3 --psm 6" if is_handwritten else ""  # Improve handwritten text recognition
        text = pytesseract.image_to_string(img, config=custom_config)
        return text.strip()
    except Exception as e:
        print(f"OCR Error: {str(e)}")
        return None

# Helper functions
def search_medications(query):
    # Placeholder for medication search functionality
    # In a real app, this would query a medication database
    # For now, return a sample list for demonstration
    sample_meds = [
        {'id': 1, 'name': 'Aspirin', 'dosage': '500mg'},
        {'id': 2, 'name': 'Ibuprofen', 'dosage': '200mg'},
        {'id': 3, 'name': 'Acetaminophen', 'dosage': '500mg'}
    ]
    
    return [med for med in sample_meds if query.lower() in med['name'].lower()]

def get_medication_details(medication_id):
    # Placeholder for medication details
    sample_meds = {
        1: {'name': 'Aspirin', 'dosage': '500mg', 'description': 'Pain reliever'},
        2: {'name': 'Ibuprofen', 'dosage': '200mg', 'description': 'Anti-inflammatory'},
        3: {'name': 'Acetaminophen', 'dosage': '500mg', 'description': 'Fever reducer'}
    }
    
    return sample_meds.get(medication_id)

def process_prescription(prescription_id):
    """Process the prescription image and extract text using OCR"""
    prescription = Prescription.query.get(prescription_id)
    if not prescription:
        return None
    
    # Get the file path
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], prescription.filename)
    
    # Perform OCR
    extracted_text = extract_text(file_path, is_handwritten=prescription.is_handwritten)
    
    # Save the extracted text to the prescription
    if extracted_text:
        prescription.extracted_text = extracted_text
        prescription.status = 'Processed'
        db.session.commit()
    
    # Parse the extracted text for medications (simple implementation)
    # In a real app, this would use NLP/ML to extract medication details
    if extracted_text:
        lines = extracted_text.split('\n')
        for line in lines:
            if 'rx:' in line.lower() or 'medication:' in line.lower():
                # Extract medication from the line (simplified approach)
                parts = line.split(':')
                if len(parts) > 1:
                    med_info = parts[1].strip()
                    # Look for dosage information
                    dosage = None
                    for part in med_info.split():
                        if part.lower().endswith('mg') or part.lower().endswith('ml'):
                            dosage = part
                            med_name = med_info.replace(dosage, '').strip()
                            break
                    else:
                        med_name = med_info
                        
                    # Create a new medication record
                    medication = Medication(
                        prescription_id=prescription.id,
                        name=med_name,
                        dosage=dosage
                    )
                    db.session.add(medication)
        
        # If no medications were found, add a placeholder
        if not Medication.query.filter_by(prescription_id=prescription.id).first():
            medication = Medication(
                prescription_id=prescription.id,
                name="Medication (please edit)",
                dosage="Unknown"
            )
            db.session.add(medication)
            
        db.session.commit()
    
    # Get result for display
    result = {
        'prescription_id': prescription.id,
        'extracted_text': extracted_text or "No text could be extracted",
        'status': prescription.status,
        'medications': [
            {
                'name': med.name,
                'dosage': med.dosage,
                'frequency': med.frequency,
                'duration': med.duration
            }
            for med in Medication.query.filter_by(prescription_id=prescription.id).all()
        ],
        'is_handwritten': prescription.is_handwritten,
        'confidence': 95.5  # Placeholder - real OCR would provide confidence scores
    }
    
    return result

# ==============================
# AUTHENTICATION BLUEPRINT
# ==============================
auth_bp = Blueprint('auth_bp', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('auth_bp.login'))

        user = User.get_user_by_email(email)
        if user and user.verify_password(password):
            session['user_id'] = user.id
            session['username'] = user.username  
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'danger')

    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('auth_bp.register'))

        if User.get_user_by_email(email):
            flash('Email already registered!', 'warning')
        else:
            user = User(username=username, email=email, password=password)
            db.session.add(user)
            db.session.commit()
            flash('Registration successful!', 'success')
            return redirect(url_for('auth_bp.login'))
    return render_template('register.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('index'))

app.register_blueprint(auth_bp)

# ==============================
# MAIN ROUTES
# ==============================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("You need to log in first.", "warning")
        return redirect(url_for('auth_bp.login'))
    
    user = User.get_user_by_id(session['user_id'])
    if user is None:
        flash("User not found. Please login again.", "danger")
        session.clear()
        return redirect(url_for('auth_bp.login'))
        
    prescriptions = Prescription.query.filter_by(user_id=user.id).all()
    return render_template('dashboard.html', user=user, prescriptions=prescriptions)

@app.route('/medications', methods=['GET', 'POST'])
def medications():
    if 'user_id' not in session:
        flash("You need to log in first.", "warning")
        return redirect(url_for('auth_bp.login'))
    
    search_query = request.args.get('search', '')
    medication_results = []
    
    if search_query:
        medication_results = search_medications(search_query)
    
    return render_template('medications.html', search_query=search_query, 
                          medication_results=medication_results)

@app.route('/history')
def history():
    if 'user_id' not in session:
        flash("You need to log in first.", "warning")
        return redirect(url_for('auth_bp.login'))
    
    user = User.get_user_by_id(session['user_id'])
    if user is None:
        flash("User not found. Please login again.", "danger")
        session.clear()
        return redirect(url_for('auth_bp.login'))
        
    prescriptions = Prescription.query.filter_by(user_id=user.id).all()
    return render_template('history.html', prescriptions=prescriptions)

@app.route('/ocr_prescription', methods=['GET', 'POST'])
def ocr_prescription():
    if 'user_id' not in session:
        flash("You need to log in first.", "warning")
        return redirect(url_for('auth_bp.login'))
        
    if request.method == 'POST':
        # Check if a file was uploaded
        if 'prescription_image' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
            
        file = request.files['prescription_image']
        
        # If no file selected
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            # Secure the filename to prevent path traversal attacks
            filename = secure_filename(file.filename)
            
            # Add timestamp to ensure uniqueness
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"{timestamp}_{filename}"
            
            # Save the file
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Get optional parameters
            is_handwritten = 'is_handwritten' in request.form
            language = request.form.get('language', 'auto')
            find_alternatives = 'find_alternatives' in request.form
            check_interactions = 'check_interactions' in request.form
            insurance_coverage = 'insurance_coverage' in request.form
            
            # Create a new prescription record
            prescription = Prescription(
                user_id=session['user_id'],
                filename=filename,
                is_handwritten=is_handwritten,
                language=language,
                find_alternatives=find_alternatives,
                check_interactions=check_interactions,
                insurance_coverage=insurance_coverage
            )
            
            db.session.add(prescription)
            db.session.commit()
            
            # Process the prescription
            result = process_prescription(prescription.id)
            
            if result:
                # Redirect to results page
                return redirect(url_for('view_prescription', prescription_id=prescription.id))
            else:
                flash('There was a problem processing your prescription.', 'danger')
                return redirect(url_for('dashboard'))
                
        else:
            flash(f'Allowed file types are: {", ".join(ALLOWED_EXTENSIONS)}', 'warning')
            return redirect(request.url)
            
    return render_template('ocr_upload.html')

@app.route('/upload_prescription')
def upload_prescription():
    if 'user_id' not in session:
        flash("You need to log in first.", "warning")
        return redirect(url_for('auth_bp.login'))
    
    # This simply renders the upload form
    return render_template('ocr_upload.html')

@app.route('/prescription/<int:prescription_id>')
def view_prescription(prescription_id):
    if 'user_id' not in session:
        flash("You need to log in first.", "warning")
        return redirect(url_for('auth_bp.login'))
        
    prescription = Prescription.query.get_or_404(prescription_id)
    
    # Security check - only allow users to view their own prescriptions
    if prescription.user_id != session['user_id']:
        flash("You don't have permission to view this prescription.", "danger")
        return redirect(url_for('dashboard'))
        
    # Get the OCR results
    result = {
        'prescription_id': prescription.id,
        'extracted_text': prescription.extracted_text or "No text could be extracted",
        'status': prescription.status,
        'medications': [
            {
                'name': med.name,
                'dosage': med.dosage,
                'frequency': med.frequency,
                'duration': med.duration
            }
            for med in Medication.query.filter_by(prescription_id=prescription.id).all()
        ],
        'is_handwritten': prescription.is_handwritten,
        'confidence': 95.5  # Placeholder
    }
    
    if not result:
        flash("Could not retrieve prescription data.", "danger")
        return redirect(url_for('dashboard'))
    
    return render_template('ocr_results.html', result=result, prescription=prescription)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    if 'user_id' not in session:
        flash("You need to log in first.", "warning")
        return redirect(url_for('auth_bp.login'))
        
    # Security check to ensure only prescription owners can access files
    prescription = Prescription.query.filter_by(filename=filename).first()
    
    if not prescription or prescription.user_id != session['user_id']:
        flash("You don't have permission to access this file.", "danger")
        return redirect(url_for('dashboard'))
        
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        flash("You need to log in first.", "warning")
        return redirect(url_for('auth_bp.login'))
        
    user = User.get_user_by_id(session['user_id'])
    
    if request.method == 'POST':
        # Update user profile
        name = request.form.get('name')
        email = request.form.get('email')
        
        # Basic validation
        if email and email != user.email and User.get_user_by_email(email):
            flash("Email already in use", "danger")
        else:
            user.name = name
            if email:
                user.email = email
                
            # Update password if provided
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            
            if current_password and new_password:
                if user.verify_password(current_password):
                    user.password_hash = generate_password_hash(new_password)
                    flash("Password updated successfully", "success")
                else:
                    flash("Current password is incorrect", "danger")
                    
            db.session.commit()
            flash("Profile updated successfully", "success")
            
    return render_template('profile.html', user=user)


@app.route('/alternative_medications')
def alternative_medications():
    # Example data for alternative medications
    alternatives = [
        {
            'original_name': 'Lipitor',
            'original_type': 'branded',
            'original_dosage': '20mg',
            'original_frequency': 'Once daily',
            'original_price': 250,
            'original_coverage': False,
            'alternatives': [
                {
                    'name': 'Atorvastatin',
                    'type': 'generic',
                    'dosage': '20mg',
                    'manufacturer': 'Cipla Ltd.',
                    'similarity_score': 98,
                    'price': 75,
                    'coverage': True,
                    'recommended': True
                },
                {
                    'name': 'Simvastatin',
                    'type': 'generic',
                    'dosage': '40mg',
                    'manufacturer': 'Sun Pharma',
                    'similarity_score': 85,
                    'price': 60,
                    'coverage': True,
                    'recommended': False
                }
            ]
        },
        {
            'original_name': 'Crestor',
            'original_type': 'branded',
            'original_dosage': '10mg',
            'original_frequency': 'Once daily',
            'original_price': 320,
            'original_coverage': False,
            'alternatives': [
                {
                    'name': 'Rosuvastatin',
                    'type': 'generic',
                    'dosage': '10mg',
                    'manufacturer': 'Dr. Reddy\'s',
                    'similarity_score': 99,
                    'price': 110,
                    'coverage': True,
                    'recommended': True
                }
            ]
        }
    ]
    
    return render_template('components/alternative_medications.html', alternatives=alternatives)


@app.route('/drug_interactions')
def drug_interactions():
    # Example data for drug interactions
    interactions = {
        'high_count': 1,
        'moderate_count': 2,
        'low_count': 1,
        'items': [
            {
                'severity': 'high',
                'medication1': 'Warfarin',
                'medication2': 'Aspirin',
                'description': 'Combining these medications increases the risk of bleeding.',
                'effects': [
                    'Increased risk of internal bleeding',
                    'Prolonged bleeding time',
                    'Higher risk of gastrointestinal bleeding'
                ],
                'recommendations': [
                    'Avoid concurrent use if possible',
                    'If concurrent use necessary, monitor closely for signs of bleeding',
                    'Consider reducing dosage of warfarin'
                ],
                'references': [
                    {'title': 'Drug Interaction Study (2024)', 'url': '#'},
                    {'title': 'Clinical Guidelines on Anticoagulants', 'url': '#'}
                ]
            },
            {
                'severity': 'moderate',
                'medication1': 'Fluoxetine',
                'medication2': 'Ibuprofen',
                'description': 'This combination may increase the risk of gastrointestinal bleeding.',
                'effects': [
                    'Increased risk of stomach bleeding',
                    'Possible stomach ulcers',
                    'Reduced effectiveness of ibuprofen'
                ],
                'recommendations': [
                    'Consider alternative pain relievers like acetaminophen',
                    'Take ibuprofen with food',
                    'Monitor for signs of stomach bleeding'
                ],
                'references': [
                    {'title': 'SSRI-NSAID Interaction Study', 'url': '#'}
                ]
            }
        ]
    }
    
    return render_template('components/drug_interactions.html', interactions=interactions)

@app.route('/prescription_detail/<int:prescription_id>')
def prescription_detail(prescription_id):
    if 'user_id' not in session:
        flash("You need to log in first.", "warning")
        return redirect(url_for('auth_bp.login'))
    
    user = User.get_user_by_id(session['user_id'])
    if user is None:
        flash("User not found. Please login again.", "danger")
        session.clear()
        return redirect(url_for('auth_bp.login'))
        
    prescription = Prescription.query.get_or_404(prescription_id)
    
    # Security check - ensure user can only view their own prescriptions
    if prescription.user_id != user.id:
        flash("You don't have permission to view this prescription.", "danger")
        return redirect(url_for('history'))
        
    return render_template('components/prescription_detail.html', prescription=prescription)

@app.route('/delete_prescription/<int:prescription_id>', methods=['POST'])
def delete_prescription(prescription_id):
    if 'user_id' not in session:
        flash("You need to log in first.", "warning")
        return redirect(url_for('auth_bp.login'))
    
    user = User.get_user_by_id(session['user_id'])
    if user is None:
        flash("User not found. Please login again.", "danger")
        session.clear()
        return redirect(url_for('auth_bp.login'))
        
    prescription = Prescription.query.get_or_404(prescription_id)
    
    # Security check - ensure user can only delete their own prescriptions
    if prescription.user_id != user.id:
        flash("You don't have permission to delete this prescription.", "danger")
        return redirect(url_for('history'))
    
    # Delete the prescription file if it exists
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], prescription.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Delete the prescription from the database (cascade will delete related medications)
    db.session.delete(prescription)
    db.session.commit()
    
    flash('Prescription deleted successfully!', 'success')
    return redirect(url_for('history'))

# ==============================
# API ROUTES
# ==============================
@app.route('/api/search_medication')
def api_search_medication():
    query = request.args.get('q', '')
    if not query or len(query) < 2:
        return jsonify([])
        
    results = search_medications(query)
    return jsonify([{'name': med['name'], 'id': med['id']} for med in results[:10]])

@app.route('/api/medication_details/<int:medication_id>')
def api_medication_details(medication_id):
    details = get_medication_details(medication_id)
    if details:
        return jsonify(details)
    else:
        return jsonify({'error': 'Medication not found'}), 404

# ==============================
# ERROR HANDLERS
# ==============================
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500

# ==============================
# INITIALIZE DATABASE
# ==============================
with app.app_context():
    db.create_all()

# ==============================
# RUN APPLICATION
# ==============================
if __name__ == '__main__':
    app.run(debug=True)