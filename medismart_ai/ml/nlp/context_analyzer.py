import spacy
from transformers import pipeline
import numpy as np
import re
from utils.logger import get_logger

logger = get_logger(__name__)

class ContextAnalyzer:
    """Analyzes medical context in prescriptions and notes"""
    
    def __init__(self):
        """Initialize the context analyzer"""
        try:
            # Load language model
            self.nlp = spacy.load("en_core_web_lg")
            
            # Initialize sentiment analysis from transformers
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english",
                truncation=True
            )
            
            # Initialize zero-shot classification
            self.classifier = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
                truncation=True
            )
            
            # Common medical contexts
            self.medical_contexts = [
                "emergency", "routine care", "chronic condition",
                "acute illness", "preventative care", "post-surgery",
                "pregnancy", "pediatric", "geriatric", "mental health",
                "infectious disease", "cardiovascular"
            ]
            
            # Medical urgency indicators
            self.urgency_indicators = [
                "emergency", "urgent", "immediately", "asap", "critical",
                "severe", "life-threatening", "deteriorating", "acute"
            ]
            
            logger.info("Context analyzer initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing context analyzer: {str(e)}")
            raise
            
    def analyze_context(self, text):
        """
        Analyze the medical context of a text
        
        Args:
            text: Medical text to analyze
            
        Returns:
            dict: Context analysis results
        """
        try:
            # Process with spaCy
            doc = self.nlp(text)
            
            # Extract key metrics
            results = {
                'sentiment': self._analyze_sentiment(text),
                'urgency': self._detect_urgency(text),
                'medical_context': self._classify_medical_context(text),
                'key_concerns': self._extract_key_concerns(doc),
                'patient_condition': self._analyze_patient_condition(doc),
                'treatment_stage': self._detect_treatment_stage(doc)
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error analyzing context: {str(e)}")
            return {'error': str(e)}
            
    def _analyze_sentiment(self, text):
        """Analyze the sentiment of the text"""
        try:
            result = self.sentiment_analyzer(text)[0]
            return {
                'label': result['label'],
                'score': result['score']
            }
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {str(e)}")
            return {'label': 'UNKNOWN', 'score': 0.0}
            
    def _detect_urgency(self, text):
        """Detect the urgency level in the text"""
        text_lower = text.lower()
        
        # Check for urgent indicators
        urgency_score = 0
        found_indicators = []
        
        for indicator in self.urgency_indicators:
            if re.search(r'\b' + re.escape(indicator) + r'\b', text_lower):
                urgency_score += 1
                found_indicators.append(indicator)
                
        # Classify urgency level
        if urgency_score >= 3:
            urgency_level = "high"
        elif urgency_score >= 1:
            urgency_level = "medium"
        else:
            urgency_level = "low"
            
        return {
            'level': urgency_level,
            'score': urgency_score,
            'indicators': found_indicators
        }
        
    def _classify_medical_context(self, text):
        """Classify the medical context using zero-shot classification"""
        try:
            result = self.classifier(
                text,
                candidate_labels=self.medical_contexts,
                multi_label=True
            )
            
            # Get top 3 contexts
            top_contexts = []
            for i in range(min(3, len(result['labels']))):
                if result['scores'][i] > 0.3:  # Only include if confidence > 0.3
                    top_contexts.append({
                        'context': result['labels'][i],
                        'confidence': result['scores'][i]
                    })
                    
            return top_contexts
            
        except Exception as e:
            logger.error(f"Error in medical context classification: {str(e)}")
            return []
            
    def _extract_key_concerns(self, doc):
        """Extract key medical concerns from the text"""
        concerns = []
        
        # Look for symptoms and conditions
        symptom_patterns = [
            "pain", "ache", "discomfort", "fever", "cough", "nausea",
            "vomiting", "diarrhea", "fatigue", "weakness", "dizziness",
            "headache", "inflammation", "swelling", "rash", "infection"
        ]
        
        for token in doc:
            if token.lower_ in symptom_patterns or any(
                symptom in token.lower_ for symptom in symptom_patterns):
                
                # Get the full noun chunk if possible
                for chunk in doc.noun_chunks:
                    if token in chunk:
                        concerns.append(chunk.text)
                        break
                else:
                    concerns.append(token.text)
                    
        # Remove duplicates while preserving order
        unique_concerns = []
        for concern in concerns:
            if concern not in unique_concerns:
                unique_concerns.append(concern)
                
        return unique_concerns
        
    def _analyze_patient_condition(self, doc):
        """Analyze the patient's condition based on text"""
        condition_indicators = {
            'stable': ["stable", "improving", "better", "good", "satisfactory"],
            'unstable': ["unstable", "worsening", "deteriorating", "poor", "critical"],
            'chronic': ["chronic", "long-term", "persistent", "recurring", "ongoing"],
            'acute': ["acute", "sudden", "severe", "intense", "new onset"]
        }
        
        # Count indicators for each condition type
        counts = {category: 0 for category in condition_indicators}
        found_terms = {category: [] for category in condition_indicators}
        
        for token in doc:
            for category, indicators in condition_indicators.items():
                if token.lower_ in indicators:
                    counts[category] += 1
                    found_terms[category].append(token.text)
                    
        # Determine primary condition
        if max(counts.values()) == 0:
            primary_condition = "unknown"
        else:
            primary_condition = max(counts, key=counts.get)
            
        return {
            'primary_condition': primary_condition,
            'indicator_counts': counts,
            'found_terms': found_terms
        }
        
    def _detect_treatment_stage(self, doc):
        """Detect the stage of treatment from text"""
        treatment_stages = {
            'initial': ["new", "initial", "first", "start", "beginning", "diagnose"],
            'ongoing': ["continue", "ongoing", "maintain", "follow-up", "adjust"],
            'final': ["complete", "discontinue", "stop", "final", "resolved", "cured"]
        }
        
        # Count indicators for each stage
        counts = {stage: 0 for stage in treatment_stages}
        evidence = {stage: [] for stage in treatment_stages}
        
        for token in doc:
            for stage, indicators in treatment_stages.items():
                if token.lower_ in indicators:
                    counts[stage] += 1
                    evidence[stage].append(token.text)
                    
        # Determine most likely stage
        if max(counts.values()) == 0:
            most_likely_stage = "unknown"
        else:
            most_likely_stage = max(counts, key=counts.get)
            
        return {
            'stage': most_likely_stage,
            'evidence': evidence,
            'confidence': counts[most_likely_stage] / (sum(counts.values()) or 1)
        }