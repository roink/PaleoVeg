import "./cache-manifest.js";

const CLASS_COLORS = [
  "#174c38", "#2e7047", "#5c7c45", "#77964a", "#3f6958", "#8b7b3f",
  "#aa9d50", "#876347", "#b68b5a", "#d1b85d", "#d8d1b9",
];
const WORLD_TOPOLOGY_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

const elements = {
  input: document.querySelector("#file-input"),
  drop: document.querySelector("#drop-zone"),
  summary: document.querySelector("#file-summary"),
  fileName: document.querySelector("#file-name"),
  fileDetails: document.querySelector("#file-details"),
  replace: document.querySelector("#replace-file"),
  privacyNote: document.querySelector("#privacy-note"),
  mappingSection: document.querySelector("#mapping-section"),
  mappingSummary: document.querySelector("#mapping-summary"),
  mappingBadge: document.querySelector("#mapping-badge"),
  mappingBody: document.querySelector("#mapping-body"),
  mappingFeedback: document.querySelector("#mapping-feedback"),
  sourceChoice: document.querySelector("#source-choice"),
  detectionNote: document.querySelector("#detection-note"),
  mappingTargetHeading: document.querySelector("#mapping-target-heading"),
  unitReview: document.querySelector("#unit-review"),
  temperatureUnit: document.querySelector("#temperature-unit"),
  temperatureUnitNote: document.querySelector("#temperature-unit-note"),
  precipitationUnit: document.querySelector("#precipitation-unit"),
  continueButton: document.querySelector("#continue-button"),
  uploadPanel: document.querySelector("#upload-panel"),
  configPanel: document.querySelector("#config-panel"),
  stepData: document.querySelector("#step-data"),
  stepConfigure: document.querySelector("#step-configure"),
  stepResults: document.querySelector("#step-results"),
  run: document.querySelector("#run-button"),
  backToData: document.querySelector("#back-to-data"),
  resultsBackConfigure: document.querySelector("#results-back-configure"),
  resultsBackData: document.querySelector("#results-back-data"),
  correction: document.querySelector("#correction"),
  co2Control: document.querySelector("#co2-control"),
  co2ManualControl: document.querySelector("#co2-manual-control"),
  co2TimeControl: document.querySelector("#co2-time-control"),
  co2Ppm: document.querySelector("#co2-ppm"),
  ageKaBp: document.querySelector("#age-ka-bp"),
  co2LookupDetails: document.querySelector("#co2-lookup-details"),
  co2Feedback: document.querySelector("#co2-feedback"),
  uploadProgress: document.querySelector("#upload-progress"),
  uploadProgressBar: document.querySelector("#upload-progress-bar"),
  uploadProgressMessage: document.querySelector("#upload-progress-message"),
  progress: document.querySelector("#progress"),
  progressBar: document.querySelector("#progress-bar"),
  progressMessage: document.querySelector("#progress-message"),
  results: document.querySelector("#results-panel"),
  resultStats: document.querySelector("#result-stats"),
  mapPreview: document.querySelector("#map-preview"),
  canvas: document.querySelector("#map-canvas"),
  mapEmpty: document.querySelector("#map-empty"),
  legend: document.querySelector("#legend"),
  previewPicker: document.querySelector("#preview-picker"),
  downloads: document.querySelector("#downloads"),
};

const stepButtons = [...document.querySelectorAll("[data-step]")];

const worker = new Worker("pyodide-worker.mjs?v=runtime-cache-4", { type: "module" });
const pending = new Map();
let requestId = 0;
let selectedFile = null;
let inputHash = null;
let latestResult = null;
let downloadUrls = [];
let activeStage = null;
let mappingAnalysis = null;
let completeAnalysis = null;
let selectedInputMode = null;
let mappingChoices = [];
let mappingReviewed = false;
let worldBordersPromise = null;
let co2DataPromise = null;
let co2LookupState = null;
let runtimeWarmup = null;
let runtimeWarming = false;

worker.onmessage = ({ data }) => {
  if (data.type === "status") {
    if (activeStage === "upload" && !runtimeWarming) showUploadProgress(data.message, data.progress);
    else if (activeStage === "prediction" || activeStage === "export") showProgress(data.message, data.progress);
    return;
  }
  const request = pending.get(data.id);
  if (!request) return;
  pending.delete(data.id);
  if (data.type === "error") request.reject(new Error(data.error));
  else request.resolve(data.result);
};

function callWorker(action, payload, transfer = []) {
  const id = ++requestId;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    worker.postMessage({ id, action, payload }, transfer);
  });
}

function registerServiceWorker() {
  if (!('serviceWorker' in navigator)) return;
  navigator.serviceWorker.register("service-worker.js").catch(() => {});
}

function shouldDeferWarmup() {
  const connection = navigator.connection;
  return Boolean(connection?.saveData) || ["slow-2g", "2g"].includes(connection?.effectiveType);
}

function warmupRuntime() {
  if (runtimeWarmup || shouldDeferWarmup()) return;
  runtimeWarming = true;
  runtimeWarmup = callWorker("warmup", {})
    .catch(() => {})
    .finally(() => { runtimeWarming = false; });
}

function updateStepNavigation() {
  const canConfigure = mappingReviewed;
  const canResults = Boolean(latestResult);
  stepButtons.forEach(button => {
    const step = button.dataset.step;
    button.disabled = (step === "configure" && !canConfigure) || (step === "results" && !canResults);
  });
}

function setWorkflowStep(step, scroll = true) {
  if (step === "configure" && !mappingReviewed) return;
  if (step === "results" && !latestResult) return;
  const panels = {
    data: elements.uploadPanel,
    configure: elements.configPanel,
    results: elements.results,
  };
  Object.entries(panels).forEach(([name, panel]) => panel.classList.toggle("hidden", name !== step));
  elements.stepData.className = step === "data" ? "active" : "completed";
  elements.stepConfigure.className = step === "configure" ? "active" : step === "results" ? "completed" : "";
  elements.stepResults.className = step === "results" ? "active" : "";
  updateStepNavigation();
  if (scroll) panels[step].scrollIntoView({ behavior: "smooth", block: "start" });
}

function showProgress(message, progress = 5) {
  elements.progress.classList.remove("hidden");
  elements.progressMessage.textContent = message;
  elements.progressBar.style.width = `${Math.max(2, Math.min(progress, 100))}%`;
}

function showUploadProgress(message, progress = 5, isError = false) {
  elements.uploadProgress.classList.remove("hidden");
  elements.uploadProgressMessage.textContent = message;
  elements.uploadProgressBar.style.width = `${Math.max(2, Math.min(progress, 100))}%`;
  elements.uploadProgressBar.style.background = isError ? "#bf5f3f" : "#bf5f3f";
}

function showError(message) {
  showProgress(message, 100);
  elements.progressBar.style.background = "#bf5f3f";
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KiB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MiB`;
}

async function sha256(file) {
  const digest = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
  return hashDigest(digest);
}

function hashDigest(digest) {
  return [...new Uint8Array(digest)].map(value => value.toString(16).padStart(2, "0")).join("");
}

function isNetcdf(file) {
  return file.name.toLowerCase().endsWith(".nc") || /netcdf/i.test(file.type);
}

async function useFile(file) {
  if (!file) return;
  selectedFile = file;
  mappingReviewed = false;
  selectedInputMode = null;
  document.querySelectorAll('input[name="input-source"]').forEach(input => { input.checked = false; });
  elements.unitReview.classList.add("hidden");
  latestResult = null;
  elements.results.classList.add("hidden");
  elements.mappingSection.classList.add("hidden");
  elements.configPanel.classList.add("hidden");
  elements.drop.classList.add("hidden");
  elements.privacyNote.classList.add("hidden");
  elements.summary.classList.remove("hidden");
  elements.fileName.textContent = file.name;
  elements.fileDetails.textContent = `${formatBytes(file.size)} · reading locally`;
  elements.run.disabled = true;
  setWorkflowStep("data", false);
  activeStage = "upload";
  showUploadProgress("Reading climate table…", 12);

  try {
    const netcdf = isNetcdf(file);
    const data = netcdf ? await file.arrayBuffer() : await file.text();
    inputHash = hashDigest(await crypto.subtle.digest("SHA-256", netcdf ? data : await file.arrayBuffer()));
    showUploadProgress("Checking bioclimatic variables…", 55);
    const analysis = await callWorker(
      "analyze",
      netcdf ? { kind: "netcdf", data, name: file.name } : { kind: "table", text: data, name: file.name },
      netcdf ? [data] : [],
    );
    if (selectedFile !== file) return;
    renderAnalysis(analysis);
    const monthlyOnly = analysis.sources?.monthly && !analysis.sources?.bioclim;
    elements.fileDetails.textContent = analysis.kind === "netcdf"
      ? `${formatBytes(file.size)} · ${analysis.rows.toLocaleString()} ${monthlyOnly ? "grid cells" : "valid grid cells"} · ${analysis.grid.latitude} × ${analysis.grid.longitude}`
      : `${formatBytes(file.size)} · ${analysis.rows.toLocaleString()} rows · ${analysis.columns} columns`;
    showUploadProgress("Climate table ready.", 100);
    setTimeout(() => elements.uploadProgress.classList.add("hidden"), 700);
  } catch (error) {
    showUploadProgress(error.message, 100, true);
    elements.fileDetails.textContent = `${formatBytes(file.size)} · could not validate`;
  } finally {
    activeStage = null;
  }
}

function renderAnalysis(analysis) {
  completeAnalysis = analysis;
  const modes = Object.keys(analysis.sources || { bioclim: analysis });
  selectedInputMode = modes.length === 1 ? modes[0] : null;
  elements.mappingSection.classList.remove("hidden");
  elements.sourceChoice.classList.toggle("hidden", modes.length < 2);
  elements.detectionNote.classList.toggle("hidden", !analysis.detection);
  elements.detectionNote.textContent = analysis.detection || "";
  if (selectedInputMode) applyInputMode(selectedInputMode);
  else {
    elements.mappingBody.replaceChildren();
    elements.mappingSummary.textContent = "Choose which climate representation to use.";
    elements.mappingBadge.textContent = "Choice required";
    elements.mappingBadge.className = "status-badge error";
    elements.continueButton.classList.add("hidden");
  }
}

function applyInputMode(mode) {
  selectedInputMode = mode;
  mappingAnalysis = completeAnalysis.sources ? completeAnalysis.sources[mode] : completeAnalysis;
  mappingChoices = mappingAnalysis.mapping.map(item => item.status === "matched" ? item.target : null);
  mappingReviewed = false;
  elements.unitReview.classList.toggle("hidden", mode !== "monthly");
  if (mode === "monthly") {
    elements.temperatureUnit.value = mappingAnalysis.suggestedUnits?.temperature || "";
    const range = mappingAnalysis.temperatureRange;
    elements.temperatureUnitNote.textContent = range
      ? `${mappingAnalysis.suggestedUnits?.temperature ? "Guessed from values" : "Unit could not be guessed"} (range ${range.minimum.toFixed(1)} to ${range.maximum.toFixed(1)}).`
      : "";
  }
  elements.mappingTargetHeading.textContent = mode === "monthly" ? "Climate role" : "PaleoVeg variable";
  renderMappingTable();
}

function mappingState() {
  const counts = new Map();
  const targetInputs = new Map();
  mappingChoices.forEach((target, index) => {
    if (!target) return;
    counts.set(target, (counts.get(target) || 0) + 1);
    const inputs = targetInputs.get(target) || [];
    inputs.push(mappingAnalysis.mapping[index].input);
    targetInputs.set(target, inputs);
  });
  const conflicts = mappingChoices.map(target => Boolean(target) && counts.get(target) > 1);
  const missing = mappingAnalysis.required.filter(target => !counts.has(target));
  return { conflicts, missing, targetInputs };
}

function renderMappingTable() {
  const { conflicts, missing, targetInputs } = mappingState();
  elements.mappingBody.replaceChildren();
  mappingAnalysis.mapping.forEach((item, index) => {
    const target = mappingChoices[index];
    const automaticTarget = item.status === "matched" ? item.target : null;
    const row = document.createElement("tr");
    const status = conflicts[index]
      ? "Conflict — chosen more than once"
      : target === automaticTarget && target
        ? item.coverage ? `Matched automatically · ${item.coverage}/12 months` : "Matched automatically"
        : target
          ? "Matched manually"
          : "Not selected";
    row.className = conflicts[index] ? "row-conflict" : target && target !== automaticTarget ? "row-manual" : target ? "row-matched" : "row-unmatched";

    const inputCell = document.createElement("td");
    inputCell.textContent = item.input;
    row.append(inputCell);

    const mappingCell = document.createElement("td");
    const select = document.createElement("select");
    select.className = "mapping-select";
    select.setAttribute("aria-label", `PaleoVeg variable for ${item.input}`);
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = "Not used";
    select.append(empty);
    mappingAnalysis.required.forEach(variable => {
      const option = document.createElement("option");
      option.value = variable;
      option.textContent = selectedInputMode === "monthly" ? monthlyRoleLabel(variable) : variable;
      option.selected = variable === target;
      select.append(option);
    });
    select.addEventListener("change", () => {
      mappingChoices[index] = select.value || null;
      mappingReviewed = false;
      renderMappingTable();
    });
    mappingCell.append(select);
    row.append(mappingCell);

    const statusCell = document.createElement("td");
    statusCell.textContent = status;
    row.append(statusCell);
    elements.mappingBody.append(row);
  });

  const unitsValid = selectedInputMode !== "monthly" || Boolean(elements.temperatureUnit.value);
  const valid = missing.length === 0 && !conflicts.some(Boolean) && unitsValid;
  const messages = [];
  if (missing.length) messages.push(`Missing: ${missing.join(", ")}`);
  const conflictCount = conflicts.filter(Boolean).length;
  if (conflictCount) messages.push(`${conflictCount} conflicting column selections`);
  if (!unitsValid) messages.push("Choose the temperature unit");
  elements.mappingSummary.textContent = valid
    ? selectedInputMode === "monthly"
      ? "Detected a 12-month temperature and precipitation climate normal. PaleoVeg will derive BIO1 and BIO4–BIO19 locally after you confirm these mappings."
      : `All 17 required variables are assigned for ${mappingAnalysis.rows.toLocaleString()} observations.`
    : messages.join(" · ");
  elements.mappingBadge.textContent = valid ? `${mappingAnalysis.required.length} / ${mappingAnalysis.required.length} assigned` : "Needs attention";
  elements.mappingBadge.className = `status-badge ${valid ? "success" : "error"}`;
  elements.run.disabled = !valid;
  elements.continueButton.classList.toggle("hidden", !valid);
  elements.configPanel.classList.toggle("hidden", !(valid && mappingReviewed));

  const conflictDescriptions = [...targetInputs.entries()]
    .filter(([, inputs]) => inputs.length > 1)
    .map(([target, inputs]) => `Matching conflict: ${target} is selected for multiple input variables: ${inputs.map(input => `“${input}”`).join(" and ")}.`);
  const missingDescription = missing.length
    ? `Missing ${selectedInputMode === "monthly" ? "monthly climate roles" : "PaleoVeg variables"}: ${missing.join(", ")}. Choose an input variable for each missing target.`
    : "";
  const feedbackItems = [...conflictDescriptions, missingDescription].filter(Boolean);
  elements.mappingFeedback.replaceChildren();
  if (feedbackItems.length) {
    const list = document.createElement("ul");
    feedbackItems.forEach(message => {
      const item = document.createElement("li");
      item.textContent = message;
      list.append(item);
    });
    elements.mappingFeedback.append(list);
  } else {
    elements.mappingFeedback.textContent = selectedInputMode === "monthly"
      ? "All four monthly climate roles are assigned exactly once. BIOCLIM derivation will begin only after confirmation."
      : "All required PaleoVeg variables are assigned exactly once.";
  }
  elements.mappingFeedback.className = `mapping-feedback ${valid ? "" : "attention"}`;
}

function monthlyRoleLabel(role) {
  return ({
    tmean: "Monthly mean temperature",
    tmin: "Monthly minimum temperature",
    tmax: "Monthly maximum temperature",
    precipitation: "Monthly precipitation total",
  })[role] || role;
}

function continueToConfiguration() {
  const { conflicts, missing } = mappingState();
  if (missing.length || conflicts.some(Boolean) || (selectedInputMode === "monthly" && !elements.temperatureUnit.value)) return;
  mappingReviewed = true;
  renderMappingTable();
  setWorkflowStep("configure");
  warmupRuntime();
}

function selectedCo2Source() {
  return document.querySelector('input[name="co2-source"]:checked')?.value || "manual";
}

async function loadCo2Data() {
  if (!co2DataPromise) {
    co2DataPromise = fetch("assets/co2_ipcc_ar6.csv?v=1")
      .then(response => {
        if (!response.ok) throw new Error("The bundled IPCC AR6 CO₂ lookup could not be loaded.");
        return response.text();
      })
      .then(text => {
        const grouped = new Map();
        text.trim().split(/\r?\n/).slice(1).forEach(line => {
          const [, ageText, ppmText] = line.split(",");
          const age = Number(ageText); const ppm = Number(ppmText);
          const values = grouped.get(age) || [];
          values.push(ppm); grouped.set(age, values);
        });
        return [...grouped.entries()].sort((a, b) => a[0] - b[0])
          .map(([age, values]) => ({ age, ppm: values.reduce((sum, value) => sum + value, 0) / values.length }));
      });
  }
  return co2DataPromise;
}

async function lookupCo2(age) {
  const knots = await loadCo2Data();
  if (age < knots[0].age || age > knots.at(-1).age) {
    throw new Error(`Enter an age from ${knots[0].age.toFixed(3)} to ${knots.at(-1).age.toFixed(3)} ka BP; the observational record is not extrapolated.`);
  }
  let right = knots.findIndex(knot => knot.age >= age);
  if (knots[right].age === age) return { age, ppm: knots[right].ppm, interpolation: "Exact observation age", bracket: [knots[right]] };
  const left = right - 1;
  const fraction = (age - knots[left].age) / (knots[right].age - knots[left].age);
  return { age, ppm: knots[left].ppm + fraction * (knots[right].ppm - knots[left].ppm), interpolation: "Linear interpolation", bracket: [knots[left], knots[right]] };
}

function renderCo2Lookup(details) {
  const bracket = details.bracket.map(point => `${(point.age + 0.05).toFixed(3)} kyr / ${point.ppm.toFixed(1)} ppm`).join(" and ");
  elements.co2LookupDetails.innerHTML = `<dl>
    <dt>Requested age</dt><dd>${details.age.toFixed(3)} ka BP (before 1950)</dd>
    <dt>IPCC source age</dt><dd>${(details.age + 0.05).toFixed(3)} kyr before 2000</dd>
    <dt>Observation${details.bracket.length > 1 ? "s" : ""}</dt><dd>${bracket}</dd>
    <dt>Method</dt><dd>${details.interpolation}</dd>
    <dt>CO₂ used</dt><dd><strong>${details.ppm.toFixed(2)} ppm</strong></dd>
  </dl>`;
}

function co2Validation() {
  if (!elements.correction.checked) return { valid: true, ppm: 310 };
  if (selectedCo2Source() === "time") {
    const age = Number(elements.ageKaBp.value);
    if (!elements.ageKaBp.value.trim() || !Number.isFinite(age)) return { valid: false, message: "Enter a finite geological age in ka BP." };
    if (!co2LookupState || co2LookupState.age !== age) return { valid: false, message: "Looking up atmospheric CO₂…" };
    if (co2LookupState.error) return { valid: false, message: co2LookupState.error };
    return { valid: true, ppm: co2LookupState.ppm, age };
  }
  const ppm = Number(elements.co2Ppm.value);
  if (!elements.co2Ppm.value.trim() || !Number.isFinite(ppm)) {
    return { valid: false, message: "Enter a finite atmospheric CO₂ concentration." };
  }
  const legacyFactors = [0.28, 0.73, 0.20, 0.76, 1.00, 1.66, 1.66, 1.62, 1.62, 1.69, 1.15];
  const scale = (310 - ppm) / (310 - 185);
  if (legacyFactors.some(factor => 1 + scale * (factor - 1) <= 0)) {
    return { valid: false, message: "This concentration produces a zero or negative vegetation-class factor. Choose a value closer to 185–310 ppm." };
  }
  return { valid: true, ppm };
}

async function updateCo2Control() {
  elements.co2Control.classList.toggle("hidden", !elements.correction.checked);
  const timeMode = selectedCo2Source() === "time";
  elements.co2ManualControl.classList.toggle("hidden", timeMode);
  elements.co2TimeControl.classList.toggle("hidden", !timeMode);
  if (elements.correction.checked && timeMode) {
    const age = Number(elements.ageKaBp.value);
    co2LookupState = null;
    elements.co2LookupDetails.replaceChildren();
    elements.run.disabled = true;
    elements.co2Feedback.textContent = "Looking up atmospheric CO₂…";
    if (elements.ageKaBp.value.trim() && Number.isFinite(age)) {
      try {
        const details = await lookupCo2(age);
        if (Number(elements.ageKaBp.value) !== age || selectedCo2Source() !== "time") return;
        co2LookupState = details;
        renderCo2Lookup(details);
      } catch (error) {
        co2LookupState = { age, error: error.message };
      }
    }
  }
  const validation = co2Validation();
  elements.co2Feedback.textContent = validation.valid ? "" : validation.message;
  elements.run.disabled = !validation.valid || !mappingReviewed;
}

async function runPrediction() {
  if (!selectedFile) return;
  const co2 = co2Validation();
  if (!co2.valid) {
    updateCo2Control();
    return;
  }
  elements.run.disabled = true;
  activeStage = "prediction";
  elements.progressBar.style.background = "#bf5f3f";
  showProgress("Preparing local calculation…", 28);
  const output = document.querySelector('input[name="output"]:checked').value;
  try {
    const result = await callWorker("predict", {
      output,
      correction: elements.correction.checked,
      co2_ppm: elements.correction.checked && selectedCo2Source() === "manual" ? co2.ppm : null,
      age_ka_bp: elements.correction.checked && selectedCo2Source() === "time" ? co2.age : null,
      columnMapping: mappingChoices,
      inputMode: selectedInputMode,
      units: { temperature: elements.temperatureUnit.value, precipitation: elements.precipitationUnit.value },
      input_sha256: inputHash,
    });
    result.configuration.created = new Date().toISOString();
    result.configuration.input_sha256 = inputHash;
    latestResult = result;
    showProgress("Complete", 100);
    await renderResults(result);
    setTimeout(() => elements.progress.classList.add("hidden"), 500);
  } catch (error) {
    showError(error.message);
  } finally {
    activeStage = null;
    updateCo2Control();
  }
}

async function renderResults(result) {
  renderAreaStatistics(result.area_stats);

  const dominantOption = document.createElement("option");
  dominantOption.value = "dominant";
  dominantOption.textContent = "Dominant vegetation";
  elements.previewPicker.replaceChildren(dominantOption, ...result.classes.map((name, index) => {
    const option = document.createElement("option");
    option.value = `fractional:${index}`;
    option.textContent = `Fractional — ${name}`;
    return option;
  }));
  const hasMapPreview = Boolean(result.preview.coordinates || result.preview.grid);
  elements.mapPreview.classList.toggle("hidden", !hasMapPreview);
  if (hasMapPreview) await renderPreview();
  renderDownloads(result);
  setWorkflowStep("results");
}

function formatSquareKilometres(value) {
  return `${new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(value)} km²`;
}

function renderAreaStatistics(areaStats) {
  if (!areaStats) {
    elements.resultStats.replaceChildren();
    elements.resultStats.classList.add("hidden");
    return;
  }
  elements.resultStats.classList.remove("hidden");
  const rows = areaStats.classes.map(item => `
    <tr>
      <th scope="row">${escapeHtml(item.name)}</th>
      <td>${formatSquareKilometres(item.dominant_square_km)}</td>
      <td>${formatSquareKilometres(item.fractional_square_km)}</td>
    </tr>`).join("");
  elements.resultStats.innerHTML = `
    <div class="area-stats-heading">
      <div><h3>Spatial coverage</h3><p>Areas cover valid climate grid cells only.</p></div>
      <p><strong>${formatSquareKilometres(areaStats.total_square_km)}</strong><span>Total valid grid area</span></p>
    </div>
    <div class="area-stats-table-wrap">
      <table>
        <thead><tr><th>Vegetation type</th><th>Dominant area</th><th>Fractional area</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  })[character]);
}

async function worldBorders() {
  if (!worldBordersPromise) {
    worldBordersPromise = (async () => {
      const [topology, topologyClient] = await Promise.all([
        fetch(WORLD_TOPOLOGY_URL).then(response => {
          if (!response.ok) throw new Error("Could not load the preview basemap.");
          return response.json();
        }),
        import("https://cdn.jsdelivr.net/npm/topojson-client@3/+esm"),
      ]);
      return topologyClient.feature(topology, topology.objects.countries).features;
    })();
  }
  return worldBordersPromise;
}

function projectWorld(longitude, latitude, width, height) {
  return [
    ((longitude + 180) / 360) * width,
    ((90 - latitude) / 180) * height,
  ];
}

function drawGeometry(ctx, geometry, width, height) {
  const drawRing = ring => {
    let previousLongitude = null;
    ring.forEach(([longitude, latitude], index) => {
      const [x, y] = projectWorld(longitude, latitude, width, height);
      if (index === 0 || Math.abs(longitude - previousLongitude) > 180) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
      previousLongitude = longitude;
    });
  };
  if (geometry.type === "Polygon") geometry.coordinates.forEach(drawRing);
  if (geometry.type === "MultiPolygon") geometry.coordinates.forEach(polygon => polygon.forEach(drawRing));
}

function drawGridPreview(ctx, grid, width, height, mode, classIndex) {
  const latitude = grid.latitude;
  const longitude = grid.longitude;
  const latitudeStep = latitude.length > 1 ? Math.abs(latitude[1] - latitude[0]) : 1;
  const longitudeStep = longitude.length > 1 ? Math.abs(longitude[1] - longitude[0]) : 1;
  const cellWidth = Math.abs((longitudeStep / 360) * width) + 0.25;
  const cellHeight = Math.abs((latitudeStep / 180) * height) + 0.25;

  for (let latIndex = 0; latIndex < latitude.length; latIndex++) {
    for (let lonIndex = 0; lonIndex < longitude.length; lonIndex++) {
      const cell = latIndex * longitude.length + lonIndex;
      const dominant = grid.dominant[cell];
      if (dominant === 255) continue;
      const [centerX, centerY] = projectWorld(longitude[lonIndex], latitude[latIndex], width, height);
      if (mode === "dominant") {
        ctx.fillStyle = CLASS_COLORS[dominant];
      } else {
        const probability = grid.probabilities[cell * latestResult.classes.length + classIndex];
        ctx.fillStyle = colorWithProbability(CLASS_COLORS[classIndex], probability);
      }
      ctx.fillRect(centerX - cellWidth / 2, centerY - cellHeight / 2, cellWidth, cellHeight);
    }
  }
}

function drawBorders(ctx, borders, width, height) {
  if (!borders) return;
  ctx.strokeStyle = "rgba(23,56,45,.36)";
  ctx.lineWidth = 0.55;
  borders.forEach(country => {
    ctx.beginPath();
    drawGeometry(ctx, country.geometry, width, height);
    ctx.stroke();
  });
}

function renderLegend(mode, classIndex) {
  if (mode === "dominant") {
    elements.legend.innerHTML = latestResult.classes.map((name, index) =>
      `<span><i style="background:${CLASS_COLORS[index]}"></i>${escapeHtml(name)}</span>`).join("");
  } else {
    elements.legend.innerHTML = `<span>0</span><span style="height:10px;width:180px;background:linear-gradient(90deg,#f3f0e5,${CLASS_COLORS[classIndex]})"></span><span>1 probability</span>`;
  }
}

async function renderPreview() {
  if (!latestResult) return;
  const result = latestResult;
  const coordinates = latestResult.preview.coordinates;
  const grid = latestResult.preview.grid;
  if (!coordinates && !grid) {
    return;
  }
  elements.canvas.classList.remove("hidden");
  elements.mapEmpty.classList.add("hidden");
  const valid = coordinates ? coordinates.latitude.map((lat, index) => ({
    lat: Number(lat),
    lon: Number(coordinates.longitude[index]),
    index,
  })).filter(point => Number.isFinite(point.lat) && Number.isFinite(point.lon)) : [];
  if (!grid && !valid.length) {
    elements.canvas.classList.add("hidden");
    elements.mapEmpty.classList.remove("hidden");
    return;
  }

  const ctx = elements.canvas.getContext("2d");
  const { width, height } = elements.canvas;
  ctx.fillStyle = "#e9e9db";
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = "rgba(23,56,45,.1)";
  ctx.lineWidth = 1;
  for (let i = 1; i < 6; i++) {
    ctx.beginPath(); ctx.moveTo(0, height * i / 6); ctx.lineTo(width, height * i / 6); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(width * i / 6, 0); ctx.lineTo(width * i / 6, height); ctx.stroke();
  }
  const [mode, selectedClass] = elements.previewPicker.value.split(":");
  const classIndex = Number(selectedClass || 0);
  let borders = null;
  try {
    borders = await worldBorders();
    if (latestResult !== result) return;
  } catch (_error) {
    // The map remains useful if a visitor is offline or the basemap CDN is unavailable.
  }

  if (grid) {
    drawGridPreview(ctx, grid, width, height, mode, classIndex);
    drawBorders(ctx, borders, width, height);
    renderLegend(mode, classIndex);
    return;
  }

  drawBorders(ctx, borders, width, height);
  const radius = Math.max(2.4, Math.min(7, 210 / Math.sqrt(valid.length)));

  for (const point of valid) {
    const [x, y] = projectWorld(point.lon, point.lat, width, height);
    if (mode === "dominant") {
      const index = latestResult.classes.indexOf(latestResult.preview.dominant[point.index]);
      ctx.fillStyle = CLASS_COLORS[Math.max(0, index)];
    } else {
      const probability = latestResult.preview.probabilities[point.index][classIndex];
      ctx.fillStyle = colorWithProbability(CLASS_COLORS[classIndex], probability);
    }
    ctx.beginPath(); ctx.arc(x, y, radius + 1.2, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(255,255,255,.88)";
    ctx.fill();
    if (mode === "dominant") {
      const index = latestResult.classes.indexOf(latestResult.preview.dominant[point.index]);
      ctx.fillStyle = CLASS_COLORS[Math.max(0, index)];
    } else {
      const probability = latestResult.preview.probabilities[point.index][classIndex];
      ctx.fillStyle = colorWithProbability(CLASS_COLORS[classIndex], probability);
    }
    ctx.beginPath(); ctx.arc(x, y, radius, 0, Math.PI * 2); ctx.fill();
  }

  renderLegend(mode, classIndex);
}

function colorWithProbability(hex, probability) {
  const rgb = [1, 3, 5].map(offset => parseInt(hex.slice(offset, offset + 2), 16));
  const base = [243, 240, 229];
  const p = Math.max(0, Math.min(1, probability));
  return `rgb(${rgb.map((value, index) => Math.round(base[index] + (value - base[index]) * p)).join(",")})`;
}

function saveDownload(filename, content, type) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  downloadUrls.push(url);
  const link = document.createElement("a");
  link.href = url; link.download = filename; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

function makeDownload(label, description, filename, format, type) {
  const button = document.createElement("button");
  button.type = "button"; button.className = "download-button";
  button.innerHTML = `<span>${escapeHtml(label)}<small>${escapeHtml(description)}</small></span><span>↓</span>`;
  button.addEventListener("click", async () => {
    button.disabled = true;
    activeStage = "export";
    showProgress(`Preparing ${label}…`, 95);
    try {
      const exported = await callWorker("export", { format });
      saveDownload(filename, exported.content, exported.type || type);
      showProgress("Download ready", 100);
      setTimeout(() => elements.progress.classList.add("hidden"), 700);
    } catch (error) {
      showError(error.message);
    } finally {
      activeStage = null;
      button.disabled = false;
    }
  });
  return button;
}

function renderDownloads(result) {
  downloadUrls.forEach(url => URL.revokeObjectURL(url));
  downloadUrls = [];
  elements.downloads.replaceChildren();
  const stem = selectedFile.name.replace(/\.[^.]+$/, "");
  if (result.exports.includes("dominant-csv")) elements.downloads.append(makeDownload("Dominant vegetation", "CSV · generated on download", `${stem}_paleoveg_dominant.csv`, "dominant-csv", "text/csv"));
  if (result.exports.includes("probabilities-csv")) elements.downloads.append(makeDownload("Class probabilities", "CSV · 11 classes · generated on download", `${stem}_paleoveg_probabilities.csv`, "probabilities-csv", "text/csv"));
  if (result.exports.includes("probabilities-npy")) elements.downloads.append(makeDownload("Class probabilities", "NumPy array · generated on download", `${stem}_paleoveg_probabilities.npy`, "probabilities-npy", "application/octet-stream"));
  if (result.exports.includes("netcdf")) elements.downloads.append(makeDownload("PaleoVeg result", "NetCDF · generated on download", `${stem}_paleoveg.nc`, "netcdf", "application/x-netcdf"));
  const configButton = document.createElement("button");
  configButton.type = "button"; configButton.className = "download-button";
  configButton.innerHTML = "<span>Run configuration<small>JSON</small></span><span>↓</span>";
  configButton.addEventListener("click", () => saveDownload(`${stem}_paleoveg_config.json`, JSON.stringify(result.configuration, null, 2), "application/json"));
  elements.downloads.append(configButton);
  if (result.preview.coordinates || result.preview.grid) {
    const pngButton = document.createElement("button");
    pngButton.type = "button"; pngButton.className = "download-button";
    pngButton.innerHTML = "<span>Map preview<small>PNG · generated on download</small></span><span>↓</span>";
    pngButton.addEventListener("click", () => elements.canvas.toBlob(blob => saveDownload(`${stem}_paleoveg_preview.png`, blob, "image/png"), "image/png"));
    elements.downloads.append(pngButton);
  }
}

elements.input.addEventListener("change", () => useFile(elements.input.files[0]));
elements.replace.addEventListener("click", () => elements.input.click());
elements.drop.addEventListener("dragover", event => { event.preventDefault(); elements.drop.classList.add("dragging"); });
elements.drop.addEventListener("dragleave", () => elements.drop.classList.remove("dragging"));
elements.drop.addEventListener("drop", event => {
  event.preventDefault(); elements.drop.classList.remove("dragging"); useFile(event.dataTransfer.files[0]);
});
elements.run.addEventListener("click", runPrediction);
elements.continueButton.addEventListener("click", continueToConfiguration);
stepButtons.forEach(button => button.addEventListener("click", () => setWorkflowStep(button.dataset.step)));
elements.backToData.addEventListener("click", () => setWorkflowStep("data"));
elements.resultsBackConfigure.addEventListener("click", () => setWorkflowStep("configure"));
elements.resultsBackData.addEventListener("click", () => setWorkflowStep("data"));
elements.previewPicker.addEventListener("change", renderPreview);
document.querySelectorAll('input[name="input-source"]').forEach(input => input.addEventListener("change", () => applyInputMode(input.value)));
elements.temperatureUnit.addEventListener("change", renderMappingTable);
elements.correction.addEventListener("change", updateCo2Control);
elements.co2Ppm.addEventListener("input", updateCo2Control);
elements.ageKaBp.addEventListener("input", updateCo2Control);
document.querySelectorAll('input[name="co2-source"]').forEach(input => input.addEventListener("change", updateCo2Control));
document.querySelector("#copy-bibtex").addEventListener("click", async event => {
  const button = event.currentTarget;
  const bibtex = `@software{schlueter_2025_paleoveg,
  author    = {Schlüter, Philipp},
  title     = {PaleoVeg},
  version   = {0.1.2},
  year      = {2025},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.15222520},
  url       = {https://doi.org/10.5281/zenodo.15222520}
}`;
  await navigator.clipboard.writeText(bibtex);
  button.textContent = "Copied";
  setTimeout(() => { button.textContent = "Copy BibTeX"; }, 1600);
});

registerServiceWorker();
updateStepNavigation();
