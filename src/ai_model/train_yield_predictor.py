"""
Purpose: AI Model Training Script (Forward Model).
Overview: Trains a RandomForest Regressor to predict reaction yield based on Enzyme Features, Temp, pH, and Substrate Type.
"""
import pandas as pd
import numpy as np
import os
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

def train_yield_predictor():
    print("Training Yield Predictor AI (Phase 7)...")
    
    dataset_path = "data/processed/training_dataset.csv"
    features_path = "data/processed/enzyme_features.csv"
    model_path = "models/yield_predictor.pkl"
    
    if not os.path.exists(dataset_path):
        print("Error: Dataset not found. Wait for generation.")
        return
        
    if not os.path.exists("models"):
        os.makedirs("models")
        
    # Load Data
    df_data = pd.read_csv(dataset_path)
    df_feat = pd.read_csv(features_path)
    
    # Merge: Add features to dataset based on 'id'
    # df_data has 2500 rows (id, temp, ph, yield)
    # df_feat has 100 rows (id, dim_0...dim_19)
    
    df_merged = pd.merge(df_data, df_feat, on='id', how='left')
    
    # Define X and y
    # X = [dim_0...dim_19, temp, ph] + Substrate(OneHot)
    
    # One-Hot Encode 'substrate'
    if 'substrate' in df_merged.columns:
        df_merged = pd.get_dummies(df_merged, columns=['substrate'], prefix='sub')
    
    # Features: dim_*, temp, ph, sub_*
    feature_cols = [c for c in df_merged.columns if c.startswith('dim_') or c.startswith('sub_')] + ['temp', 'ph']
    
    print(f"Features: {feature_cols}")
    
    X = df_merged[feature_cols]
    y = df_merged['yield']
    
    # Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, WhiteKernel
    
    # Subsampling Strategy (GPR is O(N^3))
    # Limit to N=1500
    N_SAMPLE = 1500
    
    if len(X_train) > N_SAMPLE:
        print(f"Subsampling GPR training data from {len(X_train)} to {N_SAMPLE}...")
        # Strategy: Keep Top 20% (High Yields) + Random rest
        # Combine X_train, y_train
        train_df = X_train.copy()
        train_df['target'] = y_train
        
        # Sort by target
        train_df = train_df.sort_values('target', ascending=False)
        
        n_top = int(N_SAMPLE * 0.2)
        n_rand = N_SAMPLE - n_top
        
        df_top = train_df.iloc[:n_top]
        df_rest = train_df.iloc[n_top:]
        
        df_rand = df_rest.sample(n=n_rand, random_state=42)
        
        df_final = pd.concat([df_top, df_rand])
        X_train_sub = df_final.drop('target', axis=1)
        y_train_sub = df_final['target']
    else:
        X_train_sub = X_train
        y_train_sub = y_train

    # Model: Gaussian Process
    # Kernel: RBF (Length scale) + WhiteKernel (Noise)
    kernel = RBF(length_scale=1.0) + WhiteKernel(noise_level=1e-5)
    model = GaussianProcessRegressor(kernel=kernel, alpha=0.0, normalize_y=True, n_restarts_optimizer=2, random_state=42)
    
    print(f"Fitting GPR on {len(X_train_sub)} samples...")
    model.fit(X_train_sub, y_train_sub)
    
    # Evaluate
    y_pred, y_std = model.predict(X_test, return_std=True)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    print(f"Model Trained (GPR). MSE: {mse:.6f}, R2: {r2:.4f}")
    
    # Save
    joblib.dump(model, model_path)
    print(f"Saved model to {model_path}")
    
    # Save Feature columns for inference
    joblib.dump(feature_cols, "models/yield_predictor_cols.pkl")

if __name__ == "__main__":
    train_yield_predictor()
