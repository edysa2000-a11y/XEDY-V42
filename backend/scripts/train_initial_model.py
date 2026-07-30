import os
import sys
import numpy as np
import xgboost as xgb

def generate_synthetic_data(num_samples=10000):
    """
    Generate synthetic RSI and MACD data for initial training.
    """
    print("Membentuk dataset sintetik...")
    np.random.seed(42)
    
    # RSI antara 10 sampai 90
    rsi = np.random.uniform(10, 90, num_samples)
    # MACD antara -5 sampai 5
    macd = np.random.uniform(-5, 5, num_samples)
    
    X = np.column_stack((rsi, macd))
    y = np.zeros(num_samples)
    
    # Logika Sintetik (Agar AI belajar pola dasar):
    # Jika RSI sangat rendah (Oversold) dan Momentum Positif -> Sangat mungkin BUY (1)
    # Jika RSI sangat tinggi (Overbought) dan Momentum Negatif -> Sangat mungkin SELL (0)
    for i in range(num_samples):
        if rsi[i] < 35 and macd[i] > 0:
            y[i] = 1 # BUY
        elif rsi[i] > 65 and macd[i] < 0:
            y[i] = 0 # SELL
        else:
            # Random dengan sedikit bobot
            prob_buy = 0.5
            if rsi[i] < 50: prob_buy += 0.1
            if macd[i] > 0: prob_buy += 0.1
            y[i] = np.random.binomial(1, prob_buy)
            
    return X, y

def train_and_save():
    print("========================================")
    print("XEDY V41 ULTIMATE - XGBOOST TRAINING")
    print("========================================")
    
    X, y = generate_synthetic_data()
    
    print("Melatih Model XGBoost Classifier...")
    model = xgb.XGBClassifier(
        n_estimators=100,
        learning_rate=0.05,
        max_depth=4,
        random_state=42,
        use_label_encoder=False,
        eval_metric='logloss'
    )
    
    model.fit(X, y)
    
    # Pastikan folder models/ ada
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    models_dir = os.path.join(project_root, 'models')
    os.makedirs(models_dir, exist_ok=True)
    
    model_path = os.path.join(models_dir, 'xgboost_base.json')
    model.save_model(model_path)
    
    print(f"[OK] Model berhasil disimpan ke: {model_path}")
    print("========================================")

if __name__ == "__main__":
    train_and_save()
