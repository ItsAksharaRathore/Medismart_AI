# core/drug/alternatives.py
from core.drug.knowledge_graph import DrugKnowledgeGraph
from data.external.fda_client import FDAClient
from data.external.who_client import WHOClient
from utils.logger import get_logger

logger = get_logger(__name__)

def find_alternatives(medications, criteria=None):
    """
    Find alternative medications for a list of prescribed medications
    
    Args:
        medications: List of medication dictionaries with name and properties
        criteria: Dictionary of criteria for alternatives
                 (e.g., {'generic_only': True, 'same_class': True})
    
    Returns:
        Dictionary mapping each medication to a list of alternatives
    """
    try:
        # Initialize knowledge graph and external clients
        drug_graph = DrugKnowledgeGraph()
        fda_client = FDAClient()
        who_client = WHOClient()
        
        # Default criteria if none provided
        if criteria is None:
            criteria = {
                'same_class': True,
                'include_generic': True,
                'include_brand': True
            }
        
        # Find alternatives for each medication
        alternatives_map = {}
        
        for med in medications:
            # Get medication name
            if isinstance(med, dict) and 'name' in med:
                med_name = med['name']
            else:
                med_name = med
            
            # Get alternatives from knowledge graph
            kg_alternatives = drug_graph.find_alternatives(med_name, criteria)
            
            # Get alternatives from FDA database
            fda_alternatives = fda_client.get_therapeutic_alternatives(med_name)
            
            # Get alternatives from WHO essential medicines
            who_alternatives = who_client.get_alternatives(med_name)
            
            # Merge and deduplicate alternatives
            all_alternatives = _merge_alternatives(
                kg_alternatives, 
                fda_alternatives, 
                who_alternatives
            )
            
            # Store in map
            alternatives_map[med_name] = all_alternatives
        
        return alternatives_map
        
    except Exception as e:
        logger.error(f"Find alternatives error: {str(e)}")
        raise

def _merge_alternatives(kg_alternatives, fda_alternatives, who_alternatives):
    """Merge and deduplicate alternatives from different sources"""
    # Use a dictionary to deduplicate by name
    alternatives_dict = {}
    
    # Process knowledge graph alternatives
    for alt in kg_alternatives:
        alternatives_dict[alt['name']] = {
            'name': alt['name'],
            'generic_name': alt.get('generic_name'),
            'drug_class': alt.get('drug_class'),
            'strength': alt.get('strength'),
            'form': alt.get('form'),
            'manufacturer': alt.get('manufacturer'),
            'price': alt.get('price'),
            'is_generic': alt.get('is_generic', False),
            'similarity_score': alt.get('similarity_score', 0.0),
            'sources': ['knowledge_graph']
        }
    
    # Process FDA alternatives
    for alt in fda_alternatives:
        name = alt['name']
        if name in alternatives_dict:
            # Update existing entry
            alternatives_dict[name]['sources'].append('fda')
            # Update any missing information
            for key, value in alt.items():
                if key != 'name' and key != 'sources':
                    if key not in alternatives_dict[name] or not alternatives_dict[name][key]:
                        alternatives_dict[name][key] = value
        else:
            # Add new entry
            alt['sources'] = ['fda']
            alternatives_dict[name] = alt
    
    # Process WHO alternatives
    for alt in who_alternatives:
        name = alt['name']
        if name in alternatives_dict:
            # Update existing entry
            alternatives_dict[name]['sources'].append('who')
            alternatives_dict[name]['is_essential'] = True
            # Update any missing information
            for key, value in alt.items():
                if key != 'name' and key != 'sources':
                    if key not in alternatives_dict[name] or not alternatives_dict[name][key]:
                        alternatives_dict[name][key] = value
        else:
            # Add new entry
            alt['sources'] = ['who']
            alt['is_essential'] = True
            alternatives_dict[name] = alt
    
    # Convert back to list and sort by similarity score
    alternatives_list = list(alternatives_dict.values())
    alternatives_list.sort(key=lambda x: x.get('similarity_score', 0.0), reverse=True)
    
    return alternatives_list