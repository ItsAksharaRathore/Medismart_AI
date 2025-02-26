from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
import os
import json
import uuid
from datetime import datetime
from models.user import User, Prescription, AlternativeMedication, DrugInteraction
from app import db, app

prescription_bp = Blueprint('prescription_bp', __name__)

# Helper function to check allowed file extensions
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'tiff'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@prescription_bp.route('/upload', methods=['GET', 'POST'])
def upload_prescription():
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login'))
    
    if request.method == 'POST':
        # Check if file was uploaded
        if 'prescription_image' not in request.files:
            flash('No file selected')
            return redirect(request.url)
        
        file = request.files['prescription_image']
        
        # Check if filename is empty
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # Generate unique filename to prevent collisions
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)
            
            # Create new prescription record
            new_prescription = Prescription(
                user_id=session['user_id'],
                prescription_image=unique_filename,
                status='processing'
            )
            
            db.session.add(new_prescription)
            db.session.commit()
            
            # In a real app, this is where you'd trigger the OCR and processing
            # For demo purposes, we'll simulate the processing with mock data
            simulate_prescription_processing(new_prescription.id)
            
            flash('Prescription uploaded successfully and is being processed')
            return redirect(url_for('prescription_bp.view_prescription', prescription_id=new_prescription.id))
        else:
            flash('Invalid file type. Please upload an image or PDF file.')
    
    return render_template('prescription_upload.html')

@prescription_bp.route('/prescription/<int:prescription_id>')
def view_prescription(prescription_id):
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login'))
    
    prescription = Prescription.query.get_or_404(prescription_id)
    
    # Security check: ensure user can only access their own prescriptions
    if prescription.user_id != session['user_id'] and session.get('role') != 'admin':
        flash('Access denied')
        return redirect(url_for('dashboard'))
    
    # Get related data
    alternatives = AlternativeMedication.query.filter_by(prescription_id=prescription_id).all()
    interactions = DrugInteraction.query.filter_by(prescription_id=prescription_id).all()
    
    return render_template('prescription_detail.html', 
                          prescription=prescription,
                          alternatives=alternatives,
                          interactions=interactions)

# This function simulates the OCR and processing that would happen
# In a real app, this would likely be an asynchronous task
def simulate_prescription_processing(prescription_id):
    prescription = Prescription.query.get(prescription_id)
    
    # Simulate OCR extraction
    mock_ocr_text = "Dr. Jane Smith\nPatient: John Doe\nDate: 2025-02-20\n\n1. Amoxicillin 500mg - Take 1 capsule three times daily for 7 days\n2. Ibuprofen 400mg - Take 1 tablet every 6 hours as needed for pain\n3. Loratadine 10mg - Take 1 tablet daily for allergies"
    prescription.ocr_text = mock_ocr_text
    
    # Simulate extracted medications
    mock_medications = [
        {
            "name": "Amoxicillin",
            "dosage": "500mg",
            "frequency": "three times daily",
            "duration": "7 days",
            "purpose": "antibiotic"
        },
        {
            "name": "Ibuprofen",
            "dosage": "400mg",
            "frequency": "every 6 hours as needed",
            "duration": "",
            "purpose": "pain relief"
        },
        {
            "name": "Loratadine",
            "dosage": "10mg",
            "frequency": "daily",
            "duration": "",
            "purpose": "allergies"
        }
    ]
    prescription.medications = json.dumps(mock_medications)
    prescription.status = 'completed'
    
    # Simulate alternative medications
    alternatives = [
        AlternativeMedication(
            prescription_id=prescription_id,
            original_medication="Amoxicillin 500mg",
            alternative_medication="Ampicillin 500mg",
            cost_difference=-15.50,
            efficacy_rating=0.95,
            reason="Generic alternative with similar efficacy at lower cost"
        ),
        AlternativeMedication(
            prescription_id=prescription_id,
            original_medication="Ibuprofen 400mg",
            alternative_medication="Naproxen 250mg",
            cost_difference=-5.25,
            efficacy_rating=0.90,
            reason="Different NSAID with longer half-life, requiring fewer doses"
        )
    ]
    
    # Simulate drug interactions
    interactions = [
        DrugInteraction(
            prescription_id=prescription_id,
            medication1="Ibuprofen",
            medication2="Amoxicillin",
            severity="mild",
            description="Ibuprofen may decrease the effectiveness of Amoxicillin",
            recommendation="Consider taking at different times"
        )
    ]
    
    # Add generated data to database
    db.session.add_all(alternatives + interactions)
    db.session.commit()

@prescription_bp.route('/prescriptions')
def prescription_history():
    if 'user_id' not in session:
        return redirect(url_for('auth_bp.login'))
    
    prescriptions = Prescription.query.filter_by(user_id=session['user_id']).order_by(Prescription.upload_date.desc()).all()
    return render_template('prescription_history.html', prescriptions=prescriptions)