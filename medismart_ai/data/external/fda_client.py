
# data/external/fda_client.py
import requests
import json
from utils.logger import get_logger
import time

logger = get_logger(__name__)

class FDAClient:
    """Client for FDA's OpenFDA API"""
    
    def __init__(self, api_key=None, base_url="https://api.fda.gov"):
        """
        Initialize FDA client
        
        Args:
            api_key: FDA API key (optional)
            base_url: FDA API base URL
        """
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        # Initialize headers
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        
        logger.info("FDA client initialized")
        
    def _construct_url(self, endpoint, params=None):
        """
        Construct request URL with parameters
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            str: Complete URL
        """
        url = f"{self.base_url}/{endpoint}"
        
        if params is None:
            params = {}
            
        # Add API key if available
        if self.api_key:
            params["api_key"] = self.api_key
            
        # Convert params to query string
        if params:
            query_params = []
            for key, value in params.items():
                if isinstance(value, list):
                    for v in value:
                        query_params.append(f"{key}={v}")
                else:
                    query_params.append(f"{key}={value}")
            
            url += "?" + "&".join(query_params)
            
        return url
        
    def _make_request(self, method, endpoint, params=None, data=None, retries=3, backoff=1):
        """
        Make HTTP request to FDA API with retry logic
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            data: Request body for POST/PUT
            retries: Number of retry attempts
            backoff: Backoff multiplier
            
        Returns:
            dict: API response
        """
        url = self._construct_url(endpoint, params)
        attempt = 0
        
        while attempt < retries:
            try:
                # Make request
                if method == "GET":
                    response = self.session.get(url, timeout=10)
                elif method == "POST":
                    response = self.session.post(url, json=data, timeout=10)
                else:
                    logger.error(f"Unsupported HTTP method: {method}")
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                # Check for success
                response.raise_for_status()
                
                return response.json()
                
            except requests.exceptions.RequestException as e:
                attempt += 1
                wait_time = backoff * (2 ** attempt)
                
                if attempt < retries:
                    logger.warning(f"Request to FDA API failed ({e}). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to connect to FDA API after {retries} attempts: {e}")
                    raise
                    
        # This should never be reached due to the raise above
        return None
        
    def get_drug_information(self, drug_name):
        """
        Get information about a drug from FDA
        
        Args:
            drug_name: Name of the drug
            
        Returns:
            dict: Drug information
        """
        try:
            params = {
                "search": f"generic_name:{drug_name}+brand_name:{drug_name}",
                "limit": 1
            }
            
            response = self._make_request(
                "GET", 
                "drug/label.json", 
                params=params
            )
            
            if "results" in response and len(response["results"]) > 0:
                return response["results"][0]
            else:
                logger.warning(f"No FDA information found for drug: {drug_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving FDA information for drug {drug_name}: {str(e)}")
            return None
            
    def get_drug_interactions(self, drug_name):
        """
        Get known drug interactions
        
        Args:
            drug_name: Name of the drug
            
        Returns:
            list: Known interactions
        """
        try:
            # This is a simplified implementation as FDA's API doesn't directly provide
            # drug interaction data in an easily accessible format
            drug_info = self.get_drug_information(drug_name)
            
            if drug_info and "drug_interactions" in drug_info:
                # Parse interaction text
                return self._parse_interaction_text(drug_info["drug_interactions"])
            else:
                logger.warning(f"No interaction information found for drug: {drug_name}")
                return []
                
        except Exception as e:
            logger.error(f"Error retrieving interaction information for drug {drug_name}: {str(e)}")
            return []
            
    def _parse_interaction_text(self, interaction_text):
        """
        Parse interaction text to structured format
        
        Args:
            interaction_text: Raw interaction text from FDA
            
        Returns:
            list: Structured interaction data
        """
        # This is a placeholder for a more sophisticated parsing logic
        # In a real system, this would use NLP or pattern matching
        
        interactions = []
        
        if isinstance(interaction_text, list):
            text = " ".join(interaction_text)
        else:
            text = str(interaction_text)
            
        # Simple pattern-based extraction (would be much more complex in practice)
        # Split by common separators
        lines = text.split("\n")
        if len(lines) == 1:
            lines = text.split(". ")
            
        for line in lines:
            if len(line.strip()) > 10:  # Minimum length to be considered meaningful
                interactions.append({
                    "description": line.strip(),
                    "severity": "unknown"  # Would need more sophisticated analysis
                })
                
        return interactions
        
    def get_adverse_events(self, drug_name, limit=10):
        """
        Get adverse events reported for a drug
        
        Args:
            drug_name: Name of the drug
            limit: Maximum number of events to return
            
        Returns:
            list: Adverse events
        """
        try:
            params = {
                "search": f"patient.drug.medicinalproduct:{drug_name}",
                "count": "patient.reaction.reactionmeddrapt.exact",
                "limit": limit
            }
            
            response = self._make_request(
                "GET", 
                "drug/event.json", 
                params=params
            )
            
            if "results" in response:
                return response["results"]
            else:
                logger.warning(f"No adverse events found for drug: {drug_name}")
                return []
                
        except Exception as e:
            logger.error(f"Error retrieving adverse events for drug {drug_name}: {str(e)}")
            return []
            
    def search_recalls(self, product_name=None, manufacturer=None, limit=10):
        """
        Search for drug recalls
        
        Args:
            product_name: Name of the product
            manufacturer: Name of the manufacturer
            limit: Maximum number of recalls to return
            
        Returns:
            list: Drug recalls
        """
        try:
            search_terms = []
            
            if product_name:
                search_terms.append(f"product_description:{product_name}")
                
            if manufacturer:
                search_terms.append(f"recalling_firm:{manufacturer}")
                
            search_query = "+".join(search_terms) if search_terms else None
            
            params = {
                "limit": limit
            }
            
            if search_query:
                params["search"] = search_query
                
            response = self._make_request(
                "GET", 
                "drug/enforcement.json", 
                params=params
            )
            
            if "results" in response:
                return response["results"]
            else:
                logger.warning(f"No recalls found for the specified criteria")
                return []
                
        except Exception as e:
            logger.error(f"Error searching drug recalls: {str(e)}")
            return []
