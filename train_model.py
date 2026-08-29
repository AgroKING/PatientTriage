import os
import sqlite3
import pandas as pd
import joblib

import config
from src.database import init_db
from src.data_loader import load_triagegeist, get_training_data
from src.risk_scorer import HybridRiskScorer


def main():
    print("🏥 PatientTriage.ai Model Training CLI")
    print("--------------------------------------")
    
    csv_path = os.path.join("data", "train.csv")
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        print("Please download the Triagegeist dataset from Kaggle and place it in the 'data/' directory.")
        print("See 'data/README.md' for download instructions.")
        return

    # Connect/init DB
    print(f"Connecting to database at: {config.DB_PATH}")
    conn = init_db(config.DB_PATH)

    # Load data
    limit = 10000
    print(f"Loading first {limit} records from {csv_path} into SQLite database...")
    try:
        count = load_triagegeist(conn, csv_path, limit=limit)
        print(f"Success: Loaded {count} patient records.")
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return

    # Extract features
    print("Extracting training features and labels...")
    try:
        X, y = get_training_data(conn)
        print(f"Training set dimensions: {X.shape[0]} samples, {X.shape[1]} features.")
    except Exception as e:
        print(f"Error preparing training data: {e}")
        return

    # Train model
    print("Training Random Forest Classifier (balanced weights, 100 trees)...")
    scorer = HybridRiskScorer()
    try:
        scorer.train(X, y)
        print("Model training complete.")
    except Exception as e:
        print(f"Error training model: {e}")
        return

    # Save model
    print(f"Saving serialized model to: {config.MODEL_PATH}")
    try:
        scorer.save_model(config.MODEL_PATH)
        print("Success: Model saved successfully. Ready for clinical decision support!")
    except Exception as e:
        print(f"Error saving model: {e}")


if __name__ == "__main__":
    main()
