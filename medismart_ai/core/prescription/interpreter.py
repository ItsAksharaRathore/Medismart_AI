# core/prescription/interpreter.py
from ml.nlp.medical_ner import extract_medical_entities
from ml.nlp.context_analyzer import analyze_context
from utils.logger import get_logger
from db.medication_db import get_medication_details, find_alternative_medications
from db.interaction_checker import check_drug_interactions

logger = get_logger(__name__)

def interpret_prescription(ocr_data):
    """
    Interpret the OCR extracted text to identify medications, dosages, etc.
    
    Args:
        ocr_data: Dictionary with OCR extracted text and metadata
        
    Returns:
        Dictionary with structured prescription data
    """
    try:
        text = ocr_data['full_text']
        language = ocr_data['language']
        is_handwritten = ocr_data.get('is_handwritten', False)
        
        # Extract medical entities (drugs, dosages, frequencies, etc.)
        # If handwritten, use more flexible extraction params
        entities = extract_medical_entities(text, language, is_handwritten=is_handwritten)
        
        # Analyze context to understand prescription intent
        context = analyze_context(text, entities)
        
        # Structure the prescription data
        prescription = {
            'doctor': _extract_doctor_info(entities, context),
            'patient': _extract_patient_info(entities, context),
            'date': _extract_date(entities, context),
            'medications': _extract_medications(entities, context),
            'diagnosis': _extract_diagnosis(entities, context),
            'instructions': _extract_instructions(entities, context),
            'confidence': {
                'overall': ocr_data['confidence'],
                'medications': _calculate_medication_confidence(entities)
            }
        }
        
        return prescription
        
    except Exception as e:
        logger.error(f"Prescription interpretation error: {str(e)}")
        raise

def suggest_medicines(medications, find_alternatives=False, check_interactions=False):
    """
    Get additional information and suggestions for medications
    
    Args:
        medications: List of medication dictionaries
        find_alternatives: Boolean to find alternative medications
        check_interactions: Boolean to check for interactions
        
    Returns:
        Extended medication list with details and suggestions
    """
    try:
        enriched_medications = []
        all_meds = []
        
        for med in medications:
            # Get additional details about the medication
            med_details = get_medication_details(med['name'])
            
            # Add details to the medication dict
            enriched_med = {**med, **med_details}
            
            # Find alternative medications if requested
            if find_alternatives:
                enriched_med['alternatives'] = find_alternative_medications(
                    med['name'], 
                    strength=med.get('strength'), 
                    form=med_details.get('form')
                )
            
            enriched_medications.append(enriched_med)
            all_meds.append(med['name'])
        
        # Check for drug interactions if requested
        if check_interactions and len(all_meds) > 1:
            interactions = check_drug_interactions(all_meds)
            
            # Add interaction warnings to each medication
            for med in enriched_medications:
                med['interactions'] = [
                    interaction for interaction in interactions
                    if med['name'] in interaction['drugs']
                ]
        
        return enriched_medications
        
    except Exception as e:
        logger.error(f"Medicine suggestion error: {str(e)}")
        # Return original medications if error
        return medications

def _extract_doctor_info(entities, context):
    """Extract doctor information from entities"""
    doctor_info = {}
    
    # Extract doctor name
    if 'DOCTOR' in entities:
        doctor_info['name'] = entities['DOCTOR'][0] if entities['DOCTOR'] else None
    
    # Extract clinic/hospital
    if 'ORGANIZATION' in entities:
        doctor_info['organization'] = entities['ORGANIZATION'][0] if entities['ORGANIZATION'] else None
    
    # Extract contact information
    if 'CONTACT' in entities:
        contacts = entities['CONTACT']
        for contact in contacts:
            if '@' in contact:
                doctor_info['email'] = contact
            elif contact.replace('-', '').isdigit():
                doctor_info['phone'] = contact
                
    return doctor_info

def _extract_patient_info(entities, context):
    """Extract patient information from entities"""
    patient_info = {}
    
    # Extract patient name
    if 'PATIENT' in entities:
        patient_info['name'] = entities['PATIENT'][0] if entities['PATIENT'] else None
    
    # Extract patient age/DOB
    if 'AGE' in entities:
        patient_info['age'] = entities['AGE'][0] if entities['AGE'] else None
    
    if 'DOB' in entities:
        patient_info['dob'] = entities['DOB'][0] if entities['DOB'] else None
    
    # Extract patient ID/insurance
    if 'ID' in entities:
        patient_info['id'] = entities['ID'][0] if entities['ID'] else None
        
    return patient_info

def _extract_date(entities, context):
    """Extract prescription date"""
    if 'DATE' in entities and entities['DATE']:
        return entities['DATE'][0]
    return None

def _extract_medications(entities, context):
    """Extract medications with dosages and instructions"""
    medications = []
    
    if 'MEDICATION' in entities and entities['MEDICATION']:
        for i, med in enumerate(entities['MEDICATION']):
            medication = {
                'name': med,
                'dosage': _get_dosage(entities, i),
                'frequency': _get_frequency(entities, i),
                'duration': _get_duration(entities, i),
                'route': _get_route(entities, i),
                'instructions': _get_med_instructions(entities, i),
                'strength': _get_strength(entities, i)
            }
            medications.append(medication)
            
    return medications

def _get_dosage(entities, index):
    """Get dosage for medication at given index"""
    if 'DOSAGE' in entities and len(entities['DOSAGE']) > index:
        return entities['DOSAGE'][index]
    return None

def _get_frequency(entities, index):
    """Get frequency for medication at given index"""
    if 'FREQUENCY' in entities and len(entities['FREQUENCY']) > index:
        return entities['FREQUENCY'][index]
    return None

def _get_duration(entities, index):
    """Get duration for medication at given index"""
    if 'DURATION' in entities and len(entities['DURATION']) > index:
        return entities['DURATION'][index]
    return None

def _get_route(entities, index):
    """Get administration route for medication at given index"""
    if 'ROUTE' in entities and len(entities['ROUTE']) > index:
        return entities['ROUTE'][index]
    return None

def _get_med_instructions(entities, index):
    """Get specific instructions for medication at given index"""
    if 'MED_INSTRUCTION' in entities and len(entities['MED_INSTRUCTION']) > index:
        return entities['MED_INSTRUCTION'][index]
    return None

def _get_strength(entities, index):
    """Get medication strength at given index"""
    if 'STRENGTH' in entities and len(entities['STRENGTH']) > index:
        return entities['STRENGTH'][index]
    return None

def _extract_diagnosis(entities, context):
    """Extract diagnosis information"""
    if 'DIAGNOSIS' in entities and entities['DIAGNOSIS']:
        return entities['DIAGNOSIS']
    return []

def _extract_instructions(entities, context):
    """Extract general instructions"""
    if 'INSTRUCTION' in entities and entities['INSTRUCTION']:
        return entities['INSTRUCTION']
    return []

def _calculate_medication_confidence(entities):
    """Calculate confidence score for medications extraction"""
    # Simple heuristic: if we have medications and at least dosage or frequency,
    # we have higher confidence
    if 'MEDICATION' not in entities or not entities['MEDICATION']:
        return 0.0
        
    has_dosage = 'DOSAGE' in entities and entities['DOSAGE']
    has_frequency = 'FREQUENCY' in entities and entities['FREQUENCY']
    
    if has_dosage and has_frequency:
        return 0.9
    elif has_dosage or has_frequency:
        return 0.7
    else:
        return 0.5