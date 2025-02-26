# db/interaction_checker.py
import sqlite3
import os
import itertools
from utils.logger import get_logger

logger = get_logger(__name__)

# Path to the drug interactions database
DB_PATH = os.path.join(os.path.dirname(__file__), '../data/medications.db')

def check_drug_interactions(medications):
    """
    Check for interactions between medications
    
    Args:
        medications: List of medication names
        
    Returns:
        List of interaction dictionaries
    """
    try:
        if len(medications) < 2:
            return []
            
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS drug_interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drug1 TEXT NOT NULL,
            drug2 TEXT NOT NULL,
            severity TEXT,
            description TEXT,
            recommendation TEXT,
            UNIQUE(drug1, drug2)
        )
        ''')
        conn.commit()
        
        # Generate all possible drug pairs
        drug_pairs = list(itertools.combinations(medications, 2))
        
        interactions = []
        for drug1, drug2 in drug_pairs:
            # Check for interactions in both directions
            query = """
            SELECT id, severity, description, recommendation
            FROM drug_interactions 
            WHERE (drug1 = ? AND drug2 = ?) OR (drug1 = ? AND drug2 = ?)
            """
            
            cursor.execute(query, (drug1, drug2, drug2, drug1))
            result = cursor.fetchone()
            
            if result:
                interaction = {
                    'id': result[0],
                    'drugs': [drug1, drug2],
                    'severity': result[1],
                    'description': result[2],
                    'recommendation': result[3]
                }
                interactions.append(interaction)
                
        return interactions
        
    except Exception as e:
        logger.error(f"Error checking drug interactions: {str(e)}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def add_drug_interaction(drug1, drug2, severity, description, recommendation):
    """
    Add a new drug interaction to the database
    
    Args:
        drug1: First drug name
        drug2: Second drug name
        severity: Severity of the interaction
        description: Description of the interaction
        recommendation: Recommendation for handling the interaction
        
    Returns:
        Boolean indicating success
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS drug_interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drug1 TEXT NOT NULL,
            drug2 TEXT NOT NULL,
            severity TEXT,
            description TEXT,
            recommendation TEXT,
            UNIQUE(drug1, drug2)
        )
        ''')
        
        # Insert or replace the interaction
        query = """
        INSERT OR REPLACE INTO drug_interactions 
        (drug1, drug2, severity, description, recommendation) 
        VALUES (?, ?, ?, ?, ?)
        """
        
        cursor.execute(query, (drug1, drug2, severity, description, recommendation))
        conn.commit()
        
        return True
        
    except Exception as e:
        logger.error(f"Error adding drug interaction: {str(e)}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def get_all_interactions():
    """
    Retrieve all drug interactions from the database
    
    Returns:
        List of interaction dictionaries
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        query = """
        SELECT id, drug1, drug2, severity, description, recommendation
        FROM drug_interactions
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        interactions = []
        for result in results:
            interaction = {
                'id': result[0],
                'drugs': [result[1], result[2]],
                'severity': result[3],
                'description': result[4],
                'recommendation': result[5]
            }
            interactions.append(interaction)
            
        return interactions
        
    except Exception as e:
        logger.error(f"Error retrieving drug interactions: {str(e)}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()