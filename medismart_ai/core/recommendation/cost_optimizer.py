# core/recommendation/cost_optimizer.py
from data.external.fda_client import FDAClient
from utils.logger import get_logger

logger = get_logger(__name__)

def optimize_cost(alternatives, insurance_provider=None):
    """
    Optimize medication alternatives based on cost and insurance coverage
    
    Args:
        alternatives: Dictionary mapping medications to their alternatives
        insurance_provider: Optional insurance provider name
        
    Returns:
        Optimized alternatives with cost information
    """
    try:
        # Initialize FDA client for pricing data
        fda_client = FDAClient()
        
        # If insurance provider is specified, get coverage information
        insurance_coverage = {}
        if insurance_provider:
            insurance_coverage = _get_insurance_coverage(insurance_provider)
        
        # Process each medication and its alternatives
        optimized_alternatives = {}
        
        for medication, alts in alternatives.items():
            # Get pricing data for alternatives
            for alt in alts:
                if 'price' not in alt or not alt['price']:
                    # Get price from FDA database if not available
                    price_info = fda_client.get_price_information(alt['name'])
                    if price_info:
                        alt['price'] = price_info.get('average_price')
                        alt['price_range'] = price_info.get('price_range')
                
                # Calculate insurance coverage if available
                if insurance_provider and alt['name'] in insurance_coverage:
                    coverage = insurance_coverage[alt['name']]
                    alt['coverage'] = coverage
                    
                    # Calculate out-of-pocket cost
                    if 'price' in alt and alt['price']:
                        alt['out_of_pocket'] = alt['price'] * (1 - coverage['coverage_percentage'] / 100.0)
                        if 'copay' in coverage:
                            alt['out_of_pocket'] = min(alt['out_of_pocket'], coverage['copay'])
            
            # Sort alternatives by cost (out-of-pocket if insurance, otherwise price)
            if insurance_provider:
                alts.sort(key=lambda x: x.get('out_of_pocket', float('inf')))
            else:
                alts.sort(key=lambda x: x.get('price', float('inf')))
            
            # Add to optimized results
            optimized_alternatives[medication] = alts
        
        return optimized_alternatives
        
    except Exception as e:
        logger.error(f"Cost optimization error: {str(e)}")
        raise

def _get_insurance_coverage(insurance_provider):
    """
    Get insurance coverage information for medications
    
    Args:
        insurance_provider: Name of the insurance provider
        
    Returns:
        Dictionary mapping medication names to coverage information
    """
    try:
        # This would typically call an external API or database
        # For now, we'll use a mock implementation
        
        # Mock coverage data (in a real system, this would come from an API)
        mock_coverage = {
            # Tier 1 - Generic drugs (highest coverage)
            'amoxicillin': {'tier': 1, 'coverage_percentage': 90, 'copay': 5},
            'lisinopril': {'tier': 1, 'coverage_percentage': 90, 'copay': 5},
            'metformin': {'tier': 1, 'coverage_percentage': 90, 'copay': 5},
            'atorvastatin': {'tier': 1, 'coverage_percentage': 90, 'copay': 5},
            
            # Tier 2 - Preferred brand drugs
            'Lipitor': {'tier': 2, 'coverage_percentage': 75, 'copay': 30},
            'Zestril': {'tier': 2, 'coverage_percentage': 75, 'copay': 30},
            'Glucophage': {'tier': 2, 'coverage_percentage': 75, 'copay': 30},
            
            # Tier 3 - Non-preferred brand drugs
            'Crestor': {'tier': 3, 'coverage_percentage': 50, 'copay': 60},
            'Prinivil': {'tier': 3, 'coverage_percentage': 50, 'copay': 60},
            
            # Tier 4 - Specialty drugs
            'Humira': {'tier': 4, 'coverage_percentage': 25, 'copay': 150},
            'Enbrel': {'tier': 4, 'coverage_percentage': 25, 'copay': 150}
        }
        
        # In a real system, we would filter by the specific insurance provider
        # For this mock, we'll just return all coverage data
        return mock_coverage
        
    except Exception as e:
        logger.error(f"Get insurance coverage error: {str(e)}")
        raise
