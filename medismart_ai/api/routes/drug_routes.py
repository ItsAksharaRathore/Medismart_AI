
# api/routes/drug_routes.py
from flask import Blueprint, request, jsonify
from core.drug.knowledge_graph import DrugKnowledgeGraph
from core.drug.interaction_checker import check_interactions
from core.recommendation.cost_optimizer import optimize_cost
from utils.validators import validate_drug_request

drug_bp = Blueprint('drug', __name__)
drug_knowledge_graph = DrugKnowledgeGraph()

@drug_bp.route('/search', methods=['GET'])
def search_drugs():
    """Search for drugs by name or properties"""
    query = request.args.get('query', '')
    limit = int(request.args.get('limit', 10))
    
    if not query:
        return jsonify({"error": "Query parameter is required"}), 400
        
    try:
        results = drug_knowledge_graph.search_drugs(query, limit)
        return jsonify(results), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@drug_bp.route('/interactions', methods=['POST'])
def drug_interactions():
    """Check interactions between drugs"""
    if not validate_drug_request(request):
        return jsonify({"error": "Invalid request"}), 400
        
    try:
        medications = request.json.get('medications', [])
        interactions = check_interactions(medications)
        
        return jsonify(interactions), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@drug_bp.route('/alternatives', methods=['POST'])
def drug_alternatives():
    """Find alternative medications with cost optimization"""
    if not validate_drug_request(request):
        return jsonify({"error": "Invalid request"}), 400
        
    try:
        medication = request.json.get('medication', '')
        insurance = request.json.get('insurance', None)
        
        alternatives = drug_knowledge_graph.find_alternatives(medication)
        
        if insurance:
            optimized_alternatives = optimize_cost(alternatives, insurance)
        else:
            optimized_alternatives = optimize_cost(alternatives)
            
        return jsonify(optimized_alternatives), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
