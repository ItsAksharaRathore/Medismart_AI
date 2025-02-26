# core/prescription/preprocessor.py
import cv2
import numpy as np
from PIL import Image
import io
from utils.logger import get_logger

logger = get_logger(__name__)

def preprocess_image(image_file, is_handwritten=False):
    """
    Preprocess prescription image to enhance OCR accuracy
    
    Args:
        image_file: File object containing the prescription image
        is_handwritten: Boolean indicating if prescription is handwritten
        
    Returns:
        Preprocessed image as numpy array
    """
    try:
        # Read image
        image_bytes = image_file.read()
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply enhanced preprocessing for handwritten text
        if is_handwritten:
            # Apply more aggressive denoising for handwritten text
            denoised = cv2.fastNlMeansDenoising(gray, None, 15, 7, 21)
            
            # Apply bilateral filter to preserve edges while removing noise
            bilateral = cv2.bilateralFilter(denoised, 9, 75, 75)
            
            # Apply Otsu's thresholding for better binarization of handwriting
            _, threshold = cv2.threshold(bilateral, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Apply morphological operations to improve character connectivity
            kernel = np.ones((2, 2), np.uint8)
            morph = cv2.morphologyEx(threshold, cv2.MORPH_CLOSE, kernel)
            
            # Detect and correct skew
            coords = np.column_stack(np.where(morph > 0))
            if len(coords) > 0:  # Check if we have any foreground pixels
                angle = cv2.minAreaRect(coords)[-1]
                
                if angle < -45:
                    angle = -(90 + angle)
                else:
                    angle = -angle
                    
                # Rotate if needed
                if abs(angle) > 0.5:
                    (h, w) = morph.shape[:2]
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, angle, 1.0)
                    processed = cv2.warpAffine(
                        morph, M, (w, h), 
                        flags=cv2.INTER_CUBIC, 
                        borderMode=cv2.BORDER_REPLICATE
                    )
                else:
                    processed = morph
            else:
                processed = morph
                
        else:
            # Standard processing for printed text
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
            
            # Apply adaptive thresholding
            threshold = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # Detect and correct skew
            coords = np.column_stack(np.where(threshold > 0))
            if len(coords) > 0:  # Check if we have any foreground pixels
                angle = cv2.minAreaRect(coords)[-1]
                
                if angle < -45:
                    angle = -(90 + angle)
                else:
                    angle = -angle
                    
                # Rotate if needed
                if abs(angle) > 0.5:
                    (h, w) = threshold.shape[:2]
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, angle, 1.0)
                    rotated = cv2.warpAffine(
                        threshold, M, (w, h), 
                        flags=cv2.INTER_CUBIC, 
                        borderMode=cv2.BORDER_REPLICATE
                    )
                else:
                    rotated = threshold
            else:
                rotated = threshold
                
            # Apply contrast enhancement
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            processed = clahe.apply(rotated)
            
        return processed
        
    except Exception as e:
        logger.error(f"Image preprocessing error: {str(e)}")
        raise

def detect_prescription_type(image):
    """
    Detect if a prescription is handwritten or printed
    
    Args:
        image: Image as numpy array
        
    Returns:
        Boolean: True if handwritten, False if printed
    """
    try:
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Calculate standard deviation of pixel values as a measure of complexity
        std_dev = np.std(gray)
        
        # Apply Canny edge detection
        edges = cv2.Canny(gray, 100, 200)
        
        # Count the number of edge pixels
        edge_count = np.count_nonzero(edges)
        
        # Calculate edge density
        edge_density = edge_count / (gray.shape[0] * gray.shape[1])
        
        # Handwritten prescriptions typically have higher edge density and std_dev
        return edge_density > 0.1 and std_dev > 50
        
    except Exception as e:
        logger.error(f"Prescription type detection error: {str(e)}")
        # Default to printed if error occurs
        return False