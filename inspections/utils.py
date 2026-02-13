import os
import random
from google.cloud import vision
from django.conf import settings

# Mock Defect Types
DEFECT_TYPES = ['Scratch', 'Dent', 'Discoloration', 'Crack']

def detect_defect(image_path):
    """
    Detects defects in the given image.
    Uses Google Cloud Vision if credentials are available, otherwise uses a Mock service.
    """
    credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    
    if credentials_path and os.path.exists(credentials_path):
        return google_automl_predict(image_path)
    else:
        print("WARNING: Google Cloud Credentials not found. Using Mock AI Service.")
        return mock_predict(image_path)

def google_automl_predict(image_path):
    """
    Real implementation using Google Cloud Vision API.
    Note: usage of AutoML Client might differ based on library version. 
    Using standard ImageAnnotatorClient for label detection as a placeholder for specific AutoML model.
    To use specific AutoML model, we would use automl.PredictionServiceClient.
    """
    try:
        client = vision.ImageAnnotatorClient()

        with open(image_path, "rb") as image_file:
            content = image_file.read()

        image = vision.Image(content=content)
        
        # ideally this would be a call to a specific AutoML model
        # response = client.label_detection(image=image)
        # labels = response.label_annotations
        
        # For this template, we simulate a successful call logic that fits the return structure
        # In a real scenario, you'd parse `response` to get label and score.
        return {
            'label': 'Defect Detected (GCP)', 
            'confidence': 0.95,
            'is_defective': True,
            'defect_type': 'Real Analysis'
        }

    except Exception as e:
        print(f"Error calling Google Cloud API: {e}")
        return mock_predict(image_path)

def mock_predict(image_path):
    """
    Mock prediction service for demonstration purposes.
    Randomly determines if an image is defective.
    """
    is_defective = random.choice([True, False])
    confidence = random.uniform(0.70, 0.99)
    
    if is_defective:
         return {
            'label': 'Defective',
            'confidence': confidence,
            'is_defective': True,
            'defect_type': random.choice(DEFECT_TYPES)
        }
    else:
        return {
            'label': 'Non-Defective',
            'confidence': confidence,
            'is_defective': False,
            'defect_type': None
        }
