const statusBox = document.getElementById("statusBox");
const metaBox = document.getElementById("metaBox");
const demoForm = document.getElementById("demoForm");
const ingestGenericForm = document.getElementById("ingestGenericForm");
const ingestHmdbForm = document.getElementById("ingestHmdbForm");
const ingestMassBankForm = document.getElementById("ingestMassBankForm");
const ingestPubChemForm = document.getElementById("ingestPubChemForm");
const ingestLiteratureForm = document.getElementById("ingestLiteratureForm");
const analyzeForm = document.getElementById("analyzeForm");
const analyzeToolForm = document.getElementById("analyzeToolForm");
const runRReportForm = document.getElementById("runRReportForm");
const rBox = document.getElementById("rBox");

const candidatesBody = document.querySelector("#candidatesTable tbody");
const pathwaysBody = document.querySelector("#pathwaysTable tbody");
let latestAnalysisResult = null;

function setStatus(message, isError = false) {
  statusBox.textContent = message;
  statusBox.style.color = isError ? "#b42318" : "#1b2330";
}

function renderCandidates(candidates) {
  candidatesBody.innerHTML = "";
  if (!Array.isArray(candidates) || candidates.length === 0) {
    candidatesBody.innerHTML = "<tr><td colspan='13'>No candidates found.</td></tr>";
    return;
  }

  for (const item of candidates) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${item.adduct_id ?? ""}</td>
      <td>${item.adduct_name ?? ""}</td>
      <td>${item.source_name ?? ""}</td>
      <td>${item.pathway ?? ""}</td>
      <td>${Number(item.ppm_error).toFixed(3)}</td>
      <td>${item.nl_error == null ? "" : Number(item.nl_error).toFixed(4)}</td>
      <td>${item.rt_error == null ? "" : Number(item.rt_error).toFixed(3)}</td>
      <td>${item.isotope_error == null ? "" : Number(item.isotope_error).toFixed(4)}</td>
      <td>${Number(item.confidence_score).toFixed(4)}</td>
      <td>${item.confidence_level ?? ""}</td>
      <td>${item.evidence_count ?? ""}</td>
      <td>${item.component_scores ? JSON.stringify(item.component_scores) : ""}</td>
      <td>${Array.isArray(item.matched_by) ? item.matched_by.join(", ") : ""}</td>
    `;
    candidatesBody.appendChild(tr);
  }
}

function renderMetadata(metadata) {
  if (!metadata) {
    metaBox.textContent = "Run metadata unavailable.";
    return;
  }
  const params = metadata.parameters || {};
  metaBox.textContent =
    `Run ID: ${metadata.run_id}\n` +
    `Generated: ${metadata.generated_at}\n` +
    `Software Version: ${metadata.software_version}\n` +
    `Scoring: ${params.scoring_version}\n` +
    `Tolerance (ppm): ${params.tolerance_ppm}\n` +
    `NL Tolerance (Da): ${params.neutral_loss_tolerance_da}\n` +
    `RT Tolerance (min): ${params.rt_tolerance_min}\n` +
    `Isotope Tolerance: ${params.isotope_tolerance}\n` +
    `Top-K: ${params.top_k_per_transition}`;
}

function renderPathways(pathways) {
  pathwaysBody.innerHTML = "";
  if (!Array.isArray(pathways) || pathways.length === 0) {
    pathwaysBody.innerHTML = "<tr><td colspan='5'>No enriched pathways.</td></tr>";
    return;
  }
  for (const item of pathways) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${item.pathway ?? ""}</td>
      <td>${item.hits ?? 0}</td>
      <td>${item.population_size ?? 0}</td>
      <td>${Number(item.enrichment_score).toFixed(4)}</td>
      <td>${Number(item.p_value).toExponential(2)}</td>
    `;
    pathwaysBody.appendChild(tr);
  }
}

function renderAnalysisResult(result, statusPrefix = "Analysis complete.") {
  latestAnalysisResult = result;
  setStatus(
    `${statusPrefix}\nSample: ${result.sample_id}\nTransitions: ${result.transitions_analyzed}\nCandidates: ${result.candidates.length}`
  );
  renderMetadata(result.metadata);
  renderCandidates(result.candidates);
  renderPathways(result.pathway_scores);
}

function renderRStatus(payload) {
  if (!payload) {
    rBox.textContent = "R statistics status unavailable.";
    return;
  }
  rBox.textContent =
    `Status: ${payload.status}\n` +
    `Message: ${payload.message}\n` +
    `Output: ${payload.output_path ?? "N/A"}\n` +
    `Script: ${payload.script_path ?? "N/A"}`;
}

async function postForm(endpoint, formData) {
  const response = await fetch(endpoint, { method: "POST", body: formData });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Request failed");
  }
  return data;
}

demoForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    setStatus("Running one-click demo...");
    const formData = new FormData(demoForm);
    const result = await postForm("/api/v1/demo/run", formData);
    renderAnalysisResult(result, "Demo run complete.");
  } catch (error) {
    setStatus(`Demo run failed: ${error.message}`, true);
  }
});

ingestGenericForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    setStatus("Uploading generic adduct CSV...");
    const formData = new FormData(ingestGenericForm);
    const result = await postForm("/api/v1/ingest/adduct-bank/upload-csv", formData);
    setStatus(
      `Generic adduct CSV ingested.\nRecords: ${result.ingested_records}\nSource: ${result.source_name}`
    );
  } catch (error) {
    setStatus(`Ingest failed: ${error.message}`, true);
  }
});

ingestHmdbForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    setStatus("Uploading HMDB CSV...");
    const formData = new FormData(ingestHmdbForm);
    const result = await postForm("/api/v1/ingest/adduct-bank/upload-hmdb", formData);
    setStatus(
      `HMDB CSV ingested.\nRecords: ${result.ingested_records}\nSource: ${result.source_name}\nIon mode: ${result.ion_mode}`
    );
  } catch (error) {
    setStatus(`HMDB ingest failed: ${error.message}`, true);
  }
});

ingestMassBankForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    setStatus("Uploading MassBank CSV...");
    const formData = new FormData(ingestMassBankForm);
    const result = await postForm("/api/v1/ingest/adduct-bank/upload-massbank", formData);
    setStatus(
      `MassBank CSV ingested.\nRecords: ${result.ingested_records}\nSource: ${result.source_name}`
    );
  } catch (error) {
    setStatus(`MassBank ingest failed: ${error.message}`, true);
  }
});

ingestPubChemForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    setStatus("Uploading PubChem CSV...");
    const formData = new FormData(ingestPubChemForm);
    const result = await postForm("/api/v1/ingest/adduct-bank/upload-pubchem", formData);
    setStatus(
      `PubChem CSV ingested.\nRecords: ${result.ingested_records}\nSource: ${result.source_name}\nIon mode: ${result.ion_mode}`
    );
  } catch (error) {
    setStatus(`PubChem ingest failed: ${error.message}`, true);
  }
});

ingestLiteratureForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    setStatus("Uploading literature supplementary CSV...");
    const formData = new FormData(ingestLiteratureForm);
    const result = await postForm("/api/v1/ingest/adduct-bank/upload-literature", formData);
    setStatus(
      `Literature CSV ingested.\nRecords: ${result.ingested_records}\nSource: ${result.source_name}`
    );
  } catch (error) {
    setStatus(`Literature ingest failed: ${error.message}`, true);
  }
});

analyzeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    setStatus("Running MRM/NL analysis...");
    const formData = new FormData(analyzeForm);
    const result = await postForm("/api/v1/analyze/mrm-nl/upload-csv", formData);
    renderAnalysisResult(result, "Analysis complete.");
  } catch (error) {
    setStatus(`Analysis failed: ${error.message}`, true);
  }
});

analyzeToolForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    setStatus("Running tool-export analysis...");
    const formData = new FormData(analyzeToolForm);
    formData.set("tolerance_ppm", "10");
    formData.set("neutral_loss_tolerance_da", "0.5");
    formData.set("rt_tolerance_min", "0.5");
    formData.set("isotope_tolerance", "0.15");
    formData.set("top_k_per_transition", "5");
    const result = await postForm("/api/v1/analyze/tool/upload-csv", formData);
    renderAnalysisResult(result, "Tool-based analysis complete.");
  } catch (error) {
    setStatus(`Tool analysis failed: ${error.message}`, true);
  }
});

runRReportForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!latestAnalysisResult) {
    setStatus("Run an analysis first before generating R report.", true);
    return;
  }
  try {
    setStatus("Generating R statistics report...");
    const reportTitle = new FormData(runRReportForm).get("report_title");
    const response = await fetch("/api/v1/stats/r-report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sample_id: latestAnalysisResult.sample_id,
        candidates: latestAnalysisResult.candidates,
        pathway_scores: latestAnalysisResult.pathway_scores,
        report_title: reportTitle,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "R report request failed");
    }
    renderRStatus(payload);
    setStatus("R statistics request processed.");
  } catch (error) {
    setStatus(`R statistics failed: ${error.message}`, true);
  }
});
