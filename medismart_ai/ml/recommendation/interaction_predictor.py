import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.multioutput import MultiOutputClassifier
import networkx as nx
from utils.logger import get_logger

logger = get_logger(__name__)

class InteractionPredictor:
    """ML-based drug interaction prediction model"""
    
    def __init__(self):
        """Initialize the interaction predictor"""
        try:
            self.drug_features = None
            self.interaction_model = None
            self.vectorizer = TfidfVectorizer(stop_words='english')
            self.drug_index = {}  # Maps drug names to indices
            self.interaction_types = []  # Types of interactions to predict
            self.interaction_graph = nx.Graph()  # Graph of known interactions
            self.severity_threshold = 0.7  # Threshold for high severity interactions
            
            logger.info("Interaction predictor initialized")
            
        except Exception as e:
            logger.error(f"Error initializing interaction predictor: {str(e)}")
            raise
            
    def load_data(self, drug_data_path, interaction_data_path):
        """
        Load drug and interaction data
        
        Args:
            drug_data_path: Path to drug data CSV
            interaction_data_path: Path to interaction data CSV
        """
        try:
            # Load drug data
            drug_df = pd.read_csv(drug_data_path)
            
            # Create drug feature vectors
            drug_features = []
            for i, row in drug_df.iterrows():
                self.drug_index[row['drug_name']] = i
                
                # Combine features into a text representation
                features = f"{row['drug_name']} {row['drug_class']} {row.get('mechanism', '')} {row.get('target', '')}"
                drug_features.append(features)
                
                # Add node to interaction graph
                self.interaction_graph.add_node(row['drug_name'])
                
            # Create TF-IDF feature matrix
            self.drug_features = self.vectorizer.fit_transform(drug_features)
            
            # Load interaction data
            interaction_df = pd.read_csv(interaction_data_path)
            
            # Extract interaction types
            self.interaction_types = sorted(interaction_df['interaction_type'].unique())
            
            # Build interaction training data
            X, y = self._prepare_interaction_training_data(interaction_df)
            
            # Train the model
            self._train_model(X, y)
            
            # Build interaction graph
            self._build_interaction_graph(interaction_df)
            
            logger.info(f"Loaded data for {len(self.drug_index)} drugs and {len(self.interaction_types)} interaction types")
            
        except Exception as e:
            logger.error(f"Error loading interaction data: {str(e)}")
            raise
            
    def _prepare_interaction_training_data(self, interaction_df):
        """Prepare training data for interaction prediction"""
        # Create feature pairs for interacting drugs
        X = []
        y = []
        
        for _, row in interaction_df.iterrows():
            drug1 = row['drug1']
            drug2 = row['drug2']
            
            # Skip if either drug is not in our index
            if drug1 not in self.drug_index or drug2 not in self.drug_index:
                continue
                
            # Get drug feature vectors
            idx1 = self.drug_index[drug1]
            idx2 = self.drug_index[drug2]
            
            # Combine feature vectors (concatenate)
            feature_vector = np.hstack([
                self.drug_features[idx1].toarray(),
                self.drug_features[idx2].toarray()
            ])
            
            X.append(feature_vector.flatten())
            
            # Create multi-label target
            interaction_label = [0] * len(self.interaction_types)
            interaction_label[self.interaction_types.index(row['interaction_type'])] = 1
            y.append(interaction_label)
            
        return np.array(X), np.array(y)
        
    def _train_model(self, X, y):
        """Train the interaction prediction model"""
        # Use Random Forest for multi-label classification
        base_classifier = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        
        self.interaction_model = MultiOutputClassifier(base_classifier)
        self.interaction_model.fit(X, y)
        
        logger.info("Interaction prediction model trained successfully")
        
    def _build_interaction_graph(self, interaction_df):
        """Build a graph of known drug interactions"""
        for _, row in interaction_df.iterrows():
            drug1 = row['drug1']
            drug2 = row['drug2']
            
            # Skip if either drug is not in our graph
            if drug1 not in self.drug_index or drug2 not in self.drug_index:
                continue
                
            # Add edge with interaction information
            self.interaction_graph.add_edge(
                drug1, drug2,
                interaction_type=row['interaction_type'],
                severity=row.get('severity', 'unknown'),
                description=row.get('description', '')
            )
            
        logger.info(f"Built interaction graph with {self.interaction_graph.number_of_edges()} known interactions")
        
    def predict_interaction(self, drug1, drug2):
        """
        Predict potential interactions between two drugs
        
        Args:
            drug1: First drug name
            drug2: Second drug name
            
        Returns:
            dict: Predicted interaction details
        """
        try:
            # Check if this is a known interaction first
            if self.interaction_graph.has_edge(drug1, drug2):
                edge_data = self.interaction_graph.get_edge_data(drug1, drug2)
                return {
                    'drug1': drug1,
                    'drug2': drug2,
                    'interaction_type': edge_data['interaction_type'],
                    'severity': edge_data['severity'],
                    'description': edge_data['description'],
                    'is_known': True,
                    'confidence': 1.0
                }
                
            # Check if both drugs are in our index
            if drug1 not in self.drug_index or drug2 not in self.drug_index:
                logger.warning(f"One or both drugs not in database: {drug1}, {drug2}")
                return {
                    'drug1': drug1,
                    'drug2': drug2,
                    'interaction_predicted': False,
                    'reason': "One or both drugs not in database"
                }
                
            # Get drug feature vectors
            idx1 = self.drug_index[drug1]
            idx2 = self.drug_index[drug2]
            
            # Combine feature vectors
            feature_vector = np.hstack([
                self.drug_features[idx1].toarray(),
                self.drug_features[idx2].toarray()
            ])
            
            # Make prediction
            X = feature_vector.reshape(1, -1)
            y_pred = self.interaction_model.predict(X)[0]
            y_prob = self.interaction_model.predict_proba(X)
            
            # Get interaction type with highest probability
            interaction_probs = [prob[0][1] for prob in y_prob]
            max_prob_idx = np.argmax(interaction_probs)
            max_prob = interaction_probs[max_prob_idx]
            
            # Only predict interaction if probability exceeds threshold
            if max_prob >= 0.5:
                predicted_type = self.interaction_types[max_prob_idx]
                
                # Estimate severity based on probability
                if max_prob >= self.severity_threshold:
                    severity = "high"
                else:
                    severity = "moderate"
                    
                return {
                    'drug1': drug1,
                    'drug2': drug2,
                    'interaction_predicted': True,
                    'interaction_type': predicted_type,
                    'severity': severity,
                    'confidence': float(max_prob),
                    'is_known': False
                }
            else:
                return {
                    'drug1': drug1,
                    'drug2': drug2,
                    'interaction_predicted': False,
                    'confidence': float(1 - max_prob)
                }
                
        except Exception as e:
            logger.error(f"Error predicting interaction: {str(e)}")
            return {
                'drug1': drug1,
                'drug2': drug2,
                'error': str(e)
            }
            
    def predict_interactions_for_prescription(self, medications):
        """
        Predict all potential interactions for a prescription with multiple medications
        
        Args:
            medications: List of medication names
            
        Returns:
            list: Predicted interactions
        """
        interactions = []
        
        # Check all pairs of medications
        for i in range(len(medications)):
            for j in range(i+1, len(medications)):
                drug1 = medications[i]
                drug2 = medications[j]
                
                interaction = self.predict_interaction(drug1, drug2)
                
                # Add to results if interaction is predicted
                if interaction.get('interaction_predicted', False) or interaction.get('is_known', False):
                    interactions.append(interaction)
                    
        # Sort by confidence/severity
        interactions.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        return interactions
        
    def find_alternative_medication(self, medication, condition, medications_to_avoid, n=3):
        """
        Find alternative medications that don't interact with current medications
        
        Args:
            medication: Current medication to find alternatives for
            condition: Medical condition being treated
            medications_to_avoid: List of medications to avoid interactions with
            n: Number of alternatives to suggest
            
        Returns:
            list: Alternative medications
        """
        try:
            alternatives = []
            
            # Find medications for the same condition
            # This would typically use a database of drug indications
            # For demonstration, using a simplified approach with NetworkX
            
            # Get medications with similar features
            idx = self.drug_index.get(medication)
            if idx is None:
                return []
                
            # Get feature vector for current medication
            med_features = self.drug_features[idx].toarray().flatten()
            
            # Calculate similarity to all other medications
            similarities = []
            for name, i in self.drug_index.items():
                if name == medication:
                    continue
                    
                other_features = self.drug_features[i].toarray().flatten()
                similarity = np.dot(med_features, other_features) / (
                    np.linalg.norm(med_features) * np.linalg.norm(other_features))
                
                similarities.append((name, similarity))
                
            # Sort by similarity
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Check each potential alternative for interactions
            for alt_name, similarity in similarities:
                if len(alternatives) >= n:
                    break
                    
                # Check for interactions with medications to avoid
                has_interaction = False
                for med in medications_to_avoid:
                    interaction = self.predict_interaction(alt_name, med)
                    if interaction.get('interaction_predicted', False) or interaction.get('is_known', False):
                        has_interaction = True
                        break
                        
                if not has_interaction:
                    alternatives.append({
                        'medication': alt_name,
                        'similarity': float(similarity),
                        'reason': f"Similar to {medication} with no predicted interactions"
                    })
                    
            return alternatives
            
        except Exception as e:
            logger.error(f"Error finding alternative medications: {str(e)}")
            return []
            
    def explain_interaction(self, drug1, drug2):
        """
        Provide detailed explanation of an interaction mechanism
        
        Args:
            drug1: First drug name
            drug2: Second drug name
            
        Returns:
            str: Explanation of the interaction mechanism
        """
        # This would typically use a detailed drug interaction database
        # For demonstration, using a simplified approach with the graph
        
        if self.interaction_graph.has_edge(drug1, drug2):
            edge_data = self.interaction_graph.get_edge_data(drug1, drug2)
            
            explanation = (
                f"Interaction: {drug1} + {drug2}\n"
                f"Type: {edge_data['interaction_type']}\n"
                f"Severity: {edge_data['severity']}\n\n"
                f"{edge_data['description']}"
            )
            
            return explanation
        else:
            # For predicted interactions, provide a generic explanation
            interaction = self.predict_interaction(drug1, drug2)
            
            if interaction.get('interaction_predicted', False):
                return (
                    f"Predicted interaction: {drug1} + {drug2}\n"
                    f"Type: {interaction['interaction_type']}\n"
                    f"Severity: {interaction['severity']}\n"
                    f"Confidence: {interaction['confidence']:.2f}\n\n"
                    f"This interaction is predicted based on the molecular properties "
                    f"and pharmacological profiles of both medications."
                )
            else:
                return f"No known or predicted interaction between {drug1} and {drug2}."