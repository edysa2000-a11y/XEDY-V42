import os
import json
import logging
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
WEIGHTS_FILE = BASE_DIR / "ml_weights.json"
MEMORY_FILE = BASE_DIR / "trade_memory.json"

DEFAULT_WEIGHTS = {
    "macro_weight": 0.30,
    "tech_weight": 0.30,
    "flow_weight": 0.40,
    "confidence_multiplier": 1.0,
    "last_evaluated_ticket": 0
}

logger = logging.getLogger("MLEngine")

def load_weights():
    if not WEIGHTS_FILE.exists():
        save_weights(DEFAULT_WEIGHTS)
        return DEFAULT_WEIGHTS.copy()
    try:
        with open(WEIGHTS_FILE, 'r') as f:
            data = json.load(f)
            # Ensure all keys exist
            for k, v in DEFAULT_WEIGHTS.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception as e:
        logger.error(f"Error loading ml_weights: {e}")
        return DEFAULT_WEIGHTS.copy()

def save_weights(weights):
    try:
        with open(WEIGHTS_FILE, 'w') as f:
            json.dump(weights, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving ml_weights: {e}")

def get_weights():
    return load_weights()

def load_memory():
    if not MEMORY_FILE.exists():
        return {}
    try:
        with open(MEMORY_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading trade_memory: {e}")
        return {}

def save_memory(memory):
    try:
        with open(MEMORY_FILE, 'w') as f:
            json.dump(memory, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving trade_memory: {e}")

def save_trade_context(ticket, action, macro_score, tech_score, flow_score, mixed_prob):
    """
    Saves the state of the AI at the time a trade was opened.
    """
    memory = load_memory()
    memory[str(ticket)] = {
        "action": action, # "BUY" or "SELL"
        "macro_score": macro_score, # e.g. 50 (wait, DXY strength. 100-DXY is gold strength)
        "tech_score": tech_score,
        "flow_score": flow_score,
        "mixed_prob": mixed_prob # The final consensus raw_prob
    }
    save_memory(memory)
    logger.info(f"Self-Learning: Saved context for Ticket #{ticket}")

def evaluate_and_update_weights(ticket, profit):
    """
    Evaluates a closed trade and shifts weights.
    Returns True if weights were updated.
    """
    memory = load_memory()
    ticket_str = str(ticket)
    
    if ticket_str not in memory:
        return False
        
    context = memory[ticket_str]
    weights = load_weights()
    
    # Only evaluate once per ticket to prevent double-penalizing
    if ticket <= weights.get("last_evaluated_ticket", 0):
        # We can just check if ticket was evaluated or not, but usually we just process newly closed deals.
        pass

    action = context.get("action")
    macro_s = context.get("macro_score", 50)
    tech_s = context.get("tech_score", 50)
    
    # Note: in consensus_gate, macro_s is (100 - dxy_strength).
    # So macro_s > 50 means Macro is BUY.
    
    signal_mixed = 1 if action == "BUY" else -1
    hasil_trade = 1 if profit >= 0 else -1
    
    true_dir = signal_mixed * hasil_trade
    
    fund_signal = 1 if macro_s > 50 else -1
    tech_signal = 1 if tech_s > 50 else -1
    
    fund_benar = (fund_signal == true_dir)
    tech_benar = (tech_signal == true_dir)
    
    alpha = 0.05 # Learning Rate
    
    w_fund = weights["macro_weight"]
    w_tech = weights["tech_weight"]
    conf = weights.get("confidence_multiplier", 1.0)
    
    updated = False
    
    if fund_benar and not tech_benar:
        w_fund += alpha
        w_tech -= alpha
        logger.info(f"ML Update: Fund Correct, Tech Wrong. Macro W: {w_fund:.2f}, Tech W: {w_tech:.2f}")
        updated = True
    elif tech_benar and not fund_benar:
        w_tech += alpha
        w_fund -= alpha
        logger.info(f"ML Update: Tech Correct, Fund Wrong. Macro W: {w_fund:.2f}, Tech W: {w_tech:.2f}")
        updated = True
        
    if fund_benar and tech_benar:
        conf = min(1.5, conf + 0.1) # Max 1.5x lot size
        logger.info(f"ML Update: Both Correct. Confidence -> {conf:.2f}")
        updated = True
    elif not fund_benar and not tech_benar:
        conf = max(0.5, conf - 0.1) # Min 0.5x lot size
        logger.info(f"ML Update: Both Wrong. Confidence -> {conf:.2f}")
        updated = True
        
    if updated:
        # Prevent extreme weights
        w_fund = max(0.1, min(0.6, w_fund))
        w_tech = max(0.1, min(0.6, w_tech))
        
        # Normalize to ensure they sum to exactly 0.6 (since flow is 0.4)
        total = w_fund + w_tech
        if total > 0:
            w_fund = (w_fund / total) * 0.6
            w_tech = (w_tech / total) * 0.6
        else:
            w_fund, w_tech = 0.3, 0.3
            
        weights["macro_weight"] = round(w_fund, 3)
        weights["tech_weight"] = round(w_tech, 3)
        weights["confidence_multiplier"] = round(conf, 3)
        weights["last_evaluated_ticket"] = max(weights.get("last_evaluated_ticket", 0), ticket)
        
        save_weights(weights)
        
        # Clean up memory to prevent bloat
        memory.pop(ticket_str)
        save_memory(memory)
        return True
        
    return False
