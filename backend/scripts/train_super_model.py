import pandas as pd
import numpy as np
import xgboost as xgb
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, precision_score

def main():
    csv_path = "data/training_features.csv"
    if not os.path.exists(csv_path):
        print(f"Error: Dataset {csv_path} not found. Please run collect_training_data.py first.")
        return
        
    print(f"Loading dataset from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # Filter out -1 (ranging/chop) to keep ONLY high-conviction trends
    clean_df = df[df['target'] != -1].reset_index(drop=True)
    print(f"Dataset filtered: original {len(df)} rows -> clean {len(clean_df)} trend rows.")
    
    if len(clean_df) < 100:
        print("Error: Not enough clean trend rows to train model.")
        return
        
    # Feature columns
    feature_cols = [
        'rsi', 'macd', 'adx', 'atr', 
        'nfp_surprise', 'cpi_surprise', 'fed_rate',
        'dxy_trend', 'yield_trend',
        'session_asia', 'session_europe', 'session_america', 'session_overlap'
    ]
    
    # Analyze and print Trend Profiling breakdown (MAE/MFE)
    strong_trend = clean_df[(clean_df['mfe'] >= 5.0) & (clean_df['mae'] <= 1.0)]
    sideways_chop = clean_df[(clean_df['mfe'] <= 2.0) & (clean_df['mae'] >= 2.0)]
    print(f"\n--- MAE/MFE TREND PROFILE ANALYSIS ---")
    print(f"  • Strong Volatility Trends (High MFE, Low MAE): {len(strong_trend)} rows")
    print(f"  • Sideways/Chop Ranges (Low MFE, High MAE): {len(sideways_chop)} rows")
    
    X = clean_df[feature_cols]
    y = clean_df['target']
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    print("Training High-Precision XGBoost Classifier...")
    # Focal-like parameter weight scaling to prioritize high confidence
    model = xgb.XGBClassifier(
        n_estimators=150,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=1.0,
        random_state=42
    )
    
    model.fit(X_train, y_train)
    
    # Evaluation
    y_pred = model.predict(X_test)
    y_probs = model.predict_proba(X_test)
    
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, average='binary')
    
    print("\n=== MODEL PERFORMANCE ===")
    print(f"Test Accuracy: {acc*100.0:.2f}%")
    print(f"Test Precision: {prec*100.0:.2f}%")
    
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    # Simulate high confidence prediction threshold (prob >= 0.85)
    print("\nSimulating High-Confidence Filter (Threshold >= 0.85)...")
    high_conf_preds = []
    high_conf_targets = []
    
    for i in range(len(y_probs)):
        prob_buy = y_probs[i][1]
        prob_sell = y_probs[i][0]
        actual = y_test.iloc[i]
        
        if prob_buy >= 0.85:
            high_conf_preds.append(1)
            high_conf_targets.append(actual)
        elif prob_sell >= 0.85:
            high_conf_preds.append(0)
            high_conf_targets.append(actual)
            
    if high_conf_preds:
        hc_acc = accuracy_score(high_conf_targets, high_conf_preds)
        print(f"High-Confidence Total Trades: {len(high_conf_preds)}")
        print(f"High-Confidence Precision (Winrate): {hc_acc*100.0:.2f}%")
        if hc_acc >= 0.90:
            print("TARGET WINRATE > 90% ACHIEVED!")
        else:
            print("Winrate target not met on test set. Consider raising threshold.")
    else:
        print("No trades triggered under 0.85 threshold. Consider widening dataset size.")
        
    # Save the model, overwriting the old xgboost_base.json model
    os.makedirs("models", exist_ok=True)
    model_save_path = "models/xgboost_base.json"
    model.save_model(model_save_path)
    print(f"Model saved successfully to {model_save_path}!")

if __name__ == "__main__":
    main()
