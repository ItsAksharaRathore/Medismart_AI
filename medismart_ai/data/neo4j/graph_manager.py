

# data/neo4j/graph_manager.py
from neo4j import GraphDatabase
from utils.logger import get_logger

logger = get_logger(__name__)

class GraphManager:
    """Neo4j graph database manager for the medical system"""
    
    def __init__(self, uri, username, password):
        """
        Initialize Neo4j graph manager
        
        Args:
            uri: Neo4j URI
            username: Neo4j username
            password: Neo4j password
        """
        try:
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
            # Verify connection by running a simple query
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS num")
                result.single()
            logger.info(f"Connected to Neo4j at {uri}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {str(e)}")
            raise
            
    def close(self):
        """Close the Neo4j driver"""
        try:
            self.driver.close()
            logger.info("Neo4j connection closed")
        except Exception as e:
            logger.error(f"Error closing Neo4j connection: {str(e)}")
            
    def add_patient(self, patient_id, patient_data):
        """
        Add a patient node to the graph
        
        Args:
            patient_id: Patient ID
            patient_data: Dictionary containing patient attributes
            
        Returns:
            bool: True if successful
        """
        try:
            with self.driver.session() as session:
                # Convert patient data to a map of properties
                props = {k: v for k, v in patient_data.items() 
                        if k not in ['prescription_ids'] and v is not None}
                props['patient_id'] = patient_id
                
                # Create patient node
                session.run(
                    """
                    MERGE (p:Patient {patient_id: $patient_id})
                    SET p += $props
                    """,
                    patient_id=patient_id,
                    props=props
                )
                
                logger.info(f"Added patient node for {patient_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error adding patient node {patient_id}: {str(e)}")
            raise
            
    def add_doctor(self, doctor_id, doctor_data):
        """
        Add a doctor node to the graph
        
        Args:
            doctor_id: Doctor ID
            doctor_data: Dictionary containing doctor attributes
            
        Returns:
            bool: True if successful
        """
        try:
            with self.driver.session() as session:
                # Convert doctor data to a map of properties
                props = {k: v for k, v in doctor_data.items() if v is not None}
                props['doctor_id'] = doctor_id
                
                # Create doctor node
                session.run(
                    """
                    MERGE (d:Doctor {doctor_id: $doctor_id})
                    SET d += $props
                    """,
                    doctor_id=doctor_id,
                    props=props
                )
                
                logger.info(f"Added doctor node for {doctor_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error adding doctor node {doctor_id}: {str(e)}")
            raise
            
    def add_medication(self, medication_id, medication_data):
        """
        Add a medication node to the graph
        
        Args:
            medication_id: Medication ID
            medication_data: Dictionary containing medication attributes
            
        Returns:
            bool: True if successful
        """
        try:
            with self.driver.session() as session:
                # Convert medication data to a map of properties
                props = {k: v for k, v in medication_data.items() if v is not None}
                props['medication_id'] = medication_id
                
                # Create medication node
                session.run(
                    """
                    MERGE (m:Medication {medication_id: $medication_id})
                    SET m += $props
                    """,
                    medication_id=medication_id,
                    props=props
                )
                
                # Add relationships for interactions if they exist
                if 'interactions' in medication_data and medication_data['interactions']:
                    for interaction in medication_data['interactions']:
                        session.run(
                            """
                            MATCH (m1:Medication {medication_id: $med1_id})
                            MATCH (m2:Medication {name: $med2_name})
                            MERGE (m1)-[r:INTERACTS_WITH]->(m2)
                            SET r.severity = $severity, r.description = $description
                            """,
                            med1_id=medication_id,
                            med2_name=interaction['medication'],
                            severity=interaction['severity'],
                            description=interaction['description']
                        )
                
                logger.info(f"Added medication node for {medication_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error adding medication node {medication_id}: {str(e)}")
            raise
            
    def add_prescription(self, prescription_id, prescription_data):
        """
        Add a prescription node and related relationships
        
        Args:
            prescription_id: Prescription ID
            prescription_data: Dictionary containing prescription details
            
        Returns:
            bool: True if successful
        """
        try:
            with self.driver.session() as session:
                # Basic prescription properties
                props = {
                    'prescription_id': prescription_id,
                    'created_at': prescription_data.get('created_at'),
                    'notes': prescription_data.get('notes'),
                    'status': prescription_data.get('status', 'active')
                }
                
                # Create prescription node
                session.run(
                    """
                    MERGE (p:Prescription {prescription_id: $prescription_id})
                    SET p += $props
                    """,
                    prescription_id=prescription_id,
                    props=props
                )
                
                # Create relationship to patient
                if 'patient_id' in prescription_data:
                    session.run(
                        """
                        MATCH (p:Prescription {prescription_id: $prescription_id})
                        MATCH (patient:Patient {patient_id: $patient_id})
                        MERGE (patient)-[r:HAS_PRESCRIPTION]->(p)
                        """,
                        prescription_id=prescription_id,
                        patient_id=prescription_data['patient_id']
                    )
                
                # Create relationship to doctor
                if 'doctor_id' in prescription_data:
                    session.run(
                        """
                        MATCH (p:Prescription {prescription_id: $prescription_id})
                        MATCH (doctor:Doctor {doctor_id: $doctor_id})
                        MERGE (doctor)-[r:PRESCRIBED]->(p)
                        """,
                        prescription_id=prescription_id,
                        doctor_id=prescription_data['doctor_id']
                    )
                
                # Create relationships to medications
                if 'medications' in prescription_data:
                    for med in prescription_data['medications']:
                        med_props = {
                            'dosage': med.get('dosage'),
                            'frequency': med.get('frequency'),
                            'duration': med.get('duration'),
                            'instructions': med.get('instructions')
                        }
                        
                        session.run(
                            """
                            MATCH (p:Prescription {prescription_id: $prescription_id})
                            MATCH (m:Medication {name: $medication_name})
                            MERGE (p)-[r:INCLUDES]->(m)
                            SET r += $props
                            """,
                            prescription_id=prescription_id,
                            medication_name=med['name'],
                            props=med_props
                        )
                
                logger.info(f"Added prescription node and relationships for {prescription_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error adding prescription node {prescription_id}: {str(e)}")
            raise
            
    def get_patient_medication_history(self, patient_id):
        """
        Get all medications a patient has been prescribed
        
        Args:
            patient_id: Patient ID
            
        Returns:
            list: List of medications with prescription details
        """
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (p:Patient {patient_id: $patient_id})-[:HAS_PRESCRIPTION]->(pr:Prescription)-[i:INCLUDES]->(m:Medication)
                    RETURN m.name as medication, 
                           collect({
                               prescription_id: pr.prescription_id, 
                               created_at: pr.created_at,
                               dosage: i.dosage,
                               frequency: i.frequency,
                               duration: i.duration,
                               instructions: i.instructions
                           }) as prescriptions
                    ORDER BY m.name
                    """,
                    patient_id=patient_id
                )
                
                return [record for record in result]
                
        except Exception as e:
            logger.error(f"Error getting medication history for patient {patient_id}: {str(e)}")
            raise
            
    def get_potential_drug_interactions(self, patient_id):
        """
        Identify potential drug interactions for a patient's active medications
        
        Args:
            patient_id: Patient ID
            
        Returns:
            list: List of potential interactions
        """
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (p:Patient {patient_id: $patient_id})-[:HAS_PRESCRIPTION]->(pr:Prescription)-[:INCLUDES]->(m1:Medication)
                    MATCH (m1)-[i:INTERACTS_WITH]->(m2:Medication)
                    MATCH (p)-[:HAS_PRESCRIPTION]->(pr2:Prescription)-[:INCLUDES]->(m2)
                    WHERE pr.status = 'active' AND pr2.status = 'active'
                    RETURN m1.name as medication1, 
                           m2.name as medication2,
                           i.severity as severity,
                           i.description as description
                    ORDER BY i.severity DESC
                    """,
                    patient_id=patient_id
                )
                
                return [record for record in result]
                
        except Exception as e:
            logger.error(f"Error getting drug interactions for patient {patient_id}: {str(e)}")
            raise
            
    def get_doctor_prescription_patterns(self, doctor_id):
        """
        Analyze prescription patterns for a specific doctor
        
        Args:
            doctor_id: Doctor ID
            
        Returns:
            list: Analysis of doctor's prescription patterns
        """
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (d:Doctor {doctor_id: $doctor_id})-[:PRESCRIBED]->(:Prescription)-[:INCLUDES]->(m:Medication)
                    RETURN m.name as medication, count(*) as prescription_count
                    ORDER BY prescription_count DESC
                    LIMIT 10
                    """,
                    doctor_id=doctor_id
                )
                
                return [record for record in result]
                
        except Exception as e:
            logger.error(f"Error getting prescription patterns for doctor {doctor_id}: {str(e)}")
            raise
            
    
    def get_medication_analytics(self, medication_name):
        """
        Get analytics for a specific medication
        
        Args:
            medication_name: Name of the medication
            
        Returns:
            dict: Analytics for the medication
        """
        try:
            with self.driver.session() as session:
                # Get total prescriptions
                count_result = session.run(
                    """
                    MATCH (:Prescription)-[:INCLUDES]->(m:Medication {name: $medication_name})
                    RETURN count(*) as total_prescriptions
                    """,
                    medication_name=medication_name
                ).single()
                
                # Get doctor distribution
                doctor_result = session.run(
                    """
                    MATCH (d:Doctor)-[:PRESCRIBED]->(p:Prescription)-[:INCLUDES]->(m:Medication {name: $medication_name})
                    RETURN d.name as doctor_name, count(*) as prescription_count
                    ORDER BY prescription_count DESC
                    LIMIT 5
                    """,
                    medication_name=medication_name
                )
                
                # Get common co-prescribed medications
                coprescribed_result = session.run(
                    """
                    MATCH (p:Prescription)-[:INCLUDES]->(m:Medication {name: $medication_name})
                    MATCH (p)-[:INCLUDES]->(other:Medication)
                    WHERE other.name <> $medication_name
                    RETURN other.name as other_medication, count(*) as coprescribed_count
                    ORDER BY coprescribed_count DESC
                    LIMIT 5
                    """,
                    medication_name=medication_name
                )
                
                analytics = {
                    "total_prescriptions": count_result["total_prescriptions"],
                    "top_prescribing_doctors": [
                        {"doctor": record["doctor_name"], "count": record["prescription_count"]} 
                        for record in doctor_result
                    ],
                    "common_coprescribed_medications": [
                        {"medication": record["other_medication"], "count": record["coprescribed_count"]} 
                        for record in coprescribed_result
                    ]
                }
                
                return analytics
                
        except Exception as e:
            logger.error(f"Error getting analytics for medication {medication_name}: {str(e)}")
            raise

    def find_similar_patients(self, patient_id, limit=5):
        """
        Find patients with similar medication profiles
        
        Args:
            patient_id: Patient ID
            limit: Maximum number of similar patients to return
            
        Returns:
            list: Similar patients with similarity score
        """
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (p1:Patient {patient_id: $patient_id})-[:HAS_PRESCRIPTION]->(pr1:Prescription)-[:INCLUDES]->(m:Medication)
                    WITH p1, collect(distinct m.name) as p1Meds
                    
                    MATCH (p2:Patient)-[:HAS_PRESCRIPTION]->(pr2:Prescription)-[:INCLUDES]->(m2:Medication)
                    WHERE p2.patient_id <> $patient_id
                    WITH p1, p1Meds, p2, collect(distinct m2.name) as p2Meds
                    
                    WITH p1, p2, 
                         p1Meds, p2Meds,
                         [med in p1Meds WHERE med in p2Meds] as commonMeds,
                         size(p1Meds) as p1MedsCount,
                         size(p2Meds) as p2MedsCount
                    
                    WITH p1, p2, 
                         p1MedsCount, p2MedsCount,
                         size(commonMeds) as commonMedsCount,
                         commonMeds
                    
                    WITH p2, 
                         1.0 * commonMedsCount / (p1MedsCount + p2MedsCount - commonMedsCount) as similarity,
                         commonMeds
                    
                    WHERE similarity > 0
                    RETURN p2.patient_id as patient_id, 
                           p2.name as name,
                           p2.age as age,
                           p2.gender as gender,
                           similarity,
                           commonMeds
                    ORDER BY similarity DESC
                    LIMIT $limit
                    """,
                    patient_id=patient_id,
                    limit=limit
                )
                
                return [record for record in result]
                
        except Exception as e:
            logger.error(f"Error finding similar patients for {patient_id}: {str(e)}")
            raise

