
# data/mongodb/prescription_repo.py
from pymongo import MongoClient, ASCENDING, DESCENDING, errors
from bson.objectid import ObjectId
import datetime
from utils.logger import get_logger

logger = get_logger(__name__)

class PrescriptionRepository:
    """MongoDB repository for prescription data"""
    
    def __init__(self, connection_string, db_name="medical_system"):
        """
        Initialize the repository
        
        Args:
            connection_string: MongoDB connection string
            db_name: Database name
        """
        try:
            self.client = MongoClient(connection_string)
            self.db = self.client[db_name]
            self.prescriptions = self.db.prescriptions
            self.patients = self.db.patients
            self.doctors = self.db.doctors
            self.medications = self.db.medications
            
            # Create indexes
            self._create_indexes()
            
            logger.info(f"Connected to MongoDB: {db_name}")
            
        except errors.ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise
            
    def _create_indexes(self):
        """Create necessary indexes for performance"""
        try:
            # Prescriptions collection indexes
            self.prescriptions.create_index([("patient_id", ASCENDING)])
            self.prescriptions.create_index([("doctor_id", ASCENDING)])
            self.prescriptions.create_index([("created_at", DESCENDING)])
            self.prescriptions.create_index([("medications.name", ASCENDING)])
            
            # Patients collection indexes
            self.patients.create_index([("medical_id", ASCENDING)], unique=True)
            self.patients.create_index([("name", ASCENDING)])
            
            # Doctors collection indexes
            self.doctors.create_index([("license_number", ASCENDING)], unique=True)
            self.doctors.create_index([("name", ASCENDING)])
            
            # Medications collection indexes
            self.medications.create_index([("name", ASCENDING)], unique=True)
            
            logger.info("MongoDB indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating MongoDB indexes: {str(e)}")
            
    def save_prescription(self, prescription_data):
        """
        Save a new prescription
        
        Args:
            prescription_data: Dictionary containing prescription details
            
        Returns:
            str: ID of the saved prescription
        """
        try:
            # Add timestamp
            prescription_data["created_at"] = datetime.datetime.now()
            prescription_data["updated_at"] = prescription_data["created_at"]
            
            # Insert prescription
            result = self.prescriptions.insert_one(prescription_data)
            
            # Update patient's prescription history
            if "patient_id" in prescription_data:
                self.patients.update_one(
                    {"_id": ObjectId(prescription_data["patient_id"])},
                    {"$push": {"prescription_ids": result.inserted_id}}
                )
                
            logger.info(f"Saved prescription {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error saving prescription: {str(e)}")
            raise
    
    def get_prescription(self, prescription_id):
        """
        Get a prescription by ID
        
        Args:
            prescription_id: Prescription ID
            
        Returns:
            dict: Prescription data or None if not found
        """
        try:
            result = self.prescriptions.find_one({"_id": ObjectId(prescription_id)})
            return result
        except Exception as e:
            logger.error(f"Error retrieving prescription {prescription_id}: {str(e)}")
            raise

    def update_prescription(self, prescription_id, update_data):
        """
        Update an existing prescription
        
        Args:
            prescription_id: ID of the prescription to update
            update_data: Dictionary containing fields to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Add updated timestamp
            update_data["updated_at"] = datetime.datetime.now()
            
            result = self.prescriptions.update_one(
                {"_id": ObjectId(prescription_id)},
                {"$set": update_data}
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Updated prescription {prescription_id}")
            else:
                logger.warning(f"No changes made to prescription {prescription_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error updating prescription {prescription_id}: {str(e)}")
            raise

    def delete_prescription(self, prescription_id):
        """
        Delete a prescription by ID
        
        Args:
            prescription_id: ID of the prescription to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get prescription to find patient ID
            prescription = self.prescriptions.find_one({"_id": ObjectId(prescription_id)})
            
            if prescription and "patient_id" in prescription:
                # Remove prescription reference from patient document
                self.patients.update_one(
                    {"_id": ObjectId(prescription["patient_id"])},
                    {"$pull": {"prescription_ids": ObjectId(prescription_id)}}
                )
            
            # Delete the prescription
            result = self.prescriptions.delete_one({"_id": ObjectId(prescription_id)})
            
            success = result.deleted_count > 0
            if success:
                logger.info(f"Deleted prescription {prescription_id}")
            else:
                logger.warning(f"Prescription {prescription_id} not found for deletion")
                
            return success
            
        except Exception as e:
            logger.error(f"Error deleting prescription {prescription_id}: {str(e)}")
            raise

    def get_patient_prescriptions(self, patient_id, limit=20, skip=0):
        """
        Get prescriptions for a specific patient
        
        Args:
            patient_id: Patient ID
            limit: Maximum number of prescriptions to return
            skip: Number of prescriptions to skip (for pagination)
            
        Returns:
            list: List of prescription documents
        """
        try:
            cursor = self.prescriptions.find(
                {"patient_id": patient_id}
            ).sort("created_at", DESCENDING).skip(skip).limit(limit)
            
            return list(cursor)
            
        except Exception as e:
            logger.error(f"Error retrieving prescriptions for patient {patient_id}: {str(e)}")
            raise

    def get_doctor_prescriptions(self, doctor_id, limit=20, skip=0):
        """
        Get prescriptions issued by a specific doctor
        
        Args:
            doctor_id: Doctor ID
            limit: Maximum number of prescriptions to return
            skip: Number of prescriptions to skip (for pagination)
            
        Returns:
            list: List of prescription documents
        """
        try:
            cursor = self.prescriptions.find(
                {"doctor_id": doctor_id}
            ).sort("created_at", DESCENDING).skip(skip).limit(limit)
            
            return list(cursor)
            
        except Exception as e:
            logger.error(f"Error retrieving prescriptions for doctor {doctor_id}: {str(e)}")
            raise

    def get_medication_prescriptions(self, medication_name, limit=20, skip=0):
        """
        Get prescriptions containing a specific medication
        
        Args:
            medication_name: Name of the medication
            limit: Maximum number of prescriptions to return
            skip: Number of prescriptions to skip (for pagination)
            
        Returns:
            list: List of prescription documents
        """
        try:
            cursor = self.prescriptions.find(
                {"medications.name": medication_name}
            ).sort("created_at", DESCENDING).skip(skip).limit(limit)
            
            return list(cursor)
            
        except Exception as e:
            logger.error(f"Error retrieving prescriptions for medication {medication_name}: {str(e)}")
            raise

    def save_patient(self, patient_data):
        """
        Save a new patient
        
        Args:
            patient_data: Dictionary containing patient details
            
        Returns:
            str: ID of the saved patient
        """
        try:
            # Add timestamp
            patient_data["created_at"] = datetime.datetime.now()
            patient_data["updated_at"] = patient_data["created_at"]
            
            # Initialize prescription list if not present
            if "prescription_ids" not in patient_data:
                patient_data["prescription_ids"] = []
            
            # Insert patient
            result = self.patients.insert_one(patient_data)
            
            logger.info(f"Saved patient {result.inserted_id}")
            return str(result.inserted_id)
            
        except errors.DuplicateKeyError:
            logger.error(f"Duplicate medical ID for patient: {patient_data.get('medical_id')}")
            raise
        except Exception as e:
            logger.error(f"Error saving patient: {str(e)}")
            raise

    def save_doctor(self, doctor_data):
        """
        Save a new doctor
        
        Args:
            doctor_data: Dictionary containing doctor details
            
        Returns:
            str: ID of the saved doctor
        """
        try:
            # Add timestamp
            doctor_data["created_at"] = datetime.datetime.now()
            doctor_data["updated_at"] = doctor_data["created_at"]
            
            # Insert doctor
            result = self.doctors.insert_one(doctor_data)
            
            logger.info(f"Saved doctor {result.inserted_id}")
            return str(result.inserted_id)
            
        except errors.DuplicateKeyError:
            logger.error(f"Duplicate license number for doctor: {doctor_data.get('license_number')}")
            raise
        except Exception as e:
            logger.error(f"Error saving doctor: {str(e)}")
            raise

    def save_medication(self, medication_data):
        """
        Save a new medication
        
        Args:
            medication_data: Dictionary containing medication details
            
        Returns:
            str: ID of the saved medication
        """
        try:
            # Add timestamp
            medication_data["created_at"] = datetime.datetime.now()
            medication_data["updated_at"] = medication_data["created_at"]
            
            # Insert medication
            result = self.medications.insert_one(medication_data)
            
            logger.info(f"Saved medication {result.inserted_id}")
            return str(result.inserted_id)
            
        except errors.DuplicateKeyError:
            logger.error(f"Duplicate name for medication: {medication_data.get('name')}")
            raise
        except Exception as e:
            logger.error(f"Error saving medication: {str(e)}")
            raise

