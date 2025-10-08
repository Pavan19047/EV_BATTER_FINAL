# src/models/train.py - ML Training Pipeline for EV Battery Predictions
"""
Trains machine learning models for:
1. RUL (Remaining Useful Life) prediction - Regression
2. Failure probability prediction - Regression/Classification

Tracks experiments with MLflow and saves models to local filesystem.

Usage:
    python train.py
"""

import json
import logging
import os
from datetime import datetime
from typing import Tuple

import joblib
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logging.warning("XGBoost not available, using RandomForest instead")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_synthetic_dataset(n_samples: int = 5000) -> pd.DataFrame:
    """
    Generate synthetic EV battery telemetry dataset for training.
    
    Args:
        n_samples: Number of samples to generate
        
    Returns:
        DataFrame with telemetry features and target variables
    """
    logger.info(f"Generating synthetic dataset with {n_samples} samples")
    
    np.random.seed(42)
    
    # Generate realistic EV battery data
    cycles = np.arange(n_samples)
    
    # State of Charge (SOC) - varies with usage
    soc = 100 - (cycles / 10) + np.random.normal(0, 10, n_samples)
    soc = np.clip(soc, 10, 100)
    
    # State of Health (SOH) - degrades over cycles
    soh = 100 - (cycles * 0.01) + np.random.normal(0, 2, n_samples)
    soh = np.clip(soh, 60, 100)
    
    # Battery voltage correlates with SOC
    battery_voltage = 350 + (soc / 100) * 50 + np.random.normal(0, 5, n_samples)
    
    # Battery current (negative = discharge, positive = charge)
    battery_current = np.random.normal(-20, 40, n_samples)
    
    # Battery temperature increases with usage and low SOH
    battery_temperature = 20 + (100 - soc) * 0.1 + (100 - soh) * 0.2 + np.random.normal(0, 5, n_samples)
    battery_temperature = np.clip(battery_temperature, 15, 60)
    
    # Motor metrics
    driving_speed = np.random.uniform(0, 120, n_samples)
    motor_temperature = 40 + (driving_speed / 120) * 40 + np.random.normal(0, 5, n_samples)
    motor_vibration = 0.3 + (driving_speed / 120) * 0.7 + np.random.normal(0, 0.1, n_samples)
    
    # Power consumption
    power_consumption = (driving_speed / 120) * 50 + np.random.uniform(5, 15, n_samples)
    
    # Distance traveled
    distance_traveled = cycles * 0.5 + np.random.normal(0, 50, n_samples)
    distance_traveled = np.maximum(0, distance_traveled)
    
    # Target variables
    # RUL: Remaining Useful Life in cycles (decreases as SOH decreases)
    rul = (soh - 60) * 25 + np.random.normal(0, 50, n_samples)  # Max ~1000 cycles at 100% SOH
    rul = np.clip(rul, 0, 1000)
    
    # Failure probability increases as SOH decreases and temperature rises
    failure_probability = (100 - soh) / 100 * 0.5 + (battery_temperature - 20) / 60 * 0.3
    failure_probability += np.random.normal(0, 0.1, n_samples)
    failure_probability = np.clip(failure_probability, 0, 1)
    
    # Create DataFrame
    df = pd.DataFrame({
        'soc': soc,
        'soh': soh,
        'battery_voltage': battery_voltage,
        'battery_current': battery_current,
        'battery_temperature': battery_temperature,
        'motor_temperature': motor_temperature,
        'motor_vibration': motor_vibration,
        'power_consumption': power_consumption,
        'driving_speed': driving_speed,
        'distance_traveled': distance_traveled,
        'rul': rul,
        'failure_probability': failure_probability
    })
    
    logger.info(f"Generated dataset shape: {df.shape}")
    logger.info(f"RUL range: [{df['rul'].min():.1f}, {df['rul'].max():.1f}]")
    logger.info(f"Failure probability range: [{df['failure_probability'].min():.3f}, {df['failure_probability'].max():.3f}]")
    
    return df


def prepare_data(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, 
                                             np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Prepare training and test datasets.
    
    Args:
        df: Input DataFrame
        
    Returns:
        Tuple of (X_train_rul, X_test_rul, y_train_rul, y_test_rul,
                  X_train_fail, X_test_fail, y_train_fail, y_test_fail)
    """
    # Feature columns
    feature_cols = [
        'soc', 'soh', 'battery_voltage', 'battery_current',
        'battery_temperature', 'motor_temperature', 'motor_vibration',
        'power_consumption', 'driving_speed', 'distance_traveled'
    ]
    
    X = df[feature_cols].values
    y_rul = df['rul'].values
    y_failure = df['failure_probability'].values
    
    # Split for RUL prediction
    X_train_rul, X_test_rul, y_train_rul, y_test_rul = train_test_split(
        X, y_rul, test_size=0.2, random_state=42
    )
    
    # Split for failure prediction
    X_train_fail, X_test_fail, y_train_fail, y_test_fail = train_test_split(
        X, y_failure, test_size=0.2, random_state=42
    )
    
    logger.info(f"Training set size: {X_train_rul.shape[0]}")
    logger.info(f"Test set size: {X_test_rul.shape[0]}")
    
    return (X_train_rul, X_test_rul, y_train_rul, y_test_rul,
            X_train_fail, X_test_fail, y_train_fail, y_test_fail)


def train_rul_model(X_train: np.ndarray, y_train: np.ndarray,
                    X_test: np.ndarray, y_test: np.ndarray) -> object:
    """
    Train RUL (Remaining Useful Life) prediction model.
    
    Args:
        X_train, y_train: Training data
        X_test, y_test: Test data
        
    Returns:
        Trained model
    """
    logger.info("Training RUL prediction model...")
    
    if XGBOOST_AVAILABLE:
        model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            n_jobs=-1
        )
        model_type = "XGBoost"
    else:
        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        model_type = "RandomForest"
    
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    
    logger.info(f"RUL Model ({model_type}) Performance:")
    logger.info(f"  MAE: {mae:.2f}")
    logger.info(f"  RMSE: {rmse:.2f}")
    logger.info(f"  R²: {r2:.4f}")
    
    # Log to MLflow
    mlflow.log_metric("rul_mae", mae)
    mlflow.log_metric("rul_rmse", rmse)
    mlflow.log_metric("rul_r2", r2)
    
    return model


def train_failure_model(X_train: np.ndarray, y_train: np.ndarray,
                       X_test: np.ndarray, y_test: np.ndarray) -> object:
    """
    Train failure probability prediction model.
    
    Args:
        X_train, y_train: Training data
        X_test, y_test: Test data
        
    Returns:
        Trained model
    """
    logger.info("Training failure probability prediction model...")
    
    if XGBOOST_AVAILABLE:
        model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42,
            n_jobs=-1
        )
        model_type = "XGBoost"
    else:
        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=8,
            random_state=42,
            n_jobs=-1
        )
        model_type = "RandomForest"
    
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    # Clip predictions to [0, 1] range
    y_pred = np.clip(y_pred, 0, 1)
    
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    
    logger.info(f"Failure Model ({model_type}) Performance:")
    logger.info(f"  MAE: {mae:.4f}")
    logger.info(f"  RMSE: {rmse:.4f}")
    logger.info(f"  R²: {r2:.4f}")
    
    # Log to MLflow
    mlflow.log_metric("failure_mae", mae)
    mlflow.log_metric("failure_rmse", rmse)
    mlflow.log_metric("failure_r2", r2)
    
    return model


def save_models(rul_model: object, failure_model: object, output_dir: str = 'models'):
    """
    Save trained models to disk.
    
    Args:
        rul_model: Trained RUL model
        failure_model: Trained failure model
        output_dir: Directory to save models
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Save models as joblib
    rul_path = os.path.join(output_dir, 'rul_xgb_model.joblib')
    failure_path = os.path.join(output_dir, 'failure_xgb_model.joblib')
    
    joblib.dump(rul_model, rul_path)
    joblib.dump(failure_model, failure_path)
    
    logger.info(f"Saved RUL model to {rul_path}")
    logger.info(f"Saved failure model to {failure_path}")
    
    # Save metadata
    rul_meta = {
        'model_type': 'XGBoost' if XGBOOST_AVAILABLE else 'RandomForest',
        'target': 'rul',
        'created_at': datetime.now().isoformat(),
        'feature_names': [
            'soc', 'soh', 'battery_voltage', 'battery_current',
            'battery_temperature', 'motor_temperature', 'motor_vibration',
            'power_consumption', 'driving_speed', 'distance_traveled'
        ]
    }
    
    failure_meta = {
        'model_type': 'XGBoost' if XGBOOST_AVAILABLE else 'RandomForest',
        'target': 'failure_probability',
        'created_at': datetime.now().isoformat(),
        'feature_names': [
            'soc', 'soh', 'battery_voltage', 'battery_current',
            'battery_temperature', 'motor_temperature', 'motor_vibration',
            'power_consumption', 'driving_speed', 'distance_traveled'
        ]
    }
    
    with open(os.path.join(output_dir, 'rul_meta.json'), 'w') as f:
        json.dump(rul_meta, f, indent=2)
    
    with open(os.path.join(output_dir, 'failure_meta.json'), 'w') as f:
        json.dump(failure_meta, f, indent=2)
    
    logger.info("Saved model metadata")
    
    # Log to MLflow
    mlflow.sklearn.log_model(rul_model, "rul_model")
    mlflow.sklearn.log_model(failure_model, "failure_model")
    mlflow.log_artifact(os.path.join(output_dir, 'rul_meta.json'))
    mlflow.log_artifact(os.path.join(output_dir, 'failure_meta.json'))


def main():
    """Main training pipeline."""
    logger.info("Starting EV Battery ML Training Pipeline")
    
    # Set up MLflow with proper Windows path handling
    mlflow_tracking_uri = os.getenv('MLFLOW_TRACKING_URI')
    if not mlflow_tracking_uri:
        # Use absolute path for Windows compatibility
        mlruns_path = os.path.abspath('./mlruns')
        mlflow_tracking_uri = f'file:///{mlruns_path.replace(os.sep, "/")}'
    
    mlflow.set_tracking_uri(mlflow_tracking_uri)
    mlflow.set_experiment("ev_battery_predictions")
    
    logger.info(f"MLflow tracking URI: {mlflow_tracking_uri}")
    
    # Start MLflow run
    with mlflow.start_run(run_name=f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
        # Log parameters
        mlflow.log_param("dataset_type", "synthetic")
        mlflow.log_param("n_samples", 5000)
        mlflow.log_param("test_size", 0.2)
        mlflow.log_param("model_framework", "XGBoost" if XGBOOST_AVAILABLE else "RandomForest")
        
        # Generate dataset
        df = generate_synthetic_dataset(n_samples=5000)
        
        # Prepare data
        (X_train_rul, X_test_rul, y_train_rul, y_test_rul,
         X_train_fail, X_test_fail, y_train_fail, y_test_fail) = prepare_data(df)
        
        # Train models
        rul_model = train_rul_model(X_train_rul, y_train_rul, X_test_rul, y_test_rul)
        failure_model = train_failure_model(X_train_fail, y_train_fail, X_test_fail, y_test_fail)
        
        # Save models
        save_models(rul_model, failure_model)
        
        logger.info("Training completed successfully")
        logger.info(f"MLflow run ID: {mlflow.active_run().info.run_id}")
    
    logger.info("\nTo view MLflow UI, run:")
    logger.info("  mlflow ui --backend-store-uri file://./mlruns")


if __name__ == '__main__':
    main()
