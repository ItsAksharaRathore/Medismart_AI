
# core/recommendation/insurance_matcher.py
from utils.logger import get_logger

logger = get_logger(__name__)

def match_insurance_coverage(medications, insurance_provider):
    """
    Match medications with insurance coverage information
    
    Args:
        medications: List of medication dictionaries
        insurance_provider: Insurance provider name
        
    Returns:
        Medications with added insurance coverage information
    """
    try:
        # Get coverage information
        coverage_info = _get_insurance_coverage(insurance_provider)
        
        # Add coverage information to medications
        for med in medications:
            med_name = med['name'].lower()
            
            # Try exact match
            if med_name in coverage_info:
                med['insurance'] = coverage_info[med_name]
                continue
                
            # Try generic name match
            if 'generic_name' in med and med['generic_name']:
                generic_name = med['generic_name'].lower()
                if generic_name in coverage_info:
                    med['insurance'] = coverage_info[generic_name]
                    continue
            
            # Try partial matches (could be improved with fuzzy matching)
            for covered_med, info in coverage_info.items():
                if covered_med in med_name or med_name in covered_med:
                    med['insurance'] = info
                    med['insurance']['partial_match'] = True
                    break
            
            # No match found
            if 'insurance' not in med:
                med['insurance'] = {
                    'covered': False,
                    'message': 'Not covered by your insurance'
                }
        
        return medications
        
    except Exception as e:
        logger.error(f"Insurance matching error: {str(e)}")
        raise

def _get_insurance_coverage(insurance_provider):
    """Get insurance coverage information (mock implementation)"""
    # In a real system, this would query an insurance API or database
    # For now, using mock data
    
    mock_coverage = {
        # Generic medications
        'amoxicillin': {
            'covered': True,
            'tier': 1,
            'coverage_percentage': 90,
            'copay': 5,
            'prior_authorization': False
        },
        'lisinopril': {
            'covered': True,
            'tier': 1,
            'coverage_percentage': 90,
            'copay': 5,
            'prior_authorization': False
        },
        'metformin': {
            'covered': True,
            'tier': 1,
            'coverage_percentage': 90,
            'copay': 5,
            'prior_authorization': False
        },
        'atorvastatin': {
            'covered': True,
            'tier': 1,
            'coverage_percentage': 90,
            'copay': 5,
            'prior_authorization': False
        },
        
        # Brand medications
        'lipitor': {
            'covered': True,
            'tier': 2,
            'coverage_percentage': 75,
            'copay': 30,
            'prior_authorization': False
        },
        'zestril': {
            'covered': True,
            'tier': 2,
            'coverage_percentage': 75,
            'copay': 30,
            'prior_authorization': False
        },
        'glucophage': {
            'covered': True,
            'tier': 2,
            'coverage_percentage': 75,
            'copay': 30,
            'prior_authorization': False
        },
        
        # Higher tier medications
        'crestor': {
            'covered': True,
            'tier': 3,
            'coverage_percentage': 50,
            'copay': 60,
            'prior_authorization': True
        },
        'humira': {
            'covered': True,
            'tier': 4,
            'coverage_percentage': 25,
            'copay': 150,
            'prior_authorization': True
        }
    }
    
    return mock_coverage
