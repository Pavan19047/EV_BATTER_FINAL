# tests/test_smoke.py - Smoke Tests for EV Digital Twin
"""
Basic smoke tests to verify core functionality.
"""

import os
import sys
import unittest
import tempfile
import numpy as np

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.common.utils import (
    extract_features,
    validate_telemetry,
    calculate_health_score,
    format_prediction_message,
    get_feature_names
)


class TestCommonUtils(unittest.TestCase):
    """Test common utility functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.valid_telemetry = {
            'ts': '2024-01-01T00:00:00',
            'soc': 85.0,
            'soh': 95.0,
            'battery_voltage': 380.0,
            'battery_current': -25.0,
            'battery_temperature': 28.5,
            'motor_temperature': 65.0,
            'motor_vibration': 0.45,
            'power_consumption': 35.0,
            'driving_speed': 80.0,
            'distance_traveled': 15000.0
        }
    
    def test_extract_features_shape(self):
        """Test that extract_features returns correct shape."""
        features = extract_features(self.valid_telemetry)
        
        # Should return (1, 10) array
        self.assertEqual(features.shape, (1, 10))
        self.assertIsInstance(features, np.ndarray)
    
    def test_extract_features_values(self):
        """Test that extract_features returns correct values."""
        features = extract_features(self.valid_telemetry)
        
        # First few values should match input
        self.assertAlmostEqual(features[0, 0], 85.0)  # soc
        self.assertAlmostEqual(features[0, 1], 95.0)  # soh
        self.assertAlmostEqual(features[0, 2], 380.0)  # battery_voltage
    
    def test_extract_features_missing_values(self):
        """Test extract_features with missing values."""
        incomplete_telemetry = {'soc': 75.0, 'soh': 90.0}
        features = extract_features(incomplete_telemetry)
        
        # Should still return correct shape with defaults
        self.assertEqual(features.shape, (1, 10))
        self.assertAlmostEqual(features[0, 0], 75.0)  # soc
        self.assertAlmostEqual(features[0, 1], 90.0)  # soh
        self.assertAlmostEqual(features[0, 2], 0.0)   # default for missing
    
    def test_validate_telemetry_valid(self):
        """Test validation with valid telemetry."""
        self.assertTrue(validate_telemetry(self.valid_telemetry))
    
    def test_validate_telemetry_missing_field(self):
        """Test validation with missing required field."""
        invalid_telemetry = self.valid_telemetry.copy()
        del invalid_telemetry['soc']
        
        self.assertFalse(validate_telemetry(invalid_telemetry))
    
    def test_validate_telemetry_out_of_range(self):
        """Test validation with out-of-range values."""
        invalid_telemetry = self.valid_telemetry.copy()
        invalid_telemetry['soc'] = 150.0  # Invalid SOC
        
        self.assertFalse(validate_telemetry(invalid_telemetry))
    
    def test_calculate_health_score(self):
        """Test health score calculation."""
        score = calculate_health_score(self.valid_telemetry)
        
        # Should be between 0 and 100
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
        
        # With good values, should be high
        self.assertGreater(score, 80)
    
    def test_calculate_health_score_degraded(self):
        """Test health score with degraded battery."""
        degraded_telemetry = self.valid_telemetry.copy()
        degraded_telemetry['soh'] = 70.0
        degraded_telemetry['battery_temperature'] = 55.0
        
        score = calculate_health_score(degraded_telemetry)
        
        # Should be lower than healthy battery
        healthy_score = calculate_health_score(self.valid_telemetry)
        self.assertLess(score, healthy_score)
    
    def test_format_prediction_message(self):
        """Test prediction message formatting."""
        rul = 650.0
        failure_prob = 0.15
        
        message = format_prediction_message(self.valid_telemetry, rul, failure_prob)
        
        # Check structure
        self.assertIn('predictions', message)
        self.assertIn('telemetry', message)
        self.assertIn('severity', message)
        
        # Check values
        self.assertEqual(message['predictions']['rul'], 650.0)
        self.assertEqual(message['predictions']['failure_probability'], 0.15)
        self.assertEqual(message['severity'], 'normal')
    
    def test_format_prediction_message_critical(self):
        """Test prediction message with critical values."""
        rul = 50.0
        failure_prob = 0.85
        
        message = format_prediction_message(self.valid_telemetry, rul, failure_prob)
        
        # Should be marked as critical
        self.assertEqual(message['severity'], 'critical')
    
    def test_get_feature_names(self):
        """Test feature names retrieval."""
        names = get_feature_names()
        
        # Should have 10 features
        self.assertEqual(len(names), 10)
        
        # Should include key features
        self.assertIn('soc', names)
        self.assertIn('soh', names)
        self.assertIn('battery_voltage', names)


class TestModelLoading(unittest.TestCase):
    """Test model loading functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary model files for testing
        self.temp_dir = tempfile.mkdtemp()
        
        # Create dummy models using joblib
        import joblib
        from sklearn.ensemble import RandomForestRegressor
        
        dummy_model = RandomForestRegressor(n_estimators=2, max_depth=2, random_state=42)
        X_dummy = np.random.rand(10, 10)
        y_dummy = np.random.rand(10)
        dummy_model.fit(X_dummy, y_dummy)
        
        self.rul_model_path = os.path.join(self.temp_dir, 'rul_xgb_model.joblib')
        self.failure_model_path = os.path.join(self.temp_dir, 'failure_xgb_model.joblib')
        
        joblib.dump(dummy_model, self.rul_model_path)
        joblib.dump(dummy_model, self.failure_model_path)
    
    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_model_files_exist(self):
        """Test that model files can be created and exist."""
        self.assertTrue(os.path.exists(self.rul_model_path))
        self.assertTrue(os.path.exists(self.failure_model_path))
    
    def test_model_loading(self):
        """Test loading models from disk."""
        import joblib
        
        rul_model = joblib.load(self.rul_model_path)
        failure_model = joblib.load(self.failure_model_path)
        
        # Models should be loadable
        self.assertIsNotNone(rul_model)
        self.assertIsNotNone(failure_model)
        
        # Models should be able to predict
        X_test = np.random.rand(1, 10)
        rul_pred = rul_model.predict(X_test)
        failure_pred = failure_model.predict(X_test)
        
        self.assertEqual(rul_pred.shape, (1,))
        self.assertEqual(failure_pred.shape, (1,))
    
    def test_model_prediction_with_telemetry(self):
        """Test end-to-end: extract features and predict."""
        import joblib
        
        model = joblib.load(self.rul_model_path)
        
        telemetry = {
            'soc': 85.0,
            'soh': 95.0,
            'battery_voltage': 380.0,
            'battery_current': -25.0,
            'battery_temperature': 28.5,
            'motor_temperature': 65.0,
            'motor_vibration': 0.45,
            'power_consumption': 35.0,
            'driving_speed': 80.0,
            'distance_traveled': 15000.0
        }
        
        # Extract features
        features = extract_features(telemetry)
        
        # Make prediction
        prediction = model.predict(features)
        
        # Should return a single value
        self.assertEqual(prediction.shape, (1,))
        self.assertIsInstance(float(prediction[0]), float)


class TestDataGeneration(unittest.TestCase):
    """Test synthetic data generation."""
    
    def test_import_train_module(self):
        """Test that train module can be imported."""
        try:
            from src.models import train
            self.assertTrue(hasattr(train, 'generate_synthetic_dataset'))
        except ImportError as e:
            self.fail(f"Failed to import train module: {e}")
    
    def test_generate_synthetic_dataset(self):
        """Test synthetic dataset generation."""
        from src.models.train import generate_synthetic_dataset
        
        df = generate_synthetic_dataset(n_samples=100)
        
        # Check shape
        self.assertEqual(len(df), 100)
        
        # Check columns exist
        required_cols = ['soc', 'soh', 'rul', 'failure_probability']
        for col in required_cols:
            self.assertIn(col, df.columns)
        
        # Check value ranges
        self.assertTrue((df['soc'] >= 0).all() and (df['soc'] <= 100).all())
        self.assertTrue((df['soh'] >= 0).all() and (df['soh'] <= 100).all())
        self.assertTrue((df['failure_probability'] >= 0).all() and (df['failure_probability'] <= 1).all())


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestCommonUtils))
    suite.addTests(loader.loadTestsFromTestCase(TestModelLoading))
    suite.addTests(loader.loadTestsFromTestCase(TestDataGeneration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
