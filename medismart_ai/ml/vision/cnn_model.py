import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from utils.logger import get_logger

logger = get_logger(__name__)

class HandwritingRecognitionModel:
    """CNN model for handwriting recognition in medical prescriptions"""
    
    def __init__(self, input_shape=(224, 224, 3), num_classes=62):
        """
        Initialize the CNN model
        
        Args:
            input_shape: Shape of input images (height, width, channels)
            num_classes: Number of output classes (letters, numbers, symbols)
        """
        self.input_shape = input_shape
        self.num_classes = num_classes
        self.model = None
        
    def build_model(self, use_pretrained=True):
        """
        Build the CNN model architecture
        
        Args:
            use_pretrained: Whether to use pretrained MobileNetV2 as base
        """
        try:
            if use_pretrained:
                # Use MobileNetV2 as base model for transfer learning
                base_model = MobileNetV2(
                    input_shape=self.input_shape,
                    include_top=False,
                    weights='imagenet'
                )
                
                # Freeze the base model layers
                base_model.trainable = False
                
                # Build the model
                model = models.Sequential([
                    base_model,
                    layers.GlobalAveragePooling2D(),
                    layers.Dropout(0.2),
                    layers.Dense(512, activation='relu'),
                    layers.BatchNormalization(),
                    layers.Dropout(0.5),
                    layers.Dense(self.num_classes, activation='softmax')
                ])
            else:
                # Build a custom CNN from scratch
                model = models.Sequential([
                    layers.Conv2D(32, (3, 3), activation='relu', input_shape=self.input_shape),
                    layers.MaxPooling2D((2, 2)),
                    layers.Conv2D(64, (3, 3), activation='relu'),
                    layers.MaxPooling2D((2, 2)),
                    layers.Conv2D(128, (3, 3), activation='relu'),
                    layers.MaxPooling2D((2, 2)),
                    layers.Conv2D(128, (3, 3), activation='relu'),
                    layers.MaxPooling2D((2, 2)),
                    layers.Flatten(),
                    layers.Dropout(0.5),
                    layers.Dense(512, activation='relu'),
                    layers.Dense(self.num_classes, activation='softmax')
                ])
                
            # Compile the model
            model.compile(
                optimizer='adam',
                loss='sparse_categorical_crossentropy',
                metrics=['accuracy']
            )
            
            self.model = model
            logger.info("CNN model for handwriting recognition built successfully")
            return model
            
        except Exception as e:
            logger.error(f"Failed to build CNN model: {str(e)}")
            raise
            
    def train(self, train_data_dir, val_data_dir, batch_size=32, epochs=10):
        """
        Train the CNN model
        
        Args:
            train_data_dir: Directory with training data
            val_data_dir: Directory with validation data
            batch_size: Batch size for training
            epochs: Number of epochs to train
            
        Returns:
            Training history
        """
        if self.model is None:
            self.build_model()
            
        # Data augmentation for training
        train_datagen = ImageDataGenerator(
            rescale=1./255,
            rotation_range=15,
            width_shift_range=0.1,
            height_shift_range=0.1,
            shear_range=0.1,
            zoom_range=0.1,
            horizontal_flip=False,
            fill_mode='nearest'
        )
        
        # Only rescaling for validation
        val_datagen = ImageDataGenerator(rescale=1./255)
        
        # Create data generators
        train_generator = train_datagen.flow_from_directory(
            train_data_dir,
            target_size=(self.input_shape[0], self.input_shape[1]),
            batch_size=batch_size,
            class_mode='sparse'
        )
        
        validation_generator = val_datagen.flow_from_directory(
            val_data_dir,
            target_size=(self.input_shape[0], self.input_shape[1]),
            batch_size=batch_size,
            class_mode='sparse'
        )
        
        # Train the model
        history = self.model.fit(
            train_generator,
            steps_per_epoch=train_generator.samples // batch_size,
            epochs=epochs,
            validation_data=validation_generator,
            validation_steps=validation_generator.samples // batch_size
        )
        
        logger.info(f"Model training completed. Final validation accuracy: {history.history['val_accuracy'][-1]:.4f}")
        return history
        
    def predict(self, image):
        """
        Predict the text in an image
        
        Args:
            image: Preprocessed image (224x224x3)
            
        Returns:
            Predicted class and confidence
        """
        if self.model is None:
            logger.error("Model not built or loaded")
            raise ValueError("Model not built or loaded")
            
        # Ensure image has correct shape
        if len(image.shape) == 3:
            image = np.expand_dims(image, axis=0)
            
        # Normalize pixel values
        image = image / 255.0
        
        # Make prediction
        predictions = self.model.predict(image)
        predicted_class = np.argmax(predictions, axis=1)[0]
        confidence = predictions[0][predicted_class]
        
        return predicted_class, confidence
        
    def save_model(self, filepath):
        """Save model to file"""
        if self.model is None:
            logger.error("No model to save")
            return False
            
        try:
            self.model.save(filepath)
            logger.info(f"Model saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save model: {str(e)}")
            return False
            
    def load_model(self, filepath):
        """Load model from file"""
        try:
            self.model = models.load_model(filepath)
            logger.info(f"Model loaded from {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            return False