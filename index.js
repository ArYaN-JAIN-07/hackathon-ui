import express from "express"
import bodyparser from "body-parser"
import fs from "fs"
import path from "path"

const app = express();
const port = 4000;

// Enable JSON and urlencoded parsing
app.use(bodyparser.urlencoded({ extended: true }));
app.use(bodyparser.json());
app.use(express.json());

app.use(express.static("public"));

// Global registry mapping for user-friendly display in UI
const datasetMapping = {
  "BBBP": { name: "Blood-Brain Barrier Penetration", category: "Distribution", description: "Predicts blood-brain barrier permeability (CNS targets)." },
  "hERG": { name: "hERG Cardiotoxicity Blocker", category: "Toxicity", description: "Predicts cardiotoxicity risk (blockade of hERG channel)." },
  "CYP2C9": { name: "CYP2C9 Metabolic Inhibition", category: "Metabolism", description: "Predicts liver metabolism safety (inhibits CYP2C9)." },
  "CYP3A4": { name: "CYP3A4 Metabolic Inhibition", category: "Metabolism", description: "Predicts liver metabolism safety (inhibits CYP3A4)." },
  "AqSolDB": { name: "Aqueous Solubility", category: "Absorption", description: "Predicts thermodynamic aqueous solubility in water (LogS)." }
};

// Helper function to read active models from registry
function getActiveModels() {
  const smilesPath = process.env.SMILES_PATH || "D:/SMILES-ADMET-Prediction";
  const registryPath = path.join(smilesPath, "models/model_registry.json");
  try {
    if (fs.existsSync(registryPath)) {
      const data = JSON.parse(fs.readFileSync(registryPath, "utf-8"));
      const active = data.models
        .filter(m => m.status === "active")
        .map(m => {
          const mapping = datasetMapping[m.dataset] || {};
          return {
            dataset: m.dataset,
            algorithm: m.algorithm,
            version: m.version,
            name: mapping.name || m.dataset,
            category: mapping.category || "General",
            description: mapping.description || "ADMET Property Prediction Model"
          };
        });
      return active;
    }
  } catch (err) {
    console.error("Error reading model registry:", err);
  }
  
  // Fallback if registry file cannot be read
  return Object.keys(datasetMapping).map(key => ({
    dataset: key,
    name: datasetMapping[key].name,
    category: datasetMapping[key].category,
    description: datasetMapping[key].description,
    version: "unknown",
    algorithm: "unknown"
  }));
}

app.get("/", (req, res) => {
  const activeModels = getActiveModels();
  res.render("index.ejs", { activeModels });
});

app.post("/predict", async (req, res) => {
  try {
    const { dataset, smiles } = req.body;

    if (!dataset || !smiles) {
      return res.status(400).json({ error: "Missing required parameters: dataset and smiles." });
    }

    // Call local python inference engine on port 5000
    const pyResponse = await fetch("http://127.0.0.1:5000/predict", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ dataset, smiles })
    });

    const pyData = await pyResponse.json();

    if (!pyResponse.ok) {
      return res.status(pyResponse.status).json({ error: pyData.error || "Inference engine error" });
    }

    return res.json(pyData);
  } catch (err) {
    console.error("Connection error to python server:", err);
    return res.status(502).json({
      error: "Could not connect to the ML prediction engine. Please check that the Python server is running on port 5000."
    });
  }
});

app.listen(port, (req, res) => {
  console.log(`The server is running on port ${port}`);
});