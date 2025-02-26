
# api/routes/prescription_routes.py
from flask import Blueprint, request, jsonify
from core.prescription.preprocessor import preprocess_image
from core.prescription.ocr_engine import extract_text
from core.prescription.interpreter import interpret_prescription
from core.drug.alternatives import find_alternatives
from core.recommendation.cost_optimizer import optimize_cost
from data.mongodb.prescription_repo import PrescriptionRepository
from security.anonymizer import anonymize_data
from utils.validators import validate_prescription_request

prescription_bp = Blueprint('prescription', __name__)
prescription_repo = PrescriptionRepository()

@prescription_bp.route('/process', methods=['POST'])
def process_prescription():
    """Process a prescription image and return interpreted data with recommendations"""
    # Validate request
    if not validate_prescription_request(request):
        return jsonify({"error": "Invalid request"}), 400
    
    try:
        # Get image from request
        image_file = request.files.get('prescription')
        user_id = request.form.get('user_id')
        insurance_provider = request.form.get('insurance_provider', None)
        
        # Process the prescription
        # 1. Preprocess the image
        processed_image = preprocess_image(image_file)
        
        # 2. Extract text using OCR
        extracted_text = extract_text(processed_image)
        
        # 3. Interpret the medical text
        prescription_data = interpret_prescription(extracted_text)
        
        # 4. Find alternative medications
        alternatives = find_alternatives(prescription_data['medications'])
        
        # 5. Optimize cost based on insurance if provided
        if insurance_provider:
            optimized_options = optimize_cost(
                alternatives, 
                insurance_provider
            )
        else:
            optimized_options = optimize_cost(alternatives)
        
        # 6. Anonymize data for storage
        anonymized_data = anonymize_data(prescription_data)
        
        # 7. Store in database
        prescription_id = prescription_repo.save_prescription(
            user_id=user_id,
            prescription_data=anonymized_data
        )
        
        # 8. Prepare response
        response = {
            "prescription_id": prescription_id,
            "interpreted_data": prescription_data,
            "alternatives": optimized_options
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@prescription_bp.route('/<prescription_id>', methods=['GET'])
def get_prescription(prescription_id):
    """Get a previously processed prescription by ID"""
    try:
        prescription = prescription_repo.get_prescription_by_id(prescription_id)
        if not prescription:
            return jsonify({"error": "Prescription not found"}), 404
            
        return jsonify(prescription), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

