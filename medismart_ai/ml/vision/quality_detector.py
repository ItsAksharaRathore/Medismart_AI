import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
from utils.logger import get_logger

logger = get_logger(__name__)

class ImageQualityDetector:
    """Assesses the quality of prescription images"""
    
    def __init__(self):
        self.blur_threshold = 100  # Laplacian variance threshold for blur detection
        self.brightness_min = 40   # Minimum acceptable brightness
        self.brightness_max = 240  # Maximum acceptable brightness
        self.contrast_threshold = 50  # Minimum acceptable contrast
        
    def assess_quality(self, image):
        """
        Assess the quality of an image
        
        Args:
            image: Input image (BGR format)
            
        Returns:
            dict: Quality assessment results
        """
        try:
            # Convert image to grayscale if it's not
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
                
            # Calculate blur score
            blur_score = self._detect_blur(gray)
            
            # Calculate brightness and contrast
            brightness = self._calculate_brightness(gray)
            contrast = self._calculate_contrast(gray)
            
            # Check if image is too dark or too bright
            is_too_dark = brightness < self.brightness_min
            is_too_bright = brightness > self.brightness_max
            
            # Check if contrast is too low
            is_low_contrast = contrast < self.contrast_threshold
            
            # Check if image is blurry
            is_blurry = blur_score < self.blur_threshold
            
            # Overall assessment
            is_good_quality = not (is_blurry or is_too_dark or 
                                  is_too_bright or is_low_contrast)
            
            result = {
                'is_good_quality': is_good_quality,
                'blur_score': blur_score,
                'is_blurry': is_blurry,
                'brightness': brightness,
                'is_too_dark': is_too_dark,
                'is_too_bright': is_too_bright,
                'contrast': contrast,
                'is_low_contrast': is_low_contrast
            }
            
            logger.debug(f"Image quality assessment: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error in quality assessment: {str(e)}")
            return {'error': str(e)}
            
    def _detect_blur(self, image):
        """
        Detect if an image is blurry using Laplacian variance
        
        Args:
            image: Grayscale image
            
        Returns:
            float: Blur score (higher is better/sharper)
        """
        # Calculate Laplacian variance
        laplacian = cv2.Laplacian(image, cv2.CV_64F)
        score = np.var(laplacian)
        return score
        
    def _calculate_brightness(self, image):
        """
        Calculate the brightness of an image
        
        Args:
            image: Grayscale image
            
        Returns:
            float: Average brightness value
        """
        return np.mean(image)
        
    def _calculate_contrast(self, image):
        """
        Calculate the contrast of an image
        
        Args:
            image: Grayscale image
            
        Returns:
            float: Contrast value
        """
        return np.std(image.astype(float))
        
    def enhance_image(self, image):
        """
        Enhance image quality for better recognition
        
        Args:
            image: Input image
            
        Returns:
            Enhanced image
        """
        try:
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
                
            # Assess quality
            quality = self.assess_quality(gray)
            
            # Apply appropriate enhancements
            enhanced = gray.copy()
            
            # Adjust brightness if needed
            if quality['is_too_dark']:
                enhanced = cv2.convertScaleAbs(enhanced, alpha=1.5, beta=30)
            elif quality['is_too_bright']:
                enhanced = cv2.convertScaleAbs(enhanced, alpha=0.8, beta=-10)
                
            # Enhance contrast if needed
            if quality['is_low_contrast']:
                # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(enhanced)
                
            # Apply deblurring if needed
            if quality['is_blurry']:
                # Use unsharp masking to sharpen the image
                gaussian = cv2.GaussianBlur(enhanced, (0, 0), 3)
                enhanced = cv2.addWeighted(enhanced, 1.5, gaussian, -0.5, 0)
                
            return enhanced
            
        except Exception as e:
            logger.error(f"Error enhancing image: {str(e)}")
            return image  # Return original image on error
            
    def compare_images(self, image1, image2):
        """
        Compare two images for similarity
        
        Args:
            image1: First image
            image2: Second image
            
        Returns:
            float: Similarity score (0-1, higher is more similar)
        """
        try:
            # Convert to grayscale if needed
            if len(image1.shape) == 3:
                gray1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)
            else:
                gray1 = image1.copy()
                
            if len(image2.shape) == 3:
                gray2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY)
            else:
                gray2 = image2.copy()
                
            # Resize images to the same dimensions if needed
            if gray1.shape != gray2.shape:
                gray2 = cv2.resize(gray2, (gray1.shape[1], gray1.shape[0]))
                
            # Calculate SSIM between the images
            score, _ = ssim(gray1, gray2, full=True)
            return score
            
        except Exception as e:
            logger.error(f"Error comparing images: {str(e)}")
            return -1  # Return negative value to indicate error