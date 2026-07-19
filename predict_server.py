import os
import sys
import json
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer

# Ensure path to SMILES-ADMET-Prediction is in path for resolving src imports
SMILES_PATH = os.environ.get("SMILES_PATH", "D:/SMILES-ADMET-Prediction")
if SMILES_PATH not in sys.path:
    sys.path.append(SMILES_PATH)

import joblib
from src.models.pipeline import ADMETPredictionPipeline

# Configure logging
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("predict_server")

# Define globals for loaded models and metadata
LOADED_MODELS = {}
ACTIVE_DATASETS = []

def load_active_models():
    """Discover active models from the model registry and load them into memory once."""
    global LOADED_MODELS, ACTIVE_DATASETS
    registry_path = os.path.join(SMILES_PATH, "models", "model_registry.json")
    
    logger.info(f"Reading model registry from {registry_path}...")
    if not os.path.exists(registry_path):
        logger.error(f"Registry file not found at {registry_path}!")
        sys.exit(1)
        
    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
    except Exception as e:
        logger.error(f"Failed to parse registry JSON: {e}")
        sys.exit(1)
        
    active_models_info = [m for m in registry.get("models", []) if m.get("status") == "active"]
    logger.info(f"Found {len(active_models_info)} active models in the registry.")
    
    for model_info in active_models_info:
        dataset = model_info["dataset"]
        rel_path = model_info["artifact_path"]
        abs_path = os.path.abspath(os.path.join(SMILES_PATH, rel_path))
        
        logger.info(f"Loading model for {dataset} from {abs_path}...")
        if not os.path.exists(abs_path):
            logger.error(f"Model artifact not found at {abs_path}!")
            continue
            
        try:
            pipeline = joblib.load(abs_path)
            LOADED_MODELS[dataset] = pipeline
            ACTIVE_DATASETS.append(dataset)
            logger.info(f"Successfully loaded {dataset} model.")
        except Exception as e:
            logger.error(f"Failed to load {dataset} model: {e}")
            logger.error(traceback.format_exc())

class PredictionHTTPHandler(BaseHTTPRequestHandler):
    """Handler for predict server requests."""
    
    def _send_json(self, status_code, data):
        """Helper to send JSON response."""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
        
    def do_OPTIONS(self):
        """Respond to OPTIONS CORS preflight."""
        self._send_json(200, {"status": "ok"})

    def do_GET(self):
        """Handle health check and model discovery GET requests."""
        if self.path == "/health" or self.path == "/":
            self._send_json(200, {
                "status": "healthy",
                "active_models": ACTIVE_DATASETS
            })
        elif self.path == "/active_models":
            self._send_json(200, {
                "active_models": ACTIVE_DATASETS
            })
        else:
            self._send_json(404, {"error": "Endpoint not found"})

    def do_POST(self):
        """Handle POST requests for model predictions."""
        if self.path != "/predict":
            self._send_json(404, {"error": "Endpoint not found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self._send_json(400, {"error": "Empty request body"})
                return

            body = self.rfile.read(content_length).decode("utf-8")
            try:
                request_data = json.loads(body)
            except json.JSONDecodeError:
                self._send_json(400, {"error": "Malformed JSON in request body"})
                return

            dataset = request_data.get("dataset")
            smiles = request_data.get("smiles")

            if not dataset:
                self._send_json(400, {"error": "Missing 'dataset' parameter"})
                return
            if not smiles or not isinstance(smiles, str) or not smiles.strip():
                self._send_json(400, {"error": "Missing or invalid 'smiles' parameter"})
                return

            smiles = smiles.strip()

            if dataset not in LOADED_MODELS:
                self._send_json(404, {
                    "error": f"Model for dataset '{dataset}' is not active or not loaded. Available models: {ACTIVE_DATASETS}"
                })
                return

            pipeline = LOADED_MODELS[dataset]
            
            try:
                logger.info(f"Running inference for dataset={dataset}, SMILES={smiles}")
                result = pipeline.predict_smiles(smiles)
                
                # Make sure response keys match the task requirements exactly
                response_payload = {
                    "dataset": dataset,
                    "prediction": result.get("prediction"),
                    "task_type": result.get("task_type", "classification")
                }
                
                # If classification and probabilities are available, copy them over
                if response_payload["task_type"] == "classification" and "probability_positive_class" in result:
                    response_payload["probability_positive_class"] = result["probability_positive_class"]
                    response_payload["probabilities"] = result.get("probabilities", [])

                self._send_json(200, response_payload)

            except ValueError as val_err:
                logger.warning(f"SMILES validation error: {val_err}")
                self._send_json(400, {
                    "error": f"SMILES validation failed: {str(val_err)}"
                })
            except Exception as inf_err:
                logger.error(f"Inference execution error: {inf_err}")
                logger.error(traceback.format_exc())
                self._send_json(500, {
                    "error": f"Inference engine failure: {str(inf_err)}"
                })

        except Exception as e:
            logger.error(f"Unexpected request processing error: {e}")
            logger.error(traceback.format_exc())
            self._send_json(500, {"error": f"Internal server error: {str(e)}"})

def run_server(port=5000):
    """Start the prediction HTTP server on localhost."""
    load_active_models()
    if not LOADED_MODELS:
        logger.error("No models loaded successfully. Exiting.")
        sys.exit(1)
        
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, PredictionHTTPHandler)
    logger.info(f"Python prediction server running on http://127.0.0.1:{port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopping...")
        httpd.server_close()
        logger.info("Server stopped.")

if __name__ == "__main__":
    port = 5000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port)
