# models/scoring.py
import math
import joblib
import numpy as np

MODEL_PATH = "models/artifacts/fraud_model.joblib"
_model_bundle = None

def load_bundle():
    global _model_bundle
    if _model_bundle is None:
        _model_bundle = joblib.load(MODEL_PATH)
    return _model_bundle

def _vectorize(feature_row: dict, cols: list[str]) -> np.ndarray:
    x = []
    for c in cols:
        v = feature_row[c]
        if c == "is_foreign_country":
            x.append(1.0 if v else 0.0)
        else:
            x.append(float(v))
    return np.array(x, dtype=float)

def score_from_features(feature_row: dict) -> float:
    """
    Returns probability of fraud (0..1)
    """
    bundle = load_bundle()
    model = bundle["model"]
    cols = bundle["feature_cols"]
    X = np.array([_vectorize(feature_row, cols)], dtype=float)
    return float(model.predict_proba(X)[0, 1])

def score_with_reasons(feature_row: dict, top_k: int = 3):
    """
    Explainability for LogisticRegression inside Pipeline(StandardScaler -> LogisticRegression).
    Produces top contributing features (approx) using scaled-feature linear contributions.
    """
    bundle = load_bundle()
    pipe = bundle["model"]
    cols = bundle["feature_cols"]

    scaler = pipe.named_steps["scaler"]
    clf = pipe.named_steps["clf"]

    x = _vectorize(feature_row, cols)
    z = (x - scaler.mean_) / scaler.scale_  # scaled features

    coefs = clf.coef_[0]  # shape (n_features,)
    intercept = float(clf.intercept_[0])

    contributions = coefs * z  # per-feature log-odds contribution
    logit = intercept + float(np.sum(contributions))
    prob = 1.0 / (1.0 + math.exp(-logit))

    # pick top absolute contributions
    idxs = np.argsort(np.abs(contributions))[::-1][:top_k]
    reasons = []
    for i in idxs:
        reasons.append({
            "feature": cols[int(i)],
            "value": float(x[int(i)]),
            "contribution": float(contributions[int(i)]),  # log-odds contribution (signed)
        })

    return prob, reasons
