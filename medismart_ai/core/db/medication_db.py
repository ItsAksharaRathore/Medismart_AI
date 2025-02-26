# db/medication_db.py
import sqlite3
import os
import json
from utils.logger import get_logger

logger = get_logger(__name__)

# Path to the medication database
DB_PATH = os.path.join(os.path.dirname(__file__), '../data/medications.db')

def get_medication_details(medication_name):
    """
    Retrieve detailed information about a medication
    
    Args:
        medication_name: Name of the medication
        
    Returns:
        Dictionary with medication details
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Search for medication with exact name or similar names
        query = """
        SELECT id, name, generic_name, brand_names, classification, form, 
               strength, indications, contraindications, side_effects, 
               warnings, interactions, storage, price_range, description
        FROM medications 
        WHERE name = ? OR name LIKE ? OR generic_name = ? OR generic_name LIKE ?
        LIMIT 1
        """
        
        search_term = f"%{medication_name}%"
        cursor.execute(query, (medication_name, search_term, medication_name, search_term))
        
        result = cursor.fetchone()
        
        if result:
            med_details = {
                'id': result[0],
                'name': result[1],
                'generic_name': result[2],
                'brand_names': json.loads(result[3]) if result[3] else [],
                'classification': result[4],
                'form': result[5],
                'strength': result[6],
                'indications': json.loads(result[7]) if result[7] else [],
                'contraindications': json.loads(result[8]) if result[8] else [],
                'side_effects': json.loads(result[9]) if result[9] else [],
                'warnings': json.loads(result[10]) if result[10] else [],
                'interactions': json.loads(result[11]) if result[11] else [],
                'storage': result[12],
                'price_range': result[13],
                'description': result[14]
            }
            return med_details
        else:
            # Return limited details if medication not found in database
            return {
                'name': medication_name,
                'generic_name': None,
                'brand_names': [],
                'classification': None,
                'form': None,
                'indications': [],
                'side_effects': [],
                'warnings': [],
                'interactions': [],
                'description': None
            }
            
    except Exception as e:
        logger.error(f"Error retrieving medication details: {str(e)}")
        return {
            'name': medication_name,
            'generic_name': None,
            'brand_names': [],
            'classification': None
        }
    finally:
        if 'conn' in locals():
            conn.close()

def find_alternative_medications(medication_name, strength=None, form=None):
    """
    Find alternative medications for a given medication
    
    Args:
        medication_name: Name of the medication
        strength: Strength of the medication
        form: Form of the medication (tablet, capsule, etc.)
        
    Returns:
        List of alternative medications
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # First, get the medication's details
        med_details = get_medication_details(medication_name)
        
        if not med_details.get('classification'):
            # If medication not found in database, return empty list
            return []
        
        # Find alternatives in the same classification
        query = """
        SELECT id, name, generic_name, brand_names, form, strength, price_range
        FROM medications 
        WHERE classification = ? AND name != ? AND generic_name != ?
        LIMIT 5
        """
        
        cursor.execute(query, (med_details['classification'], medication_name, 
                              med_details.get('generic_name', '')))
        
        results = cursor.fetchall()
        
        alternatives = []
        for result in results:
            alt = {
                'id': result[0],
                'name': result[1],
                'generic_name': result[2],
                'brand_names': json.loads(result[3]) if result[3] else [],
                'form': result[4],
                'strength': result[5],
                'price_range': result[6]
            }
            alternatives.append(alt)
            
        return alternatives
        
    except Exception as e:
        logger.error(f"Error finding alternative medications: {str(e)}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def search_medications(query, limit=10):
    """
    Search for medications by name, generic name, or brand names
    
    Args:
        query: Search query
        limit: Maximum number of results to return
        
    Returns:
        List of medication dictionaries
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        search_term = f"%{query}%"
        sql_query = """
        SELECT id, name, generic_name, brand_names, classification, form, strength
        FROM medications 
        WHERE name LIKE ? OR generic_name LIKE ?
        LIMIT ?
        """
        
        cursor.execute(sql_query, (search_term, search_term, limit))
        results = cursor.fetchall()
        
        medications = []
        for result in results:
            med = {
                'id': result[0],
                'name': result[1],
                'generic_name': result[2],
                'brand_names': json.loads(result[3]) if result[3] else [],
                'classification': result[4],
                'form': result[5],
                'strength': result[6]
            }
            medications.append(med)
            
        return medications
        
    except Exception as e:
        logger.error(f"Error searching medications: {str(e)}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def add_medication(name, generic_name=None, brand_names=None, classification=None, 
                  form=None, strength=None, indications=None, contraindications=None, 
                  side_effects=None, warnings=None, interactions=None, storage=None, 
                  price_range=None, description=None):
    """
    Add a new medication to the database
    
    Args:
        name: Name of the medication
        generic_name: Generic name of the medication
        brand_names: List of brand names
        classification: Classification of the medication
        form: Form of the medication (tablet, capsule, etc.)
        strength: Strength of the medication
        indications: List of indications
        contraindications: List of contraindications
        side_effects: List of side effects
        warnings: List of warnings
        interactions: List of interactions
        storage: Storage instructions
        price_range: Price range of the medication
        description: Description of the medication
        
    Returns:
        ID of the newly added medication or None if failed
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Convert lists to JSON
        brand_names_json = json.dumps(brand_names or [])
        indications_json = json.dumps(indications or [])
        contraindications_json = json.dumps(contraindications or [])
        side_effects_json = json.dumps(side_effects or [])
        warnings_json = json.dumps(warnings or [])
        interactions_json = json.dumps(interactions or [])
        
        # Create medications table if it doesn't exist
        create_medication_table()
        
        # Insert the medication
        query = """
        INSERT INTO medications 
        (name, generic_name, brand_names, classification, form, strength, 
         indications, contraindications, side_effects, warnings, 
         interactions, storage, price_range, description) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        cursor.execute(query, (
            name, generic_name, brand_names_json, classification, 
            form, strength, indications_json, contraindications_json, 
            side_effects_json, warnings_json, interactions_json, 
            storage, price_range, description
        ))
        
        conn.commit()
        return cursor.lastrowid
        
    except Exception as e:
        logger.error(f"Error adding medication: {str(e)}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def create_medication_table():
    """
    Create the medications table if it doesn't exist
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
        # Create the medications table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS medications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            generic_name TEXT,
            brand_names TEXT,
            classification TEXT,
            form TEXT,
            strength TEXT,
            indications TEXT,
            contraindications TEXT,
            side_effects TEXT,
            warnings TEXT,
            interactions TEXT,
            storage TEXT,
            price_range TEXT,
            description TEXT
        )
        ''')
        
        conn.commit()
        logger.info("Medications table created successfully")
        
    except Exception as e:
        logger.error(f"Error creating medications table: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

# Initialize the database when module is imported
create_medication_table()