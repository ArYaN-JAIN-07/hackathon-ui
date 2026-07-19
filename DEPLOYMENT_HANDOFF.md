# DEPLOYMENT HANDOFF: SMILES ADMET Prediction Pipeline

This document outlines the exact deployable model artifacts, loading instructions, inference API details, and runtime dependencies required by the web development team to integrate the trained ADMET models into a separate web application.

---

## 1. Active Production Models

The following 5 active models are fully trained, verified, and registered as active in [model_registry.json](file:///D:/SMILES-ADMET-Prediction/models/model_registry.json). These are the only models that should be deployed:

| Endpoint (Dataset) | Task Type | Algorithm | Version | File Name | File Format |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **BBBP** | Classification | `RandomForestClassifier` | `v4` | `BBBP_Representation_A_RandomForest_v4.joblib` | `.joblib` |
| **hERG** | Classification | `RandomForestClassifier` | `v4` | `hERG_Representation_A_RandomForest_v4.joblib` | `.joblib` |
| **CYP2C9** | Classification | `RandomForestClassifier` | `v3` | `CYP2C9_Representation_A_RandomForest_v3.joblib` | `.joblib` |
| **CYP3A4** | Classification | `RandomForestClassifier` | `v3` | `CYP3A4_Representation_A_RandomForest_v3.joblib` | `.joblib` |
| **AqSolDB** | Regression | `RandomForestRegressor` | `v1` | `AqSolDB_Representation_A_RandomForestRegressor_v1.joblib` | `.joblib` |

---

## 2. Exact Model File Paths

The production artifacts are located under the following relative paths in this repository:

* **BBBP:** `models/trained_models/BBBP_Representation_A_RandomForest_v4.joblib`
* **hERG:** `models/trained_models/hERG_Representation_A_RandomForest_v4.joblib`
* **CYP2C9:** `models/trained_models/CYP2C9_Representation_A_RandomForest_v3.joblib`
* **CYP3A4:** `models/trained_models/CYP3A4_Representation_A_RandomForest_v3.joblib`
* **AqSolDB:** `models/trained_models/AqSolDB_Representation_A_RandomForestRegressor_v1.joblib`

*Additionally, their metadata JSON records (e.g. `BBBP_Representation_A_RandomForest_v4_metadata.json`) containing training parameters and performance hashes are adjacent to each artifact in the same directory.*

---

## 3. Loading Instructions

### Deployment Entry Point
* **Class Name:** `ADMETPredictionPipeline`
* **Module:** `src.models.pipeline`
* **Loading Method:** `joblib.load()`

### Python Example Code for Loading
The backend must import the pipeline class and use `joblib` to deserialize the model file:

```python
import sys
import joblib
from pathlib import Path

# 1. Ensure the ML codebase is on the Python path
sys.path.append("/path/to/SMILES-ADMET-Prediction")

# 2. Load the pipeline class
from src.models.pipeline import ADMETPredictionPipeline

# 3. Load the model artifact
model_path = Path("models/trained_models/hERG_Representation_A_RandomForest_v4.joblib")
pipeline: ADMETPredictionPipeline = joblib.load(model_path)
```

---

## 4. Inference API

The deserialized `ADMETPredictionPipeline` provides a fully self-contained inference contract. It performs SMILES validation, physical-chemical descriptor extraction (via RDKit), NaN imputation, feature scaling, column alignment, and runs predictions.

### Single Prediction
* **Method:** `pipeline.predict_smiles(smiles: str) -> Dict[str, Any]`
* **Expected Input:** A valid SMILES string (e.g. `"CCO"`).
* **Expected Output:** A Python dictionary with prediction results.

### Batch Prediction
* **Method:** `pipeline.predict_smiles_batch(smiles_list: List[str]) -> List[Dict[str, Any]]`
* **Expected Input:** A list of SMILES strings.
* **Expected Output:** A list of prediction dictionaries.

---

## 5. Required Dependencies

The backend serving environment must have the following libraries installed:

1. **`scikit-learn`** (ML estimators and standard scaling)
2. **`rdkit`** (parsing SMILES strings and calculating molecular descriptors/fingerprints)
3. **`pandas`** and **`numpy`** (handling data alignments and array calculations)
4. **`joblib`** (deserialization of model files)

---

## 6. Expected Input/Output Formats

### Classification Outputs (BBBP, hERG, CYP2C9, CYP3A4)
Classification models return predicted binary classes (`0.0` or `1.0`), alongside probability scores if supported.

#### Example Output (`pipeline.predict_smiles("CCO")` on hERG):
```json
{
    "prediction": 0.0,
    "dataset": "hERG",
    "representation": "Representation_A",
    "algorithm": "RandomForestClassifier",
    "version": "v4",
    "task_type": "classification",
    "probabilities": [0.86, 0.14],
    "probability_positive_class": 0.14
}
```

### Regression Outputs (AqSolDB)
Regression models return predicted continuous values.

#### Example Output (`pipeline.predict_smiles("CCO")` on AqSolDB):
```json
{
    "prediction": 1.1286900007840002,
    "dataset": "AqSolDB",
    "representation": "Representation_A",
    "algorithm": "RandomForestRegressor",
    "version": "v1",
    "task_type": "regression"
}
```

---

## 7. Backend Integration Steps

The backend flow requires **no external preprocessing** because `ADMETPredictionPipeline` is fully self-contained:

```
SMILES String (e.g. "CCO")
      ↓
joblib.load("models/trained_models/...")
      ↓
pipeline.predict_smiles(smiles)
      ↓
Return JSON Response to Frontend
```

---

## 8. Deployment Checklist

- [x] **Model Verification:** Verified that all 5 active models deserialize successfully and yield correct output schemas.
- [x] **No Serve-Time Feature Skew:** Verified that scaling variables (`scaler`) and descriptor mean values (`imputation_means`) are embedded in the pipeline object.
- [x] **Invalid Input Safety:** Verified that invalid SMILES inputs (e.g., `"invalid_smiles"`) safely raise a catchable `ValueError` instead of crashing.

---

## 9. Smoke Test Instructions

You can run a quick validation check by running the verified script:

```bash
python -c "
import joblib, sys
sys.path.append('.')
p = joblib.load('models/trained_models/BBBP_Representation_A_RandomForest_v4.joblib')
print(p.predict_smiles('CCO'))
"
```

Expected Output: A dictionary with `"prediction": 1.0` or `"prediction": 0.0` depending on the endpoint.

---

## 10. Final Recommendation

The web application developer only needs to configure the Python path to import [pipeline.py](file:///D:/SMILES-ADMET-Prediction/src/models/pipeline.py), call `joblib.load()` on the paths in Section 2, and expose the `predict_smiles` outputs directly as JSON API endpoints.

These are the exact artifacts that should be deployed in the web application.
