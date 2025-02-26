
# core/drug/interaction_checker.py
from data.neo4j.graph_manager import Neo4jGraphManager
from ml.recommendation.interaction_predictor import predict_interactions
from utils.logger import get_logger

logger = get_logger(__name__)

def check_interactions(medications):
    """
    Check for interactions between a list of medications
    
    Args:
        medications: List of medication names
        
    Returns:
        List of interaction details with severity and recommendations
    """
    try:
        # Initialize graph manager
        graph_manager = Neo4jGraphManager()
        
        # Get known interactions from knowledge graph
        known_interactions = _get_known_interactions(graph_manager, medications)
        
        # Predict potential interactions using ML
        predicted_interactions = predict_interactions(medications)
        
        # Merge and deduplicate interactions
        all_interactions = _merge_interactions(known_interactions, predicted_interactions)
        
        # Sort by severity
        severity_map = {'High': 3, 'Moderate': 2, 'Low': 1, 'Unknown': 0}
        all_interactions.sort(
            key=lambda x: severity_map.get(x.get('severity', 'Unknown'), 0),
            reverse=True
        )
        
        return all_interactions
        
    except Exception as e:
        logger.error(f"Interaction check error: {str(e)}")
        raise

def _get_known_interactions(graph_manager, medications):
    """Get known interactions from the knowledge graph"""
    # Cypher query to find interactions
    cypher_query = """
    MATCH (d1:Drug)-[i:INTERACTS_WITH]->(d2:Drug)
    WHERE d1.name IN $medications AND d2.name IN $medications
    RETURN d1.name as drug1, d2.name as drug2,
           i.severity as severity, i.description as description,
           i.effect as effect, i.recommendation as recommendation,
           i.evidence_level as evidence_level, 'known' as source
    """
    
    # Execute query
    return graph_manager.execute_query(cypher_query, {"medications": medications})

def _merge_interactions(known, predicted):
    """Merge and deduplicate interactions from different sources"""
    # Create lookup dictionary for known interactions
    interaction_lookup = {}
    for interaction in known:
        pair = tuple(sorted([interaction['drug1'], interaction['drug2']]))
        interaction_lookup[pair] = interaction
    
    # Add predicted interactions if they don't exist in known
    for interaction in predicted:
        pair = tuple(sorted([interaction['drug1'], interaction['drug2']]))
        if pair not in interaction_lookup:
            interaction_lookup[pair] = interaction
        else:
            # If known has higher evidence, keep it; otherwise blend information
            known_evidence = interaction_lookup[pair].get('evidence_level', 'unknown')
            predicted_evidence = interaction.get('evidence_level', 'predicted')
            
            if known_evidence == 'unknown' and predicted_evidence != 'unknown':
                # Update with predicted information
                interaction_lookup[pair] = interaction
    
    return list(interaction_lookup.values())