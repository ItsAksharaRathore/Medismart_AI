import numpy as np
import cv2
from langdetect import detect, detect_langs
from langdetect.lang_detect_exception import LangDetectException
from utils.logger import get_logger

logger = get_logger(__name__)

def detect_language(image=None, text=None):
    """
    Detect the language of text in an image or provided text
    
    Args:
        image: Optional image array
        text: Optional text string
        
    Returns:
        Detected language code (e.g., 'en', 'fr', 'es')
    """
    try:
        # If text is provided, use it directly
        if text:
            return detect_text_language(text)
            
        # If image is provided, extract and detect text
        if image is not None:
            # For image-based detection, we'll need OCR first
            # This is a simplified implementation using Tesseract
            import pytesseract
            
            # Extract text using multiple language models
            languages = ['eng', 'fra', 'deu', 'spa', 'ara', 'hin', 'chi_sim']
            texts = {}
            confidences = {}
            
            for lang in languages:
                try:
                    # Extract text with language-specific model
                    text = pytesseract.image_to_string(image, lang=lang)
                    
                    # Calculate confidence based on character count
                    if len(text.strip()) > 0:
                        texts[lang] = text
                        confidences[lang] = len(text.strip())
                except Exception:
                    continue
                    
            # If no text was extracted, return default
            if not texts:
                return 'eng'
                
            # Use the language with highest text extraction
            best_lang = max(confidences, key=confidences.get)
            
            # Try to detect language from the best text
            extracted_text = texts[best_lang]
            detected_lang = detect_text_language(extracted_text)
            
            # Map Tesseract language codes to standard codes
            lang_mapping = {
                'eng': 'en',
                'fra': 'fr',
                'deu': 'de',
                'spa': 'es',
                'ara': 'ar',
                'hin': 'hi',
                'chi_sim': 'zh-cn'
            }
            
            return detected_lang
            
        # If neither text nor image is provided
        logger.error("Either text or image must be provided")
        return None
        
    except Exception as e:
        logger.error(f"Error detecting language: {str(e)}")
        return 'en'  # Default to English on error


def detect_text_language(text):
    """
    Detect the language of the provided text
    
    Args:
        text: String of text to analyze
        
    Returns:
        Language code (e.g., 'en', 'fr', 'es')
    """
    try:
        # Try to detect the language
        language = detect(text)
        
        # Get language with confidence scores
        language_probabilities = detect_langs(text)
        
        # Log the confidence scores
        logger.debug(f"Language probabilities: {language_probabilities}")
        
        return language
    except LangDetectException as e:
        logger.warning(f"Failed to detect language: {str(e)}")
        return 'en'  # Default to English on error
    except Exception as e:
        logger.error(f"Unexpected error in language detection: {str(e)}")
        return 'en'  # Default to English on error


def process_prescription_image(image_path):
    """
    Process a prescription image to detect language and prepare for further analysis
    
    Args:
        image_path: Path to the prescription image
        
    Returns:
        dict: Dictionary containing language and processed image information
    """
    try:
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            logger.error(f"Failed to load image: {image_path}")
            return {'error': 'Failed to load image'}
            
        # Preprocess image
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Adaptive thresholding to handle varying lighting
        binary = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # Detect language
        language = detect_language(image=binary)
        
        return {
            'language': language,
            'processed_image': binary,
            'original_image': image
        }
    except Exception as e:
        logger.error(f"Error processing prescription image: {str(e)}")
        return {'error': str(e)}