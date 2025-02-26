
# data/external/nih_client.py
import requests
import json
from utils.logger import get_logger
import time

logger = get_logger(__name__)

class NIHClient:
    """Client for National Institutes of Health (NIH) APIs"""
    
    def __init__(self, api_key=None, base_url="https://api.nih.gov"):
        """
        Initialize NIH client
        
        Args:
            api_key: NIH API key (if required)
            base_url: NIH API base URL
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
            
        logger.info("NIH client initialized")
        
    def _make_request(self, method, endpoint, params=None, data=None, retries=3, backoff=1):
        """
        Make HTTP request to NIH API with retry logic
        
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
                    logger.warning(f"Request to NIH API failed ({e}). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to connect to NIH API after {retries} attempts: {e}")
                    raise
                    
        # This should never be reached due to the raise above
        return None
        
    def search_clinical_trials(self, condition=None, drug=None, location=None, status="recruiting", limit=10):
        """
        Search for clinical trials in ClinicalTrials.gov
        
        Args:
            condition: Medical condition
            drug: Drug or intervention
            location: Geographic location
            status: Trial status (e.g., recruiting, completed)
            limit: Maximum number of results
            
        Returns:
            list: Clinical trials matching criteria
        """
        try:
            params = {"limit": limit, "status": status}
            
            if condition:
                params["condition"] = condition
                
            if drug:
                params["intervention"] = drug
                
            if location:
                params["location"] = location
                
            # Note: This is a placeholder implementation for NIH's ClinicalTrials.gov API
            response = self._make_request("GET", "clinicaltrials", params=params)
            
            return response.get("studies", [])
            
        except Exception as e:
            logger.error(f"Error searching clinical trials: {str(e)}")
            return []
            
    def get_drug_interactions(self, drug_name):
        """
        Get drug interactions from NIH resources (like DrugBank)
        
        Args:
            drug_name: Name of the drug
            
        Returns:
            list: Drug interactions
        """
        try:
            params = {"name": drug_name}
            
            # Note: This is a placeholder implementation as NIH doesn't provide
            # a direct unified API for drug interactions
            response = self._make_request("GET", "druginteractions", params=params)
            
            return response.get("interactions", [])
            
        except Exception as e:
            logger.error(f"Error retrieving drug interactions for {drug_name}: {str(e)}")
            return []
            
    def get_medication_information(self, medication_name):
        """
        Get detailed information about a medication from NIH resources
        
        Args:
            medication_name: Name of the medication
            
        Returns:
            dict: Medication information
        """
        try:
            params = {"name": medication_name}
            
            # Note: This is a placeholder implementation for NIH's drug information
            response = self._make_request("GET", "druginfo", params=params)
            
            if "results" in response and len(response["results"]) > 0:
                return response["results"][0]
            else:
                logger.warning(f"No NIH information found for medication: {medication_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving NIH information for medication {medication_name}: {str(e)}")
            return None
            
    def search_pubmed(self, query, max_results=10):
        """
        Search for medical literature in PubMed
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            list: PubMed articles matching the query
        """
        try:
            params = {
                "term": query,
                "retmax": max_results
            }
            
            # Note: This is a simplified implementation for the PubMed API
            response = self._make_request("GET", "pubmed", params=params)
            
            return response.get("articles", [])
            
        except Exception as e:
            logger.error(f"Error searching PubMed for '{query}': {str(e)}")
            return []
            
    def get_disease_information(self, disease_name):
        """
        Get information about a disease from NIH resources
        
        Args:
            disease_name: Name of the disease
            
        Returns:
            dict: Disease information
        """
        try:
            params = {"name": disease_name}
            
            # Note: This is a placeholder implementation for disease information
            response = self._make_request("GET", "diseaseinfo", params=params)
            
            if "results" in response and len(response["results"]) > 0:
                return response["results"][0]
            else:
                logger.warning(f"No NIH information found for disease: {disease_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving NIH disease information for {disease_name}: {str(e)}")
            return None
