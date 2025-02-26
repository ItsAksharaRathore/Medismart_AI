
# data/external/who_client.py
import requests
import json
from utils.logger import get_logger
import time

logger = get_logger(__name__)

class WHOClient:
    """Client for World Health Organization APIs"""
    
    def __init__(self, api_key=None, base_url="https://api.who.int"):
        """
        Initialize WHO client
        
        Args:
            api_key: WHO API key (if required)
            base_url: WHO API base URL
        """
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        
        # Initialize headers
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        
        # Add API key to headers if available
        if self.api_key:
            self.session.headers.update({"X-API-Key": self.api_key})
            
        logger.info("WHO client initialized")
        
    def _make_request(self, method, endpoint, params=None, data=None, retries=3, backoff=1):
        """
        Make HTTP request to WHO API with retry logic
        
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
        url = f"{self.base_url}/{endpoint}"
        attempt = 0
        
        while attempt < retries:
            try:
                # Make request
                if method == "GET":
                    response = self.session.get(url, params=params, timeout=10)
                elif method == "POST":
                    response = self.session.post(url, json=data, params=params, timeout=10)
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
                    logger.warning(f"Request to WHO API failed ({e}). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to connect to WHO API after {retries} attempts: {e}")
                    raise
                    
        # This should never be reached due to the raise above
        return None
        
    def get_essential_medicines(self, query=None, category=None):
        """
        Get information from WHO Essential Medicines List
        
        Args:
            query: Search query for medicine name
            category: Medicine category filter
            
        Returns:
            list: Matching medicines
        """
        try:
            params = {}
            
            if query:
                params["q"] = query
                
            if category:
                params["category"] = category
                
            # Note: This is a placeholder implementation as WHO doesn't provide
            # a direct API for essential medicines list
            response = self._make_request("GET", "essentialmedicines", params=params)
            
            return response.get("results", [])
            
        except Exception as e:
            logger.error(f"Error retrieving WHO essential medicines data: {str(e)}")
            return []
            
    def get_atc_classification(self, drug_name):
        """
        Get ATC (Anatomical Therapeutic Chemical) classification for a drug
        
        Args:
            drug_name: Name of the drug
            
        Returns:
            dict: ATC classification information
        """
        try:
            params = {"drug": drug_name}
            
            # Note: This is a placeholder implementation as WHO doesn't provide
            # a direct API for ATC classification
            response = self._make_request("GET", "atc", params=params)
            
            if "results" in response and len(response["results"]) > 0:
                return response["results"][0]
            else:
                logger.warning(f"No ATC classification found for: {drug_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving WHO ATC classification for {drug_name}: {str(e)}")
            return None
            
    def get_disease_information(self, disease_name):
        """
        Get information about a disease from WHO
        
        Args:
            disease_name: Name of the disease
            
        Returns:
            dict: Disease information
        """
        try:
            params = {"name": disease_name}
            
            # Note: This is a placeholder implementation as WHO doesn't provide
            # a unified disease information API
            response = self._make_request("GET", "diseases", params=params)
            
            if "results" in response and len(response["results"]) > 0:
                return response["results"][0]
            else:
                logger.warning(f"No WHO information found for disease: {disease_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving WHO disease information for {disease_name}: {str(e)}")
            return None
            
    def get_treatment_guidelines(self, condition):
        """
        Get WHO treatment guidelines for a specific condition
        
        Args:
            condition: Medical condition or disease
            
        Returns:
            list: Treatment guidelines
        """
        try:
            params = {"condition": condition}
            
            # Note: This is a placeholder implementation as WHO doesn't provide
            # a direct API for treatment guidelines
            response = self._make_request("GET", "guidelines", params=params)
            
            return response.get("guidelines", [])
            
        except Exception as e:
            logger.error(f"Error retrieving WHO treatment guidelines for {condition}: {str(e)}")
            return []
