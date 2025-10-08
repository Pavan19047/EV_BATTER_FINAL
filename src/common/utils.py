# src/common/utils.py - Shared Utility Functions
"""
Common utilities used across the EV Digital Twin project.
"""

import logging
from typing import Dict, List
import numpy as np

logger = logging.getLogger(__name__)


def extract_features(telemetry: Dict) -> np.ndarray:
    """
    Extract feature vector from telemetry dictionary.
    
    Args:
        telemetry: Dictionary containing telemetry fields
        
    Returns:
        numpy array with shape (1, n_features) ready for model prediction
    """
    # Define feature order (must match training data)
    feature_names = [
        'soc',
        'soh',
        'battery_voltage',
        'battery_current',
        'battery_temperature',
        'motor_temperature',
        'motor_vibration',
        'power_consumption',
        'driving_speed',
        'distance_traveled'
    ]
    
    # Extract values in correct order with defaults
    features = []
    for name in feature_names:
        value = telemetry.get(name, 0.0)
        # Handle None values
        if value is None:
            value = 0.0
        features.append(float(value))
    
    # Return as 2D array (1 sample, n features)
    return np.array([features])


def validate_telemetry(telemetry: Dict) -> bool:
    """
    Validate that telemetry contains required fields with reasonable values.
    
    Args:
        telemetry: Dictionary containing telemetry fields
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = [
        'soc', 'soh', 'battery_voltage', 'battery_current',
        'battery_temperature', 'motor_temperature', 'motor_vibration',
        'power_consumption', 'driving_speed', 'distance_traveled'
    ]
    
    # Check all required fields exist
    for field in required_fields:
        if field not in telemetry:
            logger.warning(f"Missing required field: {field}")
            return False
    
    # Validate ranges
    validations = {
        'soc': (0, 100),
        'soh': (0, 100),
        'battery_voltage': (200, 500),
        'battery_temperature': (-20, 80),
        'motor_temperature': (0, 150),
        'driving_speed': (0, 200)
    }
    
    for field, (min_val, max_val) in validations.items():
        value = telemetry.get(field)
        if value is not None and not (min_val <= value <= max_val):
            logger.warning(f"Field {field} value {value} out of range [{min_val}, {max_val}]")
            return False
    
    return True


def calculate_health_score(telemetry: Dict) -> float:
    """
    Calculate overall battery health score (0-100).
    
    Args:
        telemetry: Dictionary containing telemetry fields
        
    Returns:
        Health score between 0 and 100
    """
    soh = telemetry.get('soh', 100)
    battery_temp = telemetry.get('battery_temperature', 25)
    
    # Base score from SOH
    score = soh
    
    # Penalize high temperatures
    if battery_temp > 45:
        temp_penalty = (battery_temp - 45) * 2
        score -= temp_penalty
    
    # Penalize low SOC
    soc = telemetry.get('soc', 100)
    if soc < 20:
        soc_penalty = (20 - soc) * 0.5
        score -= soc_penalty
    
    # Ensure score is in valid range
    return max(0, min(100, score))


def format_prediction_message(telemetry: Dict, rul: float, failure_prob: float) -> Dict:
    """
    Format prediction results into a standardized message.
    
    Args:
        telemetry: Original telemetry data
        rul: Remaining Useful Life prediction
        failure_prob: Failure probability prediction
        
    Returns:
        Dictionary with formatted prediction message
    """
    health_score = calculate_health_score(telemetry)
    
    # Determine severity level
    if failure_prob > 0.7 or rul < 100:
        severity = "critical"
    elif failure_prob > 0.4 or rul < 300:
        severity = "warning"
    else:
        severity = "normal"
    
    message = {
        'timestamp': telemetry.get('ts'),
        'predictions': {
            'rul': round(rul, 1),
            'failure_probability': round(failure_prob, 4),
            'health_score': round(health_score, 1)
        },
        'telemetry': {
            'soc': telemetry.get('soc'),
            'soh': telemetry.get('soh'),
            'battery_temperature': telemetry.get('battery_temperature')
        },
        'severity': severity
    }
    
    return message


def get_feature_names() -> List[str]:
    """
    Get the ordered list of feature names used in models.
    
    Returns:
        List of feature names
    """
    return [
        'soc',
        'soh',
        'battery_voltage',
        'battery_current',
        'battery_temperature',
        'motor_temperature',
        'motor_vibration',
        'power_consumption',
        'driving_speed',
        'distance_traveled'
    ]


def parse_pg_connection_string(conn_string: str) -> Dict[str, str]:
    """
    Parse PostgreSQL connection string into components.
    
    Args:
        conn_string: Connection string like "host=localhost port=5432 ..."
        
    Returns:
        Dictionary with connection parameters
    """
    params = {}
    for part in conn_string.split():
        if '=' in part:
            key, value = part.split('=', 1)
            params[key] = value
    return params
