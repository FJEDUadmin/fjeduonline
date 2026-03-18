const statusBox = document.getElementById("statusBox");
const ingestGenericForm = document.getElementById("ingestGenericForm");
const ingestHmdbForm = document.getElementById("ingestHmdbForm");
const analyzeForm = document.getElementById("analyzeForm");

const candidatesBody = document.querySelector("#candidatesTable tbody");
const pathwaysBody = document.querySelector("#pathwaysTable tbody");

function setStatus(message, isError = false) {
  statusBox.textContent = message;
  statusBox.style.color = isError ? "#b42318" : "#1b2330";
}

function renderCandidates(candidates) {
  candidatesBody.innerHTML = "";
  if (!Array.isArray(candidates) || candidates.length === 0) {
    candidatesBody.innerHTML = "<tr><td colspan='8'>No candidates found.</td></tr>";
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
      <td>${Number(item.confidence_score).toFixed(4)}</td>
      <td>${Array.isArray(item.matched_by) ? item.matched_by.join(", ") : ""}</td>
    `;
    candidatesBody.appendChild(tr);
  }
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

async function postForm(endpoint, formData) {
  const response = await fetch(endpoint, { method: "POST", body: formData });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Request failed");
  }
  return data;
}

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

analyzeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    setStatus("Running MRM/NL analysis...");
    const formData = new FormData(analyzeForm);
    const result = await postForm("/api/v1/analyze/mrm-nl/upload-csv", formData);
    setStatus(
      `Analysis complete.\nSample: ${result.sample_id}\nTransitions: ${result.transitions_analyzed}\nCandidates: ${result.candidates.length}`
    );
    renderCandidates(result.candidates);
    renderPathways(result.pathway_scores);
  } catch (error) {
    setStatus(`Analysis failed: ${error.message}`, true);
  }
});
