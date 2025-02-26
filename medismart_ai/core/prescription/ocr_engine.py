# core/prescription/ocr_engine.py
import pytesseract
from pytesseract import Output
import cv2
import numpy as np
from ml.nlp.language_detector import detect_language
from utils.logger import get_logger
import os
import tensorflow as tf

logger = get_logger(__name__)

# Load handwriting recognition model (if available)
hw_model = None
try:
    # Path to handwriting recognition model (TensorFlow/Keras model)
    hw_model_path = os.path.join(os.path.dirname(__file__), '../../models/handwriting_model')
    if os.path.exists(hw_model_path):
        hw_model = tf.keras.models.load_model(hw_model_path)
        logger.info("Handwriting recognition model loaded successfully")
except Exception as e:
    logger.warning(f"Failed to load handwriting recognition model: {str(e)}")

def extract_text(image, is_handwritten=False):
    """
    Extract text from preprocessed prescription image
    
    Args:
        image: Preprocessed image as numpy array
        is_handwritten: Boolean indicating if prescription is handwritten
        
    Returns:
        Dictionary with extracted text and metadata
    """
    try:
        # Detect language in the image
        language = detect_language(image)
        lang_config = f"-l {language}" if language else ""
        
        if is_handwritten and hw_model:
            # Use specialized handwriting model for handwritten text
            text_blocks = _extract_handwritten_text(image)
            
            # Combine text blocks to form complete text
            full_text = " ".join([block['text'] for block in text_blocks])
            
            # Calculate confidence
            confidence = np.mean([block['conf'] for block in text_blocks]) if text_blocks else 0
            
        else:
            # Configure Tesseract for better handwriting recognition if handwritten
            if is_handwritten:
                # Use specific Tesseract configuration for handwritten text
                custom_config = f'{lang_config} --oem 1 --psm 6 -c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,;:\'\"()[]{}!?-+/*= "'
            else:
                # Standard configuration for printed text
                custom_config = f'{lang_config} --oem 1 --psm 6'
            
            # Extract text with detailed data
            ocr_data = pytesseract.image_to_data(
                image, 
                config=custom_config, 
                output_type=Output.DICT
            )
            
            # Extract complete text
            full_text = pytesseract.image_to_string(image, config=custom_config)
            
            # Create structured text blocks
            text_blocks = []
            n_boxes = len(ocr_data['text'])
            
            for i in range(n_boxes):
                if int(ocr_data['conf'][i]) > 30:  # Lower confidence threshold for handwritten text
                    text_blocks.append({
                        'text': ocr_data['text'][i],
                        'conf': ocr_data['conf'][i],
                        'x': ocr_data['left'][i],
                        'y': ocr_data['top'][i],
                        'w': ocr_data['width'][i],
                        'h': ocr_data['height'][i]
                    })
            
            # Calculate average confidence
            confidence = np.mean([block['conf'] for block in text_blocks]) if text_blocks else 0
        
        # Post-process extracted text
        corrected_text = _post_process_text(full_text, is_handwritten)
        
        return {
            'full_text': corrected_text,
            'language': language,
            'blocks': text_blocks,
            'confidence': confidence,
            'is_handwritten': is_handwritten
        }
        
    except Exception as e:
        logger.error(f"OCR extraction error: {str(e)}")
        raise

def _extract_handwritten_text(image):
    """
    Extract text from handwritten image using the specialized handwriting model
    
    Args:
        image: Preprocessed image as numpy array
        
    Returns:
        List of text blocks with positions and confidence
    """
    # If no handwriting model available, fall back to Tesseract
    if hw_model is None:
        return []
    
    try:
        # This is a placeholder for actual handwriting model implementation
        # In a real implementation, we would:
        # 1. Segment the image into lines and words
        # 2. Process each segment through the handwriting recognition model
        # 3. Return the recognized text with positions
        
        # Placeholder: For now, we'll just use Tesseract with special config
        custom_config = '--oem 1 --psm 6 -c tessedit_char_whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,;:\'\"()[]{}!?-+/*= "'
        
        ocr_data = pytesseract.image_to_data(
            image, 
            config=custom_config, 
            output_type=Output.DICT
        )
        
        text_blocks = []
        n_boxes = len(ocr_data['text'])
        
        for i in range(n_boxes):
            if int(ocr_data['conf'][i]) > 30 and ocr_data['text'][i].strip():
                text_blocks.append({
                    'text': ocr_data['text'][i],
                    'conf': ocr_data['conf'][i],
                    'x': ocr_data['left'][i],
                    'y': ocr_data['top'][i],
                    'w': ocr_data['width'][i],
                    'h': ocr_data['height'][i]
                })
        
        return text_blocks
        
    except Exception as e:
        logger.error(f"Handwritten text extraction error: {str(e)}")
        return []

def _post_process_text(text, is_handwritten=False):
    """
    Post-process OCR extracted text to correct common errors
    
    Args:
        text: Raw OCR text
        is_handwritten: Boolean indicating if text is from handwritten source
        
    Returns:
        Corrected text
    """
    # Common OCR errors in medical context
    corrections = {
        '0mg': '0 mg',
        '5mg': '5 mg',
        '1Omg': '10 mg',
        '15mg': '15 mg',
        '2Omg': '20 mg',
        '25mg': '25 mg',
        '3Omg': '30 mg',
        '5Omg': '50 mg',
        '10Omg': '100 mg',
        'm!': 'ml',
        'mI': 'ml',
        # Add more common corrections here
    }
    
    # Additional corrections for handwritten text
    if is_handwritten:
        handwritten_corrections = {
            'tabiet': 'tablet',
            'tabiet5': 'tablets',
            'capsuie': 'capsule',
            'capsuies': 'capsules',
            'mg,': 'mg',
            'mi,': 'ml',
            'daiiy': 'daily',
            'rnorning': 'morning',
            'rng': 'mg',
            'ml,': 'ml',
            'lday': '/day',
            '1day': '/day',
            'capsules ': 'capsules',
            'tablets ': 'tablets',
            # Add more handwriting-specific corrections
        }
        
        # Update corrections with handwriting-specific ones
        corrections.update(handwritten_corrections)
    
    # Apply corrections
    corrected = text
    for error, fix in corrections.items():
        corrected = corrected.replace(error, fix)
        
    return corrected