"""Delay prediction runtime wrapper.

This module attempts to load a persisted sklearn-like model and a
vectorizer. Imports are performed lazily so that the main application
does not fail at import time when ML dependencies or model files aren't
available in a development environment.
"""

MODEL_PATH = "delay_model.pkl"
VECT_PATH = "damage_vectorizer.pkl"


def predict_delay(repair_days, warehouse_load, vendor_load, damage_text):
    try:
        # import heavy ML deps lazily
        import joblib
        import numpy as np
    except Exception:
        return None

    try:
        model = joblib.load(MODEL_PATH)
        vect = joblib.load(VECT_PATH)
    except Exception:
        return None

    try:
        damage_features = vect.transform([damage_text]).toarray()
        X = np.hstack([[repair_days, warehouse_load, vendor_load], damage_features[0]])
        prob = model.predict_proba([X])[0][1]
        return round(prob * 100, 2)
    except Exception:
        return None
