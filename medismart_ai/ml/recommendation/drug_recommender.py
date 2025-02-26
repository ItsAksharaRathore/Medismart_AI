import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import tensorflow as tf
from tensorflow.keras import layers, models
from utils.logger import get_logger

logger = get_logger(__name__)

class DrugRecommender:
    """
    ML-based drug recommendation system for physicians
    Uses collaborative filtering and content-based approaches
    """
    
    def __init__(self):
        """Initialize the drug recommender"""
        try:
            self.drug_features = None
            self.drug_similarity = None
            self.condition_drug_matrix = None
            self.vectorizer = TfidfVectorizer(stop_words='english')
            self.deep_model = None
            self.drug_embeddings = None
            self.drug_names = []
            self.condition_names = []
            self.drug_descriptions = {}
            self.drug_interactions = {}
            
            logger.info("Drug recommender initialized")
            
        except Exception as e:
            logger.error(f"Error initializing drug recommender: {str(e)}")
            raise
            
    def load_data(self, drug_data_path, condition_data_path=None):
        """
        Load drug and condition data for recommendations
        
        Args:
            drug_data_path: Path to drug data CSV
            condition_data_path: Path to condition-drug associations CSV
        """
        try:
            # Load drug data
            drug_df = pd.read_csv(drug_data_path)
            self.drug_names = drug_df['drug_name'].tolist()
            
            # Create drug feature matrix
            drug_features = []
            for _, row in drug_df.iterrows():
                # Combine relevant features into a single text string
                feature_text = f"{row['drug_name']} {row['drug_class']} {row['indications']} {row['mechanism']}"
                drug_features.append(feature_text)
                
                # Store drug description for explanations
                self.drug_descriptions[row['drug_name']] = row['description']
                
            # Use TF-IDF to create feature vectors
            self.drug_features = self.vectorizer.fit_transform(drug_features)
            
            # Calculate drug similarity matrix
            self.drug_similarity = cosine_similarity(self.drug_features)
            
            # Load condition-drug associations if available
            if condition_data_path:
                condition_df = pd.read_csv(condition_data_path)
                self.condition_names = sorted(condition_df['condition'].unique())
                
                # Create condition-drug matrix
                self._create_condition_drug_matrix(condition_df)
                
                # Train deep learning model if enough data
                if len(condition_df) > 1000:
                    self._train_deep_model(condition_df)
                    
            logger.info(f"Loaded data for {len(self.drug_names)} drugs and {len(self.condition_names)} conditions")
            
        except Exception as e:
            logger.error(f"Error loading drug data: {str(e)}")
            raise
            
    def _create_condition_drug_matrix(self, condition_df):
        """Create a matrix of condition-drug associations"""
        # Initialize matrix with zeros
        matrix = np.zeros((len(self.condition_names), len(self.drug_names)))
        
        # Fill matrix with prescription counts or efficacy scores
        for _, row in condition_df.iterrows():
            condition_idx = self.condition_names.index(row['condition'])
            drug_idx = self.drug_names.index(row['drug'])
            
            # Use efficacy or frequency as the value
            if 'efficacy' in row:
                value = row['efficacy']
            elif 'frequency' in row:
                value = row['frequency']
            else:
                value = 1  # Binary association
                
            matrix[condition_idx, drug_idx] = value
            
        self.condition_drug_matrix = matrix
        
    def _train_deep_model(self, condition_df):
        """Train a deep learning model for drug recommendations"""
        try:
            # Create embedding dimensions
            n_drugs = len(self.drug_names)
            n_conditions = len(self.condition_names)
            embedding_dim = 50
            
            # Build the model
            drug_input = layers.Input(shape=(1,))
            condition_input = layers.Input(shape=(1,))
            
            # Embedding layers
            drug_embedding = layers.Embedding(n_drugs, embedding_dim)(drug_input)
            drug_embedding = layers.Flatten()(drug_embedding)
            
            condition_embedding = layers.Embedding(n_conditions, embedding_dim)(condition_input)
            condition_embedding = layers.Flatten()(condition_embedding)
            
            # Concatenate embeddings
            concat = layers.Concatenate()([drug_embedding, condition_embedding])
            
            # Dense layers
            dense1 = layers.Dense(128, activation='relu')(concat)
            dense2 = layers.Dense(64, activation='relu')(dense1)
            dense3 = layers.Dense(32, activation='relu')(dense2)
            
            # Output layer
            output = layers.Dense(1, activation='sigmoid')(dense3)
            
            # Create and compile model
            self.deep_model = models.Model(
                inputs=[drug_input, condition_input],
                outputs=output
            )
            
            self.deep_model.compile(
                optimizer='adam',
                loss='binary_crossentropy',
                metrics=['accuracy']
            )
            
            # Prepare training data
            drug_indices = []
            condition_indices = []
            targets = []
            
            for _, row in condition_df.iterrows():
                drug_idx = self.drug_names.index(row['drug'])
                condition_idx = self.condition_names.index(row['condition'])
                
                # Use efficacy or frequency as target, normalized to 0-1
                if 'efficacy' in row:
                    target = row['efficacy'] / 10.0  # Assuming efficacy is 0-10
                elif 'frequency' in row:
                    target = min(row['frequency'] / 100.0, 1.0)  # Normalize frequency
                else:
                    target = 1.0  # Binary association
                    
                drug_indices.append(drug_idx)
                condition_indices.append(condition_idx)
                targets.append(target)
                
            # Convert to numpy arrays
            drug_indices = np.array(drug_indices)
            condition_indices = np.array(condition_indices)
            targets = np.array(targets)
            
            # Train the model
            self.deep_model.fit(
                [drug_indices, condition_indices],
                targets,
                epochs=20,
                batch_size=64,
                validation_split=0.2,
                verbose=0
            )
            
            # Extract drug embeddings for similarity calculations
            drug_ids = np.arange(n_drugs)
            drug_layer = self.deep_model.get_layer('embedding')
            self.drug_embeddings = drug_layer.get_weights()[0]
            
            logger.info("Deep learning model trained successfully")
            
        except Exception as e:
            logger.error(f"Error training deep model: {str(e)}")
            self.deep_model = None
            
    def recommend_for_condition(self, condition, n=5):
        """
        Recommend drugs for a specific medical condition
        
        Args:
            condition: Medical condition name
            n: Number of recommendations to return
            
        Returns:
            list: Recommended drugs with scores
        """
        try:
            # Check if condition is known
            if condition not in self.condition_names:
                logger.warning(f"Unknown condition: {condition}")
                return []
                
            condition_idx = self.condition_names.index(condition)
            
            # Get drugs already associated with this condition
            if self.condition_drug_matrix is not None:
                condition_drugs = self.condition_drug_matrix[condition_idx]
                
                # Sort drugs by association strength
                sorted_indices = np.argsort(condition_drugs)[::-1]
                
                # Get top n drugs
                recommendations = []
                for idx in sorted_indices[:n]:
                    if condition_drugs[idx] > 0:
                        recommendations.append({
                            'drug': self.drug_names[idx],
                            'score': float(condition_drugs[idx]),
                            'reason': f"Commonly prescribed for {condition}"
                        })
                        
                return recommendations
            else:
                logger.warning("No condition-drug matrix available")
                return []
                
        except Exception as e:
            logger.error(f"Error recommending for condition: {str(e)}")
            return []
            
    def recommend_similar_drugs(self, drug_name, n=5):
        """
        Recommend similar drugs to the given drug
        
        Args:
            drug_name: Name of the drug to find alternatives for
            n: Number of recommendations to return
            
        Returns:
            list: Similar drugs with similarity scores
        """
        try:
            # Check if drug is known
            if drug_name not in self.drug_names:
                logger.warning(f"Unknown drug: {drug_name}")
                return []
                
            drug_idx = self.drug_names.index(drug_name)
            
            # Get similarity scores
            similarity_scores = self.drug_similarity[drug_idx]
            
            # Sort by similarity (excluding the drug itself)
            sorted_indices = np.argsort(similarity_scores)[::-1][1:n+1]
            
            # Get top n similar drugs
            similar_drugs = []
            for idx in sorted_indices:
                similar_drugs.append({
                    'drug': self.drug_names[idx],
                    'similarity': float(similarity_scores[idx]),
                    'reason': f"Similar to {drug_name} in mechanism and indication"
                })
                
            return similar_drugs
            
        except Exception as e:
            logger.error(f"Error finding similar drugs: {str(e)}")
            return []
            
    def recommend_for_patient(self, patient_data, n=5):
        """
        Recommend drugs based on patient-specific data
        
        Args:
            patient_data: Dictionary with patient information
            n: Number of recommendations to return
            
        Returns:
            list: Personalized drug recommendations
        """
        try:
            recommendations = []
            
            # Get recommendations for patient's condition
            if 'condition' in patient_data and patient_data['condition'] in self.condition_names:
                condition_recs = self.recommend_for_condition(patient_data['condition'], n=n)
                recommendations.extend(condition_recs)
                
            # Filter based on patient allergies
            if 'allergies' in patient_data and patient_data['allergies']:
                recommendations = [
                    rec for rec in recommendations 
                    if rec['drug'] not in patient_data['allergies']
                ]
                
            # Consider patient age for appropriate medications
            if 'age' in patient_data:
                age = patient_data['age']
                
                # Add age-specific reasoning
                for rec in recommendations:
                    if age < 18:
                        rec['note'] = "Verify pediatric dosing"
                    elif age > 65:
                        rec['note'] = "Consider geriatric dosing adjustments"
                        
            # Consider patient's current medications for interactions
            if 'current_medications' in patient_data:
                for rec in recommendations:
                    # Check for interactions (this would use a proper drug interaction database)
                    interactions = self._check_interactions(
                        rec['drug'], 
                        patient_data['current_medications']
                    )
                    if interactions:
                        rec['interactions'] = interactions
                        
            # Sort by score if available
            if recommendations:
                recommendations.sort(key=lambda x: x.get('score', 0), reverse=True)
                
            return recommendations[:n]
            
        except Exception as e:
            logger.error(f"Error in patient-specific recommendations: {str(e)}")
            return []
            
    def _check_interactions(self, drug, current_medications):
        """Check for interactions between a drug and current medications"""
        # This would typically use a drug interaction database
        # For demonstration, using a simplified approach
        
        # Sample interaction pairs (would be from a database)
        interaction_pairs = [
            ('ibuprofen', 'aspirin', 'Increased risk of bleeding'),
            ('lisinopril', 'potassium', 'Risk of hyperkalemia'),
            ('warfarin', 'aspirin', 'Increased risk of bleeding'),
            ('fluoxetine', 'sertraline', 'Serotonin syndrome risk')
        ]
        
        # Check for interactions
        interactions = []
        for med1, med2, risk in interaction_pairs:
            if (drug.lower() == med1 and med2 in [m.lower() for m in current_medications]) or \
               (drug.lower() == med2 and med1 in [m.lower() for m in current_medications]):
                interactions.append({
                    'medication': med1 if drug.lower() == med2 else med2,
                    'risk': risk
                })
                
        return interactions
        
    def explain_recommendation(self, drug_name):
        """
        Provide an explanation for why a drug is recommended
        
        Args:
            drug_name: Name of the drug to explain
            
        Returns:
            str: Explanation of the drug
        """
        if drug_name in self.drug_descriptions:
            return self.drug_descriptions[drug_name]
        else:
            return f"No detailed information available for {drug_name}"