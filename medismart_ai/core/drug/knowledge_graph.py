
# core/drug/knowledge_graph.py
from data.neo4j.graph_manager import Neo4jGraphManager
from utils.logger import get_logger

logger = get_logger(__name__)

class DrugKnowledgeGraph:
    """Manages drug knowledge and relationships using Neo4j graph database"""
    
    def __init__(self):
        """Initialize the drug knowledge graph"""
        self.graph_manager = Neo4jGraphManager()
        self.logger = get_logger(__name__)
    
    def search_drugs(self, query, limit=10):
        """
        Search for drugs by name or properties
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            List of matching drugs with properties
        """
        try:
            # Create fuzzy search query for Neo4j
            cypher_query = """
            MATCH (d:Drug)
            WHERE d.name =~ $query OR d.generic_name =~ $query OR ANY(a IN d.aliases WHERE a =~ $query)
            RETURN d.name as name, d.generic_name as generic_name, 
                   d.drug_class as drug_class, d.strength as strength, 
                   d.form as form, d.manufacturer as manufacturer
            LIMIT $limit
            """
            
            # Make the query case-insensitive
            fuzzy_query = f"(?i).*{query}.*"
            
            # Execute query
            results = self.graph_manager.execute_query(
                cypher_query, 
                {"query": fuzzy_query, "limit": limit}
            )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Drug search error: {str(e)}")
            raise
    
    def find_alternatives(self, medication, criteria=None):
        """
        Find alternative medications for a given drug
        
        Args:
            medication: Name of the medication
            criteria: Dictionary of criteria for alternatives
                     (e.g., {'generic_only': True, 'same_class': True})
            
        Returns:
            List of alternative medications with properties
        """
        try:
            # Default criteria if none provided
            if criteria is None:
                criteria = {
                    'same_class': True,
                    'include_generic': True,
                    'include_brand': True
                }
            
            # Base Cypher query
            cypher_query = """
            MATCH (d:Drug {name: $medication})
            """
            
            # Add criteria
            if criteria.get('same_class', False):
                cypher_query += """
                MATCH (d)-[:HAS_CLASS]->(c:DrugClass)<-[:HAS_CLASS]-(alt:Drug)
                WHERE d <> alt
                """
            else:
                cypher_query += """
                MATCH (d)-[:HAS_INDICATION]->(i:Indication)<-[:HAS_INDICATION]-(alt:Drug)
                WHERE d <> alt
                """
            
            # Filter by generic/brand
            if criteria.get('include_generic', True) and not criteria.get('include_brand', True):
                cypher_query += " AND alt.is_generic = true"
            elif not criteria.get('include_generic', True) and criteria.get('include_brand', True):
                cypher_query += " AND alt.is_generic = false"
            
            # Return results
            cypher_query += """
            RETURN alt.name as name, alt.generic_name as generic_name,
                   alt.drug_class as drug_class, alt.strength as strength,
                   alt.form as form, alt.manufacturer as manufacturer,
                   alt.average_price as price, alt.is_generic as is_generic
            ORDER BY alt.is_generic DESC, alt.average_price ASC
            LIMIT 10
            """
            
            # Execute query
            results = self.graph_manager.execute_query(
                cypher_query, 
                {"medication": medication}
            )
            
            # Add similarity scores
            for result in results:
                result['similarity_score'] = self._calculate_similarity(
                    medication, result['name']
                )
            
            # Sort by similarity
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Find alternatives error: {str(e)}")
            raise
    
    def get_drug_interactions(self, medications):
        """
        Get interactions between a list of medications
        
        Args:
            medications: List of medication names
            
        Returns:
            List of interaction details between medications
        """
        try:
            # Cypher query to find interactions
            cypher_query = """
            MATCH (d1:Drug)-[i:INTERACTS_WITH]->(d2:Drug)
            WHERE d1.name IN $medications AND d2.name IN $medications
            RETURN d1.name as drug1, d2.name as drug2,
                   i.severity as severity, i.description as description,
                   i.effect as effect, i.recommendation as recommendation
            """
            
            # Execute query
            results = self.graph_manager.execute_query(
                cypher_query, 
                {"medications": medications}
            )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Drug interaction check error: {str(e)}")
            raise
    
    def get_drug_properties(self, medication):
        """
        Get detailed properties of a medication
        
        Args:
            medication: Name of the medication
            
        Returns:
            Dictionary of drug properties
        """
        try:
            # Cypher query to get drug properties
            cypher_query = """
            MATCH (d:Drug {name: $medication})
            OPTIONAL MATCH (d)-[:HAS_CLASS]->(c:DrugClass)
            OPTIONAL MATCH (d)-[:HAS_INDICATION]->(i:Indication)
            OPTIONAL MATCH (d)-[:HAS_SIDE_EFFECT]->(s:SideEffect)
            RETURN d.name as name, d.generic_name as generic_name,
                   d.strength as strength, d.form as form,
                   d.manufacturer as manufacturer, d.average_price as price,
                   d.is_generic as is_generic, collect(DISTINCT c.name) as drug_classes,
                   collect(DISTINCT i.name) as indications,
                   collect(DISTINCT s.name) as side_effects
            """
            
            # Execute query
            results = self.graph_manager.execute_query(
                cypher_query, 
                {"medication": medication}
            )
            
            if results:
                return results[0]
            return None
            
        except Exception as e:
            self.logger.error(f"Get drug properties error: {str(e)}")
            raise
    
    def _calculate_similarity(self, drug1, drug2):
        """
        Calculate similarity score between two drugs
        
        Args:
            drug1: Name of first drug
            drug2: Name of second drug
            
        Returns:
            Similarity score between 0 and 1
        """
        try:

            cypher_query = """
            MATCH (d1:Drug {name: $drug1}), (d2:Drug {name: $drug2})
            
            // Calculate class similarity
            OPTIONAL MATCH (d1)-[:HAS_CLASS]->(c1:DrugClass)
            OPTIONAL MATCH (d2)-[:HAS_CLASS]->(c2:DrugClass)
            WITH d1, d2, count(DISTINCT c1) as c1Count, 
                 count(DISTINCT c2) as c2Count,
                 count(DISTINCT c1) + count(DISTINCT c2) as totalClasses,
                 count(DISTINCT c1) - size(apoc.coll.subtract(
                     collect(DISTINCT c1.name), collect(DISTINCT c2.name)
                 )) as sharedClasses
                 
            // Calculate indication similarity
            OPTIONAL MATCH (d1)-[:HAS_INDICATION]->(i1:Indication)
            OPTIONAL MATCH (d2)-[:HAS_INDICATION]->(i2:Indication)
            WITH d1, d2, sharedClasses, totalClasses,
                 count(DISTINCT i1) as i1Count, 
                 count(DISTINCT i2) as i2Count,
                 count(DISTINCT i1) + count(DISTINCT i2) as totalIndications,
                 count(DISTINCT i1) - size(apoc.coll.subtract(
                     collect(DISTINCT i1.name), collect(DISTINCT i2.name)
                 )) as sharedIndications
            
            // Calculate overall similarity score
            WITH d1, d2, 
                 CASE WHEN totalClasses > 0 
                      THEN 1.0 * sharedClasses / totalClasses 
                      ELSE 0 END as classSimilarity,
                 CASE WHEN totalIndications > 0 
                      THEN 1.0 * sharedIndications / totalIndications 
                      ELSE 0 END as indicationSimilarity
            
            // Weighted similarity score (more weight on class similarity)
            RETURN (classSimilarity * 0.6 + indicationSimilarity * 0.4) as similarity
            """
            
            # Execute query
            results = self.graph_manager.execute_query(
                cypher_query, 
                {"drug1": drug1, "drug2": drug2}
            )
            
            if results and 'similarity' in results[0]:
                return results[0]['similarity']
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Calculate similarity error: {str(e)}")
            # Fall back to simple name-based similarity
            return self._fallback_similarity(drug1, drug2)
    
    def _fallback_similarity(self, drug1, drug2):
        """Simple fallback similarity calculation based on string similarity"""
        # Convert to lowercase
        drug1 = drug1.lower()
        drug2 = drug2.lower()
        
        # Calculate Jaccard similarity of character bigrams
        def get_bigrams(s):
            return set(s[i:i+2] for i in range(len(s)-1))
            
        bigrams1 = get_bigrams(drug1)
        bigrams2 = get_bigrams(drug2)
        
        intersection = len(bigrams1.intersection(bigrams2))
        union = len(bigrams1.union(bigrams2))
        
        if union == 0:
            return 0.0
            
        return intersection / union





# === Machine Learning Models ===


