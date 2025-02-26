import spacy
from spacy.tokens import Doc, Span
import re
import numpy as np
from utils.logger import get_logger

logger = get_logger(__name__)

class MedicalNER:
    """Named Entity Recognition for medical prescriptions"""
    
    def __init__(self, model_path=None):
        """
        Initialize the NER model
        
        Args:
            model_path: Path to a custom spaCy model, if None use a pretrained model
        """
        try:
            # Load medical NER model
            if model_path:
                self.nlp = spacy.load(model_path)
                logger.info(f"Loaded custom NER model from {model_path}")
            else:
                # Load general model and configure for medical domain
                self.nlp = spacy.load("en_core_web_lg")
                logger.info("Loaded standard spaCy model")
                
            # Add custom entity recognizer pipe for prescriptions
            if "prescription_ner" not in self.nlp.pipe_names:
                self.nlp.add_pipe("prescription_ner", after="ner")
                logger.info("Added prescription NER component")
                
            # Medication-related patterns
            self.medication_patterns = {
                'dose_pattern': r'(\d+(?:\.\d+)?)\s*(mg|g|ml|mcg|IU)',
                'frequency_pattern': r'(\d+(?:-\d+)?)\s*times?\s*(?:a|per)\s*(day|daily|week|month|hour|evening|morning|night|noon)',
                'duration_pattern': r'for\s+(\d+(?:-\d+)?)\s*(days?|weeks?|months?|years?)',
                'route_pattern': r'(oral|IV|intravenous|topical|sublingual|subcutaneous|intramuscular|rectal|inhaled)'
            }
            
            # Common drug names and categories
            self.drug_categories = [
                'antibiotic', 'analgesic', 'antipyretic', 'antihistamine',
                'antihypertensive', 'antidepressant', 'antipsychotic', 'diuretic',
                'steroid', 'nsaid', 'statin', 'sedative', 'laxative'
            ]
            
            # Load common medication names
            self.medications = self._load_medications()
            
        except Exception as e:
            logger.error(f"Error initializing Medical NER: {str(e)}")
            raise
            
    def _load_medications(self):
        """Load common medication names from a resource file"""
        try:
            # This would typically load from a database or file
            # For demonstration, a small sample list is used
            medications = [
                "acetaminophen", "paracetamol", "ibuprofen", "aspirin", "amoxicillin",
                "lisinopril", "metformin", "atorvastatin", "levothyroxine", "amlodipine",
                "metoprolol", "albuterol", "omeprazole", "losartan", "gabapentin",
                "hydrochlorothiazide", "sertraline", "fluoxetine", "montelukast", "pantoprazole"
            ]
            return medications
        except Exception as e:
            logger.error(f"Error loading medications: {str(e)}")
            return []
            
    def extract_entities(self, text):
        """
        Extract medical entities from prescription text
        
        Args:
            text: Prescription text
            
        Returns:
            dict: Dictionary of extracted entities
        """
        try:
            # Process the text with spaCy
            doc = self.nlp(text)
            
            # Extract standard entities
            entities = {
                'medications': [],
                'dosages': [],
                'frequencies': [],
                'durations': [],
                'routes': []
            }
            
            # Extract medications from general entities
            for ent in doc.ents:
                if ent.label_ in ['ORG', 'PRODUCT', 'GPE']:
                    # Check if this might be a medication
                    if any(med in ent.text.lower() for med in self.medications):
                        entities['medications'].append({
                            'text': ent.text,
                            'start': ent.start_char,
                            'end': ent.end_char
                        })
                        
            # Extract medication names based on our custom dictionary
            for med in self.medications:
                med_regex = r'\b' + re.escape(med) + r'\b'
                for match in re.finditer(med_regex, text, re.IGNORECASE):
                    entities['medications'].append({
                        'text': match.group(0),
                        'start': match.start(),
                        'end': match.end()
                    })
                    
            # Extract dosages using regex
            for match in re.finditer(self.medication_patterns['dose_pattern'], text):
                entities['dosages'].append({
                    'text': match.group(0),
                    'value': match.group(1),
                    'unit': match.group(2),
                    'start': match.start(),
                    'end': match.end()
                })
                
            # Extract frequencies
            for match in re.finditer(self.medication_patterns['frequency_pattern'], text):
                entities['frequencies'].append({
                    'text': match.group(0),
                    'count': match.group(1),
                    'period': match.group(2),
                    'start': match.start(),
                    'end': match.end()
                })
                
            # Extract durations
            for match in re.finditer(self.medication_patterns['duration_pattern'], text):
                entities['durations'].append({
                    'text': match.group(0),
                    'count': match.group(1),
                    'unit': match.group(2),
                    'start': match.start(),
                    'end': match.end()
                })
                
            # Extract administration routes
            for match in re.finditer(self.medication_patterns['route_pattern'], text):
                entities['routes'].append({
                    'text': match.group(0),
                    'route': match.group(1),
                    'start': match.start(),
                    'end': match.end()
                })
                
            # Get prescription structured details
            prescription_details = self._structure_prescription(entities, text)
            
            return {
                'entities': entities,
                'prescription': prescription_details
            }
            
        except Exception as e:
            logger.error(f"Error extracting medical entities: {str(e)}")
            return {'error': str(e)}
            
    def _structure_prescription(self, entities, text):
        """
        Structure entities into prescription details
        
        Args:
            entities: Extracted entities
            text: Original text
            
        Returns:
            list: Structured prescription details
        """
        prescriptions = []
        
        # Try to associate medications with their details
        for med in entities['medications']:
            med_start = med['start']
            med_end = med['end']
            
            # Find closest dosage
            closest_dosage = self._find_closest_entity(med_end, entities['dosages'])
            
            # Find closest frequency
            closest_frequency = self._find_closest_entity(med_end, entities['frequencies'])
            
            # Find closest duration
            closest_duration = self._find_closest_entity(med_end, entities['durations'])
            
            # Find closest route
            closest_route = self._find_closest_entity(med_end, entities['routes'])
            
            # Create structured prescription
            prescription = {
                'medication': med['text'],
                'dosage': closest_dosage['text'] if closest_dosage else None,
                'frequency': closest_frequency['text'] if closest_frequency else None,
                'duration': closest_duration['text'] if closest_duration else None,
                'route': closest_route['text'] if closest_route else None
            }
            
            prescriptions.append(prescription)
            
        return prescriptions
        
    def _find_closest_entity(self, position, entity_list):
        """Find the entity closest to a position in text"""
        if not entity_list:
            return None
            
        distances = [abs(e['start'] - position) for e in entity_list]
        min_distance_index = np.argmin(distances)
        
        # Only return if reasonably close (within 100 characters)
        if distances[min_distance_index] <= 100:
            return entity_list[min_distance_index]
        return None
        
    def get_drug_interactions(self, medications):
        """
        Check for potential drug interactions between medications
        
        Args:
            medications: List of medication names
            
        Returns:
            list: Potential interactions
        """
        # This would typically call an external API or database
        # For demonstration, using a simplified approach
        
        # Sample interaction pairs (would be from a database)
        interaction_pairs = [
            ('ibuprofen', 'aspirin', 'Increased risk of bleeding'),
            ('lisinopril', 'potassium', 'Risk of hyperkalemia'),
            ('warfarin', 'aspirin', 'Increased risk of bleeding'),
            ('fluoxetine', 'sertraline', 'Serotonin syndrome risk')
        ]
        
        # Normalize medication names
        normalized_meds = [med.lower().strip() for med in medications]
        
        # Check for interactions
        interactions = []
        for med1, med2, risk in interaction_pairs:
            if med1 in normalized_meds and med2 in normalized_meds:
                interactions.append({
                    'medication1': med1,
                    'medication2': med2,
                    'risk': risk,
                    'severity': 'high'  # Would be determined by the database
                })
                
        return interactions
        
    def validate_prescription(self, prescription):
        """
        Validate a prescription for completeness and correctness
        
        Args:
            prescription: Structured prescription dictionary
            
        Returns:
            dict: Validation results
        """
        validation = {
            'is_valid': True,
            'missing_fields': [],
            'warnings': []
        }
        
        # Check required fields
        required_fields = ['medication', 'dosage', 'frequency']
        for field in required_fields:
            if not prescription.get(field):
                validation['is_valid'] = False
                validation['missing_fields'].append(field)
                
        # Check if medication name is recognized
        if prescription.get('medication'):
            med_name = prescription['medication'].lower()
            if not any(med.lower() in med_name for med in self.medications):
                validation['warnings'].append(f"Medication '{prescription['medication']}' not recognized")
                
        return validation