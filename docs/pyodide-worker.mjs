import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v314.0.2/full/pyodide.mjs";
import "./cache-manifest.js";

const WHEEL_NAME = "paleoveg-0.2.0-py3-none-any.whl";
const MODEL_ASSET_URL = new URL("assets/model.pkl.bz2", self.location.href).href;
const MODEL_PATH = "/tmp/paleoveg-model.pkl.bz2";
const REQUIRED_COLUMNS = [
  "bio1", "bio4", "bio5", "bio6", "bio7", "bio8", "bio9", "bio10",
  "bio11", "bio12", "bio13", "bio14", "bio15", "bio16", "bio17", "bio18", "bio19",
];
const CLASS_NAMES = [
  "Evergreen Needleleaf Forest", "Evergreen Broadleaf Forest",
  "Deciduous Needleleaf Forest", "Deciduous Broadleaf Forest",
  "Mixed Forest", "Woodland", "Wooded Grassland", "Closed Shrubland",
  "Open Shrubland", "Grassland", "Bare Ground",
];

let pyodidePromise;
let modelPromise;
let currentInput = null;
let currentPrediction = null;

function status(message, progress) {
  self.postMessage({ type: "status", message, progress });
}

async function cachedAsset(url) {
  if (!self.caches) return { response: await fetch(url), persisted: Promise.resolve() };
  try {
    const cache = await caches.open(self.PALEOVEG_RUNTIME_CACHE);
    const cached = await cache.match(url);
    if (cached) return { response: cached, persisted: Promise.resolve() };
    const response = await fetch(url);
    if (!response.ok) return { response, persisted: Promise.resolve() };
    return { response, persisted: cache.put(url, response.clone()).catch(() => {}) };
  } catch {
    return { response: await fetch(url), persisted: Promise.resolve() };
  }
}

async function getPyodide() {
  if (!pyodidePromise) {
    pyodidePromise = (async () => {
      status("Loading browser Python…", 8);
      const pyodide = await loadPyodide();
      status("Loading scientific Python packages…", 16);
      await pyodide.loadPackage(["micropip", "numpy", "pandas", "scikit-learn"]);
      const wheelUrl = new URL(`assets/${WHEEL_NAME}?v=runtime-cache-5`, self.location.href).href;
      status("Installing the local PaleoVeg browser package…", 25);
      const { response, persisted } = await cachedAsset(wheelUrl);
      if (!response.ok) throw new Error(`PaleoVeg package download failed (${response.status} ${response.statusText}).`);
      await persisted;
      pyodide.globals.set("paleoveg_wheel_url", wheelUrl);
      await pyodide.runPythonAsync(`
import micropip
await micropip.install(paleoveg_wheel_url, deps=False)
`);
      return pyodide;
    })().catch(error => {
      pyodidePromise = undefined;
      throw error;
    });
  }
  return pyodidePromise;
}

async function writeResponseToFile(response, pyodide) {
  const total = Number(response.headers.get("content-length")) || 184599816;
  const reader = response.body.getReader();
  const stream = pyodide.FS.open(MODEL_PATH, "w");
  let received = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      pyodide.FS.write(stream, value, 0, value.length, received);
      received += value.length;
      const fraction = Math.min(received / total, 1);
      status(`Downloading model… ${Math.round(fraction * 100)}%`, 30 + fraction * 38);
    }
  } finally {
    pyodide.FS.close(stream);
  }
}

async function ensureModel(pyodide) {
  if (!modelPromise) {
    modelPromise = (async () => {
      status("Loading PaleoVeg model (176 MiB)…", 30);
      const { response, persisted } = await cachedAsset(MODEL_ASSET_URL);
      if (!response.ok || !response.body) {
        throw new Error(`Model download failed (${response.status} ${response.statusText}).`);
      }
      await writeResponseToFile(response, pyodide);
      await persisted;
      status("Decompressing classifier… 0%", 70);
      pyodide.globals.set("paleoveg_model_path", MODEL_PATH);
      pyodide.globals.set("report_model_load_progress", fraction => {
        if (fraction >= 0.995) {
          status("Restoring random-forest classifier…", 78);
        } else {
          status(`Decompressing classifier… ${Math.round(fraction * 100)}%`, 70 + fraction * 8);
        }
      });
      await pyodide.runPythonAsync(`
from paleoveg import load_model
_paleoveg_model = load_model(
    paleoveg_model_path,
    progress_callback=report_model_load_progress,
)
`);
      status("Classifier loaded. Preparing prediction…", 79);
    })().catch(error => {
      modelPromise = undefined;
      throw error;
    });
  }
  return modelPromise;
}

async function warmup() {
  const pyodide = await getPyodide();
  await ensureModel(pyodide);
  return { ready: true };
}

async function analyze(payload) {
  if (!payload.kind && String(payload.name || "").toLowerCase().endsWith(".nc")) {
    throw new Error("This NetCDF upload needs the current PaleoVeg browser application. Reload the page, then select the file again.");
  }
  if (payload.kind === "netcdf") return analyzeNetcdf(payload);
  const pyodide = await getPyodide();
  currentInput = { kind: "table", text: payload.text, name: payload.name };
  pyodide.globals.set("input_text", payload.text);
  const result = await pyodide.runPythonAsync(`
import io
import json
import numpy as np
import pandas as pd
from paleoveg import MONTHLY_ROLES, REQUIRED_COLUMNS, match_bioclim_columns, match_monthly_column_groups

def _read_paleoveg_table(text):
    try:
        frame = pd.read_csv(io.StringIO(text), sep=None, engine="python")
    except Exception as exc:
        raise ValueError(f"Could not parse the table: {exc}") from exc
    if frame.empty:
        raise ValueError("The table has no data rows.")
    if len(frame.columns) < 2:
        raise ValueError("Only one column was detected. Please use a comma, tab, or semicolon delimiter.")
    return frame

_input_frame = _read_paleoveg_table(input_text)
_mapping_report = match_bioclim_columns(_input_frame.columns)
_valid_targets = {
    item["target"] for item in _mapping_report if item["status"] == "matched"
}
_bio_analysis = {
    "kind": "table",
    "rows": len(_input_frame),
    "columns": len(_input_frame.columns),
    "required": REQUIRED_COLUMNS,
    "mapping": _mapping_report,
    "matched": len(_valid_targets),
    "missing": [name for name in REQUIRED_COLUMNS if name not in _valid_targets],
    "ambiguous": [item for item in _mapping_report if item["status"] == "ambiguous"],
}
_monthly_mapping = match_monthly_column_groups(_input_frame.columns)
_monthly_targets = {item["target"] for item in _monthly_mapping if item["status"] == "matched"}
_temperature_columns = [
    column for item in _monthly_mapping
    if item["target"] in ("tmean", "tmin", "tmax") and item["coverage"] == 12
    for column in item["columns"]
]
_temperature_values = pd.to_numeric(
    _input_frame[_temperature_columns].stack(), errors="coerce"
).replace([np.inf, -np.inf], np.nan).dropna() if _temperature_columns else pd.Series(dtype=float)
_temperature_min = float(_temperature_values.min()) if len(_temperature_values) else None
_temperature_max = float(_temperature_values.max()) if len(_temperature_values) else None
_temperature_guess = (
    "celsius" if _temperature_min is not None and _temperature_min >= -100 and _temperature_max <= 100
    else "kelvin" if _temperature_min is not None and _temperature_min >= 200 and _temperature_max <= 400
    else None
)
_monthly_analysis = {
    "kind": "table", "rows": len(_input_frame), "columns": len(_input_frame.columns),
    "required": MONTHLY_ROLES, "mapping": _monthly_mapping,
    "matched": len(_monthly_targets),
    "missing": [role for role in MONTHLY_ROLES if role not in _monthly_targets],
    "ambiguous": [item for item in _monthly_mapping if item["status"] == "ambiguous"],
    "suggestedUnits": {"temperature": _temperature_guess, "precipitation": "mm-month"},
    "temperatureRange": {"minimum": _temperature_min, "maximum": _temperature_max} if _temperature_min is not None else None,
}
_sources = {}
if not _bio_analysis["missing"]:
    _sources["bioclim"] = _bio_analysis
if len([item for item in _monthly_mapping if item["coverage"] == 12]) >= 4:
    _sources["monthly"] = _monthly_analysis
if not _sources:
    _sources["bioclim"] = _bio_analysis
_analysis = {
    "kind": "table", "rows": len(_input_frame), "columns": len(_input_frame.columns),
    "sources": _sources,
    "detection": (
        "Detected supplied BIOCLIM variables and 12-month temperature and precipitation climate normals. Choose which representation to use."
        if len(_sources) > 1 else
        "Detected 12-month temperature and precipitation climate normals. Review the proposed mappings before PaleoVeg derives BIO1 and BIO4–BIO19."
        if "monthly" in _sources else None
    ),
}
json.dumps(_analysis)
`);
  return JSON.parse(result);
}

function canonicalBioName(name) {
  const match = String(name).toLowerCase().replace(/[^a-z0-9]/g, "").match(/^(?:bio|bioclim|bioclimatic)0*(\d{1,2})$/);
  const target = match ? `bio${Number(match[1])}` : null;
  return REQUIRED_COLUMNS.includes(target) ? target : null;
}

function canonicalMonthlyRole(name) {
  const compact = String(name).toLowerCase().replace(/[^a-z0-9]/g, "");
  if (["tmp", "tmean", "temp", "temperature", "meantemperature"].includes(compact)) return "tmean";
  if (["tmn", "tmin", "mintemp", "minimumtemperature"].includes(compact)) return "tmin";
  if (["tmx", "tmax", "maxtemp", "maximumtemperature"].includes(compact)) return "tmax";
  if (["pre", "prec", "pr", "ppt", "precip", "precipitation"].includes(compact)) return "precipitation";
  return null;
}

function flatNetcdfValues(values) {
  if (!Array.isArray(values) || !Array.isArray(values[0])) return Float32Array.from(values);
  const length = values.reduce((total, part) => total + part.length, 0);
  const flattened = new Float32Array(length);
  let offset = 0;
  values.forEach(part => { flattened.set(part, offset); offset += part.length; });
  return flattened;
}

function netcdfMissingValues(variable) {
  return variable.attributes
    .filter(attribute => ["_FillValue", "missing_value"].includes(attribute.name))
    .flatMap(attribute => {
      if (Array.isArray(attribute.value) || ArrayBuffer.isView(attribute.value)) return Array.from(attribute.value, Number);
      return [Number(attribute.value)];
    })
    .filter(Number.isFinite);
}

function isNetcdfMissing(value, missingValues) {
  return !Number.isFinite(value) || missingValues.some(missing => value === missing);
}

function normalizeSpatialGrid(reader, variable, latitudeName, longitudeName, latCount, lonCount) {
  const dimensionNames = variable.dimensions.map(index => reader.dimensions[index].name);
  const shape = variable.dimensions.map(index => reader.dimensions[index].size);
  if (!dimensionNames.includes(latitudeName) || !dimensionNames.includes(longitudeName)) {
    throw new Error(`${variable.name} must use the latitude and longitude dimensions.`);
  }
  dimensionNames.forEach((name, index) => {
    if (name !== latitudeName && name !== longitudeName && shape[index] !== 1) {
      throw new Error(`${variable.name} has unsupported non-spatial dimension ${name} with size ${shape[index]}.`);
    }
  });
  const values = flatNetcdfValues(reader.getDataVariable(variable));
  const expected = shape.reduce((product, size) => product * size, 1);
  if (values.length !== expected) throw new Error(`${variable.name} has inconsistent dimension metadata.`);
  const positions = Object.fromEntries(dimensionNames.map((name, index) => [name, index]));
  const strides = shape.map((_, index) => shape.slice(index + 1).reduce((a, b) => a * b, 1));
  const missingValues = netcdfMissingValues(variable);
  const normalized = new Float32Array(latCount * lonCount);
  for (let lat = 0; lat < latCount; lat++) for (let lon = 0; lon < lonCount; lon++) {
    const indexes = new Array(shape.length).fill(0);
    indexes[positions[latitudeName]] = lat;
    indexes[positions[longitudeName]] = lon;
    const source = indexes.reduce((sum, value, index) => sum + value * strides[index], 0);
    normalized[lat * lonCount + lon] = isNetcdfMissing(values[source], missingValues) ? NaN : values[source];
  }
  return normalized;
}

const EARTH_RADIUS_KM = 6371.0088;

function coordinateCellBoundaries(coordinates, { clamp = null, singletonWidth = 1 } = {}) {
  if (coordinates.length === 0) return new Float64Array();
  const boundaries = new Float64Array(coordinates.length + 1);
  if (coordinates.length === 1) {
    boundaries[0] = coordinates[0] - singletonWidth / 2;
    boundaries[1] = coordinates[0] + singletonWidth / 2;
  } else {
    boundaries[0] = coordinates[0] - (coordinates[1] - coordinates[0]) / 2;
    for (let index = 1; index < coordinates.length; index++) {
      boundaries[index] = (coordinates[index - 1] + coordinates[index]) / 2;
    }
    const last = coordinates.length - 1;
    boundaries[last + 1] = coordinates[last] + (coordinates[last] - coordinates[last - 1]) / 2;
  }
  if (clamp) {
    for (let index = 0; index < boundaries.length; index++) {
      boundaries[index] = Math.max(clamp[0], Math.min(clamp[1], boundaries[index]));
    }
  }
  return boundaries;
}

function gridAreaStatistics(latitudes, longitudes, validIndices, dominant, probabilities) {
  const latitudeBounds = coordinateCellBoundaries(latitudes, { clamp: [-90, 90] });
  const longitudeBounds = coordinateCellBoundaries(longitudes);
  const cellAreas = new Float64Array(latitudes.length * longitudes.length);
  for (let latitudeIndex = 0; latitudeIndex < latitudes.length; latitudeIndex++) {
    const latitudeFactor = Math.abs(
      Math.sin(latitudeBounds[latitudeIndex + 1] * Math.PI / 180)
      - Math.sin(latitudeBounds[latitudeIndex] * Math.PI / 180),
    );
    for (let longitudeIndex = 0; longitudeIndex < longitudes.length; longitudeIndex++) {
      const longitudeWidth = Math.abs(longitudeBounds[longitudeIndex + 1] - longitudeBounds[longitudeIndex]) * Math.PI / 180;
      cellAreas[latitudeIndex * longitudes.length + longitudeIndex] = EARTH_RADIUS_KM ** 2 * longitudeWidth * latitudeFactor;
    }
  }

  const dominantSquareKm = new Float64Array(CLASS_NAMES.length);
  const fractionalSquareKm = new Float64Array(CLASS_NAMES.length);
  let totalSquareKm = 0;
  for (let row = 0; row < validIndices.length; row++) {
    const area = cellAreas[validIndices[row]];
    totalSquareKm += area;
    dominantSquareKm[dominant[row]] += area;
    for (let classIndex = 0; classIndex < CLASS_NAMES.length; classIndex++) {
      fractionalSquareKm[classIndex] += area * probabilities[row * CLASS_NAMES.length + classIndex];
    }
  }
  return {
    total_square_km: totalSquareKm,
    classes: CLASS_NAMES.map((name, index) => ({
      name,
      dominant_square_km: dominantSquareKm[index],
      fractional_square_km: fractionalSquareKm[index],
    })),
  };
}

function analyzeMonthlyNetcdf(reader, payload, latitudeName, longitudeName) {
  const variableNames = reader.variables.map(variable => variable.name);
  const timeName = variableNames.find(name => /^time$/i.test(name));
  if (!timeName) throw new Error("Monthly NetCDF input needs a time coordinate with 12 climatological months.");
  const roleVariables = new Map();
  reader.variables.forEach(variable => {
    const role = canonicalMonthlyRole(variable.name);
    if (role) roleVariables.set(role, variable);
  });
  const roles = ["tmean", "tmin", "tmax", "precipitation"];
  const missingRoles = roles.filter(role => !roleVariables.has(role));
  if (missingRoles.length) throw new Error(`Monthly climate normal is missing: ${missingRoles.join(", ")}.`);
  const latitudes = Float64Array.from(reader.getDataVariable(latitudeName));
  const longitudes = Float64Array.from(reader.getDataVariable(longitudeName));
  const timeValues = reader.getDataVariable(timeName);
  if (timeValues.length !== 12) throw new Error("PaleoVeg accepts exactly 12 climatological months, not an unaggregated multi-year series.");
  const cellCount = latitudes.length * longitudes.length;
  const monthlyLayers = new Map();
  const monthlyShapes = new Map();
  roles.forEach(role => {
    const variable = roleVariables.get(role);
    const shape = variable.dimensions.map(index => reader.dimensions[index].size);
    const dimensionNames = variable.dimensions.map(index => reader.dimensions[index].name);
    if (!dimensionNames.includes(timeName) || !dimensionNames.includes(latitudeName) || !dimensionNames.includes(longitudeName)) {
      throw new Error(`${variable.name} must use the time, latitude, and longitude dimensions.`);
    }
    const values = flatNetcdfValues(reader.getDataVariable(variable));
    if (values.length !== cellCount * 12) throw new Error(`${variable.name} does not contain 12 complete spatial layers.`);
    monthlyLayers.set(variable.name, values);
    monthlyShapes.set(variable.name, { shape, dimensionNames, timeName, missingValues: netcdfMissingValues(variable) });
  });
  const mapping = roles.map(role => ({ input: roleVariables.get(role).name, target: role, status: "matched", coverage: 12 }));
  let temperatureMinimum = Infinity;
  let temperatureMaximum = -Infinity;
  for (const role of ["tmean", "tmin", "tmax"]) {
    const source = roleVariables.get(role).name;
    const values = monthlyLayers.get(source);
    const missingValues = monthlyShapes.get(source).missingValues;
    for (const value of values) {
      if (isNetcdfMissing(value, missingValues)) continue;
      temperatureMinimum = Math.min(temperatureMinimum, value);
      temperatureMaximum = Math.max(temperatureMaximum, value);
    }
  }
  const temperatureGuess = temperatureMinimum >= -100 && temperatureMaximum <= 100
    ? "celsius"
    : temperatureMinimum >= 200 && temperatureMaximum <= 400
      ? "kelvin"
      : null;
  const suggestedUnits = { temperature: temperatureGuess, precipitation: "mm-month" };
  const temperatureRange = Number.isFinite(temperatureMinimum)
    ? { minimum: temperatureMinimum, maximum: temperatureMaximum }
    : null;
  const spatialDimensions = [
    { name: longitudeName, size: longitudes.length },
    { name: latitudeName, size: latitudes.length },
  ];
  const coordinate = (name, dimension) => {
    const variable = reader.variables.find(item => item.name === name);
    return { name, dimensions: [dimension], type: variable.type, attributes: variable.attributes, values: reader.getDataVariable(variable) };
  };
  currentInput = {
    kind: "netcdf-monthly", name: payload.name, latitudes, longitudes, latitudeName, longitudeName,
    monthlyLayers, monthlyShapes, mapping, validCells: cellCount,
    netcdfTemplate: {
      dimensions: spatialDimensions, dimensionIds: [1, 0],
      coordinateVariables: [coordinate(longitudeName, 0), coordinate(latitudeName, 1)],
      globalAttributes: reader.globalAttributes,
    },
  };
  return {
    kind: "netcdf", rows: cellCount, columns: 4,
    sources: { monthly: { kind: "netcdf", rows: cellCount, columns: 4, required: roles, mapping, matched: 4, missing: [], ambiguous: [], suggestedUnits, temperatureRange } },
    detection: "Detected 12-month mean, minimum, and maximum temperature plus monthly precipitation totals. Review the proposed mappings before PaleoVeg derives BIO1 and BIO4–BIO19.",
    grid: { latitude: latitudes.length, longitude: longitudes.length },
  };
}

async function analyzeNetcdf(payload) {
  status("Reading NetCDF metadata…", 20);
  const { NetCDFReader } = await import("https://cdn.jsdelivr.net/npm/netcdfjs@4.0.0/+esm");
  let reader;
  try {
    reader = new NetCDFReader(payload.data);
  } catch (error) {
    throw new Error(`Could not read this NetCDF file. PaleoVeg currently supports classic NetCDF files: ${error.message}`);
  }

  const variableNames = reader.variables.map(variable => variable.name);
  const latitudeName = variableNames.find(name => /^(lat|latitude)$/i.test(name));
  const longitudeName = variableNames.find(name => /^(lon|longitude)$/i.test(name));
  if (!latitudeName || !longitudeName) {
    throw new Error("NetCDF input needs latitude and longitude coordinate variables named lat/lon or latitude/longitude.");
  }

  const sourceForTarget = new Map();
  variableNames.forEach(name => {
    const target = canonicalBioName(name);
    if (target) {
      if (sourceForTarget.has(target)) {
        throw new Error(`NetCDF contains multiple variables that match ${target}.`);
      }
      sourceForTarget.set(target, name);
    }
  });
  let monthlyAnalysis = null;
  let monthlyAlternative = null;
  if (["tmean", "tmin", "tmax", "precipitation"].every(role => variableNames.some(name => canonicalMonthlyRole(name) === role))) {
    monthlyAnalysis = analyzeMonthlyNetcdf(reader, payload, latitudeName, longitudeName);
    monthlyAlternative = currentInput;
  }
  const missing = REQUIRED_COLUMNS.filter(name => !sourceForTarget.has(name));
  if (missing.length) {
    if (monthlyAnalysis) return monthlyAnalysis;
    throw new Error(`NetCDF is missing BIOCLIM variables and a complete monthly climate normal. Missing BIO layers: ${missing.join(", ")}.`);
  }

  const latitudes = Float64Array.from(reader.getDataVariable(latitudeName));
  const longitudes = Float64Array.from(reader.getDataVariable(longitudeName));
  const cellCount = latitudes.length * longitudes.length;
  const layers = new Map();
  for (const target of REQUIRED_COLUMNS) {
    status(`Reading ${sourceForTarget.get(target)}…`, 22 + (layers.size / REQUIRED_COLUMNS.length) * 23);
    const variable = reader.variables.find(item => item.name === sourceForTarget.get(target));
    layers.set(sourceForTarget.get(target), normalizeSpatialGrid(
      reader, variable, latitudeName, longitudeName, latitudes.length, longitudes.length,
    ));
  }

  let validCells = 0;
  for (let cell = 0; cell < cellCount; cell++) {
    let valid = true;
    for (const target of REQUIRED_COLUMNS) {
      if (!Number.isFinite(layers.get(sourceForTarget.get(target))[cell])) {
        valid = false;
        break;
      }
    }
    if (valid) validCells++;
  }
  if (!validCells) throw new Error("The NetCDF file has no grid cells with all 17 finite BIO variables.");

  const mapping = REQUIRED_COLUMNS.map(target => ({
    input: sourceForTarget.get(target), target, status: "matched",
  }));
  const coordinate = (name, dimension) => {
    const variable = reader.variables.find(item => item.name === name);
    return { name, dimensions: [dimension], type: variable.type, attributes: variable.attributes, values: reader.getDataVariable(variable) };
  };
  currentInput = {
    kind: "netcdf",
    name: payload.name,
    latitudes,
    longitudes,
    latitudeName,
    longitudeName,
    layers,
    mapping,
    validCells,
    netcdfTemplate: {
      dimensions: [
        { name: longitudeName, size: longitudes.length },
        { name: latitudeName, size: latitudes.length },
      ],
      // Prediction grids are normalized to latitude-major, longitude-minor.
      dimensionIds: [1, 0],
      coordinateVariables: [coordinate(longitudeName, 0), coordinate(latitudeName, 1)],
      globalAttributes: reader.globalAttributes,
    },
    monthlyAlternative,
  };
  const bioclimSource = {
    kind: "netcdf",
    rows: validCells,
    columns: REQUIRED_COLUMNS.length,
    required: REQUIRED_COLUMNS,
    mapping,
    matched: REQUIRED_COLUMNS.length,
    missing: [],
    ambiguous: [],
    grid: { latitude: latitudes.length, longitude: longitudes.length },
  };
  if (!monthlyAnalysis) return bioclimSource;
  return {
    ...bioclimSource,
    sources: { bioclim: bioclimSource, monthly: monthlyAnalysis.sources.monthly },
    detection: "Detected supplied BIOCLIM variables and 12-month temperature and precipitation climate normals. Choose which representation to use.",
  };
}

function selectedNetcdfLayers(columnMapping) {
  if (columnMapping.length !== currentInput.mapping.length) {
    throw new Error("The submitted column mapping does not match the NetCDF BIO layers.");
  }
  const layers = new Map();
  const sourceNames = new Map();
  columnMapping.forEach((target, index) => {
    if (!REQUIRED_COLUMNS.includes(target)) throw new Error("All NetCDF BIO layers must be assigned before prediction.");
    if (layers.has(target)) throw new Error(`PaleoVeg variable ${target} is selected more than once.`);
    const source = currentInput.mapping[index].input;
    layers.set(target, currentInput.layers.get(source));
    sourceNames.set(target, source);
  });
  const missing = REQUIRED_COLUMNS.filter(target => !layers.has(target));
  if (missing.length) throw new Error(`Missing PaleoVeg variable assignments: ${missing.join(", ")}.`);
  layers.sourceNames = sourceNames;
  return layers;
}

function buildNetcdfDominantCsv(validIndices, dominant, selectedLayers) {
  const { latitudes, longitudes } = currentInput;
  const header = [
    currentInput.latitudeName,
    currentInput.longitudeName,
    ...REQUIRED_COLUMNS.map(target => selectedLayers.sourceNames.get(target)),
    "Dominant Class",
  ];
  const rows = new Array(validIndices.length + 1);
  rows[0] = header.join(",");
  for (let row = 0; row < validIndices.length; row++) {
    const cell = validIndices[row];
    const latIndex = Math.floor(cell / longitudes.length);
    const lonIndex = cell % longitudes.length;
    const values = REQUIRED_COLUMNS.map(target => selectedLayers.get(target)[cell]);
    rows[row + 1] = [latitudes[latIndex], longitudes[lonIndex], ...values, CLASS_NAMES[dominant[row]]].join(",");
  }
  return rows.join("\n");
}

function normalizeMonthlyGrid(values, metadata, latCount, lonCount) {
  const output = new Float32Array(latCount * lonCount * 12);
  const positions = Object.fromEntries(metadata.dimensionNames.map((name, index) => [name, index]));
  const strides = metadata.shape.map((_, index) => metadata.shape.slice(index + 1).reduce((a, b) => a * b, 1));
  for (let lat = 0; lat < latCount; lat++) for (let lon = 0; lon < lonCount; lon++) for (let month = 0; month < 12; month++) {
    const indexes = new Array(metadata.shape.length).fill(0);
    indexes[positions[metadata.timeName]] = month;
    indexes[positions[currentInput.latitudeName]] = lat;
    indexes[positions[currentInput.longitudeName]] = lon;
    const source = indexes.reduce((sum, value, index) => sum + value * strides[index], 0);
    const value = values[source];
    output[(lat * lonCount + lon) * 12 + month] = isNetcdfMissing(value, metadata.missingValues) ? NaN : value;
  }
  return output;
}

async function deriveMonthlyNetcdf(payload, pyodide) {
  const roles = ["tmean", "tmin", "tmax", "precipitation"];
  if (!["celsius", "kelvin"].includes(payload.units?.temperature)) throw new Error("Choose the monthly temperature unit.");
  if (payload.columnMapping.length !== currentInput.mapping.length) throw new Error("The submitted monthly mapping is incomplete.");
  const selected = new Map();
  payload.columnMapping.forEach((role, index) => {
    if (!roles.includes(role) || selected.has(role)) throw new Error("Each monthly climate role must be assigned exactly once.");
    selected.set(role, currentInput.mapping[index].input);
  });
  if (selected.size !== 4) throw new Error("Mean, minimum, maximum temperature and precipitation are required.");
  const monthlyVariableMapping = Object.fromEntries(selected);
  const rows = currentInput.latitudes.length * currentInput.longitudes.length;
  for (const role of roles) {
    const source = selected.get(role);
    const normalized = normalizeMonthlyGrid(currentInput.monthlyLayers.get(source), currentInput.monthlyShapes.get(source), currentInput.latitudes.length, currentInput.longitudes.length);
    if (payload.units?.temperature === "kelvin" && role !== "precipitation") {
      for (let index = 0; index < normalized.length; index++) if (Number.isFinite(normalized[index])) normalized[index] -= 273.15;
    }
    pyodide.FS.writeFile(`/tmp/paleoveg-${role}.f32`, new Uint8Array(normalized.buffer));
  }
  pyodide.globals.set("monthly_grid_rows", rows);
  status("Deriving 17 BIOCLIM variables from the monthly climate normal…", 74);
  await pyodide.runPythonAsync(`
import numpy as np
from paleoveg import REQUIRED_COLUMNS, derive_bioclimatic_variables
def _monthly_file(role):
    return np.fromfile(f"/tmp/paleoveg-{role}.f32", dtype=np.float32).reshape(monthly_grid_rows, 12)
_derived_bioclim = derive_bioclimatic_variables(
    _monthly_file("tmean"), _monthly_file("tmin"), _monthly_file("tmax"), _monthly_file("precipitation")
).astype(np.float32)
_derived_bioclim.tofile("/tmp/paleoveg-derived-bioclim.f32")
`);
  const values = new Float32Array(pyodide.FS.readFile("/tmp/paleoveg-derived-bioclim.f32").buffer);
  const layers = new Map();
  REQUIRED_COLUMNS.forEach((target, feature) => {
    const layer = new Float32Array(rows);
    for (let row = 0; row < rows; row++) layer[row] = values[row * REQUIRED_COLUMNS.length + feature];
    layers.set(target, layer);
  });
  let validCells = 0;
  for (let row = 0; row < rows; row++) if (Number.isFinite(layers.get("bio1")[row])) validCells++;
  currentInput.layers = layers;
  currentInput.mapping = REQUIRED_COLUMNS.map(target => ({ input: target, target, status: "derived" }));
  currentInput.validCells = validCells;
  currentInput.kind = "netcdf";
  const derivedPayload = { ...payload, columnMapping: REQUIRED_COLUMNS, inputMode: "monthly" };
  const result = await predictNetcdf(derivedPayload, pyodide);
  result.configuration.input_mode = "monthly";
  result.configuration.bioclim_derivation = "PaleoVeg model-compatible monthly normals v1";
  result.configuration.monthly_variable_mapping = monthlyVariableMapping;
  result.configuration.monthly_units = { temperature: "degrees Celsius", precipitation: "mm/month" };
  currentPrediction.configuration = result.configuration;
  return result;
}

// A compact NetCDF-3 classic writer keeps the browser build fully static. It
// writes the source grid's dimensions and coordinate variables without needing
// another Python package or a server-side conversion step.
const NETCDF_TYPE = { byte: 1, char: 2, short: 3, int: 4, float: 5, double: 6 };
const NETCDF_TYPE_SIZE = { 1: 1, 2: 1, 3: 2, 4: 4, 5: 4, 6: 8 };

class NetcdfWriter {
  constructor() { this.bytes = []; }
  writeUint8(value) { this.bytes.push(value & 0xff); }
  writeInt8(value) { this.writeUint8(value); }
  writeUint32(value) {
    this.writeUint8(value >>> 24); this.writeUint8(value >>> 16); this.writeUint8(value >>> 8); this.writeUint8(value);
  }
  writeInt16(value) { this.writeUint8(value >> 8); this.writeUint8(value); }
  writeInt32(value) { this.writeUint32(value >>> 0); }
  writeFloat32(value) {
    const buffer = new ArrayBuffer(4); new DataView(buffer).setFloat32(0, value, false);
    this.writeBytes(new Uint8Array(buffer));
  }
  writeFloat64(value) {
    const buffer = new ArrayBuffer(8); new DataView(buffer).setFloat64(0, value, false);
    this.writeBytes(new Uint8Array(buffer));
  }
  writeBytes(bytes) { for (const byte of bytes) this.bytes.push(byte); }
  pad() { while (this.bytes.length % 4) this.writeUint8(0); }
  writeName(name) {
    const encoded = new TextEncoder().encode(String(name));
    this.writeUint32(encoded.length); this.writeBytes(encoded); this.pad();
  }
  toUint8Array() { return Uint8Array.from(this.bytes); }
}

function netcdfAttribute(name, type, value) { return { name, type, value }; }

function netcdfAttributeValues(attribute) {
  if (attribute.type === "char") return new TextEncoder().encode(String(attribute.value));
  return Array.isArray(attribute.value) ? attribute.value : [attribute.value];
}

function writeNetcdfValues(writer, type, values) {
  const typeId = NETCDF_TYPE[type];
  if (typeId === 2) {
    writer.writeBytes(values instanceof Uint8Array ? values : new TextEncoder().encode(String(values)));
    return;
  }
  for (const value of values) {
    if (typeId === 1) writer.writeInt8(value);
    else if (typeId === 3) writer.writeInt16(value);
    else if (typeId === 4) writer.writeInt32(value);
    else if (typeId === 5) writer.writeFloat32(value);
    else if (typeId === 6) writer.writeFloat64(value);
  }
}

function writeNetcdfAttributes(writer, attributes) {
  const supported = attributes.filter(attribute => NETCDF_TYPE[attribute.type]);
  if (!supported.length) { writer.writeUint32(0); writer.writeUint32(0); return; }
  writer.writeUint32(12); writer.writeUint32(supported.length);
  for (const attribute of supported) {
    const values = netcdfAttributeValues(attribute);
    writer.writeName(attribute.name); writer.writeUint32(NETCDF_TYPE[attribute.type]); writer.writeUint32(values.length);
    writeNetcdfValues(writer, attribute.type, values); writer.pad();
  }
}

function netcdfDataBytes(variable) {
  const typeSize = NETCDF_TYPE_SIZE[NETCDF_TYPE[variable.type]];
  const count = variable.type === "char"
    ? netcdfAttributeValues({ type: "char", value: variable.values }).length
    : variable.values.length;
  return Math.ceil((count * typeSize) / 4) * 4;
}

function buildNetcdfResult(dominantGrid, probabilityGrid, payload) {
  const template = currentInput.netcdfTemplate;
  const dimensions = template.dimensions;
  const dimensionIds = template.dimensionIds;
  const classAttributeValue = CLASS_NAMES.map(name => name.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "")).join(" ");
  const sharedAttributes = [
    netcdfAttribute("coordinates", "char", `${currentInput.longitudeName} ${currentInput.latitudeName}`),
    netcdfAttribute("source", "char", "PaleoVeg browser prediction"),
  ];
  const variables = template.coordinateVariables.map(variable => ({ ...variable, values: variable.values }));
  if (payload.output === "both" || payload.output === "dominant") {
    const classCodes = new Int8Array(dominantGrid.length);
    for (let index = 0; index < dominantGrid.length; index++) classCodes[index] = dominantGrid[index] === 255 ? 0 : dominantGrid[index] + 1;
    variables.push({
      name: "dominant_vegetation", type: "byte", dimensions: dimensionIds, values: classCodes,
      attributes: [
        ...sharedAttributes,
        netcdfAttribute("long_name", "char", "dominant PaleoVeg vegetation class"),
        netcdfAttribute("_FillValue", "byte", [0]),
        netcdfAttribute("valid_min", "byte", [1]), netcdfAttribute("valid_max", "byte", [CLASS_NAMES.length]),
        netcdfAttribute("flag_meanings", "char", classAttributeValue),
      ],
    });
  }
  if (payload.output === "both" || payload.output === "probabilities") {
    CLASS_NAMES.forEach((className, classIndex) => {
      const values = new Float32Array(dominantGrid.length);
      for (let cell = 0; cell < dominantGrid.length; cell++) values[cell] = probabilityGrid[cell * CLASS_NAMES.length + classIndex];
      variables.push({
        name: `fractional_${className.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "")}`,
        type: "float", dimensions: dimensionIds, values,
        attributes: [...sharedAttributes, netcdfAttribute("long_name", "char", `PaleoVeg fractional vegetation: ${className}`), netcdfAttribute("units", "char", "1")],
      });
    });
  }
  const predictionConfiguration = currentPrediction?.configuration || {};
  const globalAttributes = [
    ...template.globalAttributes.filter(attribute => NETCDF_TYPE[attribute.type]),
    netcdfAttribute("title", "char", "PaleoVeg vegetation prediction"),
    netcdfAttribute("source_input_file", "char", currentInput.name),
    netcdfAttribute("source_input_sha256", "char", payload.input_sha256 || "not available"),
    netcdfAttribute("paleoveg_version", "char", "0.2.0"),
    netcdfAttribute("paleoveg_model_version", "char", "v0.1.2"),
    netcdfAttribute("paleoveg_c3_c4_correction", "char", String(Boolean(payload.correction))),
    netcdfAttribute("paleoveg_co2_ppm", "double", predictionConfiguration.co2_ppm),
    netcdfAttribute("paleoveg_co2_source", "char", predictionConfiguration.co2_source),
    ...(predictionConfiguration.age_ka_bp == null ? [] : [
      netcdfAttribute("paleoveg_age_ka_bp", "double", predictionConfiguration.age_ka_bp),
      netcdfAttribute("paleoveg_age_reference_year", "int", 1950),
      netcdfAttribute("paleoveg_co2_source_age_kyr_before_2000", "double", predictionConfiguration.co2_lookup.source_age_kyr_before_2000),
      netcdfAttribute("paleoveg_co2_interpolation", "char", predictionConfiguration.co2_lookup.interpolation),
      netcdfAttribute("paleoveg_co2_dataset_doi", "char", predictionConfiguration.co2_lookup.dataset_doi),
    ]),
    netcdfAttribute("history", "char", "Created locally by PaleoVeg browser application"),
  ];
  const writeHeader = begins => {
    const writer = new NetcdfWriter();
    writer.writeBytes(new TextEncoder().encode("CDF\u0001")); writer.writeUint32(0);
    writer.writeUint32(10); writer.writeUint32(dimensions.length);
    dimensions.forEach(dimension => { writer.writeName(dimension.name); writer.writeUint32(dimension.size); });
    writeNetcdfAttributes(writer, globalAttributes);
    writer.writeUint32(11); writer.writeUint32(variables.length);
    variables.forEach((variable, index) => {
      writer.writeName(variable.name); writer.writeUint32(variable.dimensions.length);
      variable.dimensions.forEach(dimension => writer.writeUint32(dimension));
      writeNetcdfAttributes(writer, variable.attributes || []);
      writer.writeUint32(NETCDF_TYPE[variable.type]); writer.writeUint32(netcdfDataBytes(variable)); writer.writeUint32(begins[index] || 0);
    });
    return writer.toUint8Array();
  };
  const provisional = writeHeader([]);
  let offset = provisional.length;
  const begins = variables.map(variable => { const begin = offset; offset += netcdfDataBytes(variable); return begin; });
  const header = writeHeader(begins);
  const output = new NetcdfWriter(); output.writeBytes(header);
  variables.forEach(variable => { writeNetcdfValues(output, variable.type, variable.values); output.pad(); });
  return output.toUint8Array();
}

async function predictNetcdf(payload, pyodide) {
  const columnMapping = payload.columnMapping || [];
  const selectedLayers = selectedNetcdfLayers(columnMapping);
  const { latitudes, longitudes } = currentInput;
  const cellCount = latitudes.length * longitudes.length;
  const validIndices = new Uint32Array(currentInput.validCells);
  const features = new Float32Array(currentInput.validCells * REQUIRED_COLUMNS.length);
  let validRow = 0;
  status("Preparing valid NetCDF grid cells…", 76);
  for (let cell = 0; cell < cellCount; cell++) {
    let valid = true;
    for (const target of REQUIRED_COLUMNS) {
      if (!Number.isFinite(selectedLayers.get(target)[cell])) {
        valid = false;
        break;
      }
    }
    if (!valid) continue;
    validIndices[validRow] = cell;
    for (let feature = 0; feature < REQUIRED_COLUMNS.length; feature++) {
      features[validRow * REQUIRED_COLUMNS.length + feature] = selectedLayers.get(REQUIRED_COLUMNS[feature])[cell];
    }
    validRow++;
  }
  pyodide.FS.writeFile("/tmp/paleoveg-netcdf-input.f32", new Uint8Array(features.buffer));
  pyodide.globals.set("netcdf_row_count", validRow);
  pyodide.globals.set("apply_correction", Boolean(payload.correction));
  pyodide.globals.set("requested_co2_json", JSON.stringify(payload.co2_ppm ?? null));
  pyodide.globals.set("requested_age_json", JSON.stringify(payload.age_ka_bp ?? null));
  status("Calculating vegetation probabilities…", 80);
  const co2Resolution = JSON.parse(await pyodide.runPythonAsync(`
import json
import numpy as np
from paleoveg import CLASS_NAMES
from paleoveg.co2 import _co2_lookup_details
from paleoveg.predictor import _competition_factors_for_co2

_requested_co2_ppm = json.loads(requested_co2_json)
_requested_age_ka_bp = json.loads(requested_age_json)
_netcdf_features = np.fromfile("/tmp/paleoveg-netcdf-input.f32", dtype=np.float32).reshape(netcdf_row_count, 17)
_netcdf_probabilities = _paleoveg_model.predict_proba(_netcdf_features)
_resolved_co2_ppm, _factors = _competition_factors_for_co2(
    CLASS_NAMES, apply_correction, _requested_co2_ppm, _requested_age_ka_bp
)
if apply_correction:
    _netcdf_probabilities *= _factors
    _netcdf_probabilities /= _netcdf_probabilities.sum(axis=1, keepdims=True)
_netcdf_dominant = _netcdf_probabilities.argmax(axis=1).astype(np.uint8)
_netcdf_probabilities.astype(np.float32).tofile("/tmp/paleoveg-netcdf-probabilities.f32")
_netcdf_dominant.tofile("/tmp/paleoveg-netcdf-dominant.u8")
json.dumps({
    "co2_ppm": _resolved_co2_ppm,
    "lookup": _co2_lookup_details(_requested_age_ka_bp) if _requested_age_ka_bp is not None else None,
})
`));

  const probabilities = new Float32Array(pyodide.FS.readFile("/tmp/paleoveg-netcdf-probabilities.f32").buffer);
  const dominant = new Uint8Array(pyodide.FS.readFile("/tmp/paleoveg-netcdf-dominant.u8").buffer);
  const dominantGrid = new Uint8Array(cellCount).fill(255);
  const probabilityGrid = new Float32Array(cellCount * CLASS_NAMES.length).fill(NaN);
  const counts = Object.fromEntries(CLASS_NAMES.map(name => [name, 0]));
  for (let row = 0; row < validRow; row++) {
    const classIndex = dominant[row];
    counts[CLASS_NAMES[classIndex]]++;
    const cell = validIndices[row];
    dominantGrid[cell] = classIndex;
    probabilityGrid.set(probabilities.subarray(row * CLASS_NAMES.length, (row + 1) * CLASS_NAMES.length), cell * CLASS_NAMES.length);
  }
  const areaStats = gridAreaStatistics(latitudes, longitudes, validIndices.subarray(0, validRow), dominant, probabilities);
  const configuration = {
    paleoveg_version: "0.2.0",
    model_version: "v0.1.2",
    c3_c4_correction: Boolean(payload.correction),
    co2_ppm: co2Resolution.co2_ppm,
    co2_source: !payload.correction ? "modern_baseline" : payload.age_ka_bp != null ? "ipcc_ar6_time_lookup" : payload.co2_ppm != null ? "manual" : "legacy_default",
    age_ka_bp: payload.age_ka_bp ?? null,
    co2_lookup: co2Resolution.lookup,
    output: payload.output,
    input_file: currentInput.name,
    input_rows: validRow,
    input_variables: REQUIRED_COLUMNS,
    grid: { latitude: latitudes.length, longitude: longitudes.length, valid_cells: validRow },
    variable_mapping: currentInput.mapping.map((item, index) => ({
      input: item.input,
      target: columnMapping[index],
      status: item.target === columnMapping[index] ? "matched" : "manual",
    })),
  };
  currentPrediction = {
    kind: "netcdf", validIndices, dominant, probabilities, dominantGrid,
    probabilityGrid, selectedLayers, configuration, payload,
  };
  return {
    rows: validRow,
    grid: { latitude: latitudes.length, longitude: longitudes.length, valid_cells: validRow },
    classes: CLASS_NAMES,
    class_counts: counts,
    area_stats: areaStats,
    preview: {
      coordinates: null,
      grid: {
        latitude: latitudes,
        longitude: longitudes,
        dominant: dominantGrid,
        probabilities: probabilityGrid,
      },
    },
    configuration,
    exports: [
      ...(payload.output === "both" || payload.output === "dominant" ? ["dominant-csv"] : []),
      ...(payload.output === "both" || payload.output === "probabilities" ? ["probabilities-npy"] : []),
      "netcdf",
    ],
  };
}

async function predict(payload) {
  if (!currentInput) throw new Error("Choose an input file first.");
  if (payload.inputMode === "monthly" && !["celsius", "kelvin"].includes(payload.units?.temperature)) throw new Error("Choose the monthly temperature unit.");
  const pyodide = await getPyodide();
  await ensureModel(pyodide);
  if (currentInput.kind === "netcdf" && payload.inputMode === "monthly" && currentInput.monthlyAlternative) {
    currentInput = currentInput.monthlyAlternative;
  }
  if (currentInput.kind === "netcdf-monthly") {
    const result = await deriveMonthlyNetcdf(payload, pyodide);
    status("Preparing preview…", 94);
    return result;
  }
  if (currentInput.kind === "netcdf") {
    const result = await predictNetcdf(payload, pyodide);
    status("Preparing preview…", 94);
    return result;
  }
  status("Calculating vegetation probabilities…", 80);
  pyodide.globals.set("prediction_output", payload.output);
  pyodide.globals.set("apply_correction", Boolean(payload.correction));
  pyodide.globals.set("requested_co2_json", JSON.stringify(payload.co2_ppm ?? null));
  pyodide.globals.set("requested_age_json", JSON.stringify(payload.age_ka_bp ?? null));
  pyodide.globals.set("input_file_name", currentInput.name);
  pyodide.globals.set("column_mapping_json", JSON.stringify(payload.columnMapping || []));
  pyodide.globals.set("input_mode", payload.inputMode || "bioclim");
  pyodide.globals.set("monthly_temperature_unit", payload.units?.temperature || "celsius");
  const result = await pyodide.runPythonAsync(`
import json
import re
import numpy as np
import pandas as pd
import paleoveg
from paleoveg import (
    CLASS_NAMES, MODEL_SHA256, MODEL_URL, MODEL_VERSION, REQUIRED_COLUMNS,
    MONTHLY_ROLES, derive_bioclimatic_variables, match_bioclim_columns,
    match_monthly_column_groups, predict,
)
from paleoveg.co2 import _co2_lookup_details
from paleoveg.predictor import _resolve_co2_ppm

requested_co2_ppm = json.loads(requested_co2_json)
requested_age_ka_bp = json.loads(requested_age_json)
_column_mapping = json.loads(column_mapping_json)
_source_frame = _input_frame
if input_mode == "monthly":
    _automatic_mapping_report = match_monthly_column_groups(_input_frame.columns)
    if len(_column_mapping) != len(_automatic_mapping_report):
        raise ValueError("The submitted monthly mapping does not match the input table.")
    _allowed_targets = MONTHLY_ROLES
else:
    _automatic_mapping_report = match_bioclim_columns(_input_frame.columns)
    if len(_column_mapping) != len(_input_frame.columns):
        raise ValueError("The submitted column mapping does not match the input table.")
    _allowed_targets = REQUIRED_COLUMNS
_invalid_targets = [target for target in _column_mapping if target is not None and target not in _allowed_targets]
if _invalid_targets:
    raise ValueError(f"Invalid variables in column mapping: {_invalid_targets}")
_mapping_counts = {target: _column_mapping.count(target) for target in _allowed_targets}
_duplicate_targets = [target for target, count in _mapping_counts.items() if count > 1]
if _duplicate_targets:
    raise ValueError(f"Variables selected more than once: {_duplicate_targets}")
_missing_targets = [target for target, count in _mapping_counts.items() if count == 0]
if _missing_targets:
    raise ValueError(f"Missing variable assignments: {_missing_targets}")

_mapping_report = []
for _item, _target in zip(_automatic_mapping_report, _column_mapping):
    _mapping_report.append({
        "input": _item["input"],
        "target": _target,
        "status": (
            "matched" if _target == _item["target"] and _item["status"] == "matched"
            else "manual" if _target is not None
            else "unmatched"
        ),
    })

if input_mode == "monthly":
    _groups_by_role = {
        target: _automatic_mapping_report[index]["columns"]
        for index, target in enumerate(_column_mapping) if target is not None
    }
    _monthly = {
        role: _input_frame[_groups_by_role[role]].apply(pd.to_numeric, errors="coerce").to_numpy()
        for role in MONTHLY_ROLES
    }
    if monthly_temperature_unit == "kelvin":
        for _role in ("tmean", "tmin", "tmax"):
            _monthly[_role] = _monthly[_role] - 273.15
    _derived = derive_bioclimatic_variables(
        _monthly["tmean"], _monthly["tmin"], _monthly["tmax"], _monthly["precipitation"]
    )
    _valid_rows = np.isfinite(_derived).all(axis=1)
    if not _valid_rows.any():
        raise ValueError("No rows contain a complete 12-month climate normal.")
    _normalized = pd.DataFrame(_derived[_valid_rows], columns=REQUIRED_COLUMNS)
    _input_frame = _source_frame.loc[_valid_rows].reset_index(drop=True)
else:
    _normalized = _input_frame.copy()
    _normalized.columns = [target if target is not None else column for column, target in zip(_input_frame.columns, _column_mapping)]
_prediction = predict(
    _normalized,
    dominant="include",
    c3_c4_correction=apply_correction,
    co2_ppm=requested_co2_ppm,
    age_ka_bp=requested_age_ka_bp,
    model=_paleoveg_model,
    normalize_columns=False,
)

_reserved_output_columns = set(CLASS_NAMES + ["Dominant Class"])
_reserved_collisions = [
    str(column) for column in _input_frame.columns
    if str(column) in _reserved_output_columns
]
if _reserved_collisions:
    raise ValueError(
        "Input columns conflict with PaleoVeg output columns: "
        + ", ".join(_reserved_collisions)
    )

_original_input = _input_frame.reset_index(drop=True)
_probability_frame = pd.concat(
    [_original_input, _prediction[CLASS_NAMES].reset_index(drop=True)], axis=1
)
_dominant_frame = pd.concat(
    [_original_input, _prediction[["Dominant Class"]].reset_index(drop=True)], axis=1
)

def _coordinate_column(columns, candidates):
    for column in columns:
        compact = re.sub(r"[^a-z0-9]", "", str(column).lower())
        if compact in candidates:
            return column
    return None

_lat_column = _coordinate_column(_input_frame.columns, {"lat", "latitude"})
_lon_column = _coordinate_column(_input_frame.columns, {"lon", "lng", "long", "longitude"})
_has_coordinates = _lat_column is not None and _lon_column is not None
_preview_limit = 20000
_preview_indices = np.linspace(
    0, len(_prediction) - 1, min(len(_prediction), _preview_limit), dtype=int
)
_preview_probabilities = _prediction.iloc[_preview_indices][CLASS_NAMES]
def _json_numbers(series):
    return [float(value) if pd.notna(value) else None for value in series]

_coordinates = None
if _has_coordinates:
    _latitudes = _json_numbers(pd.to_numeric(_input_frame.iloc[_preview_indices][_lat_column], errors="coerce"))
    _longitudes = _json_numbers(pd.to_numeric(_input_frame.iloc[_preview_indices][_lon_column], errors="coerce"))
    if any(lat is not None and lon is not None for lat, lon in zip(_latitudes, _longitudes)):
        _coordinates = {"latitude": _latitudes, "longitude": _longitudes}

_preview = {
    "coordinates": _coordinates,
    "dominant": _prediction.iloc[_preview_indices]["Dominant Class"].tolist(),
    "probabilities": _preview_probabilities.to_numpy().tolist(),
}
_counts = _prediction["Dominant Class"].value_counts().reindex(CLASS_NAMES, fill_value=0)
_run_result = {
    "rows": len(_prediction),
    "classes": CLASS_NAMES,
    "class_counts": _counts.to_dict(),
    "preview": _preview,
    "exports": (
        (["dominant-csv"] if prediction_output in ("both", "dominant") else [])
        + (["probabilities-csv"] if prediction_output in ("both", "probabilities") else [])
    ),
    "configuration": {
        "paleoveg_version": paleoveg.__version__,
        "model_version": MODEL_VERSION,
        "model_url": MODEL_URL,
        "model_sha256": MODEL_SHA256,
        "c3_c4_correction": bool(apply_correction),
        "co2_ppm": _resolve_co2_ppm(apply_correction, requested_co2_ppm, requested_age_ka_bp),
        "co2_source": (
            "modern_baseline" if not apply_correction
            else "ipcc_ar6_time_lookup" if requested_age_ka_bp is not None
            else "manual" if requested_co2_ppm is not None
            else "legacy_default"
        ),
        "age_ka_bp": requested_age_ka_bp,
        "co2_lookup": _co2_lookup_details(requested_age_ka_bp) if requested_age_ka_bp is not None else None,
        "output": prediction_output,
        "input_file": input_file_name,
        "input_rows": len(_input_frame),
        "input_mode": input_mode,
        "bioclim_derivation": "PaleoVeg model-compatible monthly normals v1" if input_mode == "monthly" else None,
        "monthly_units": {"temperature": monthly_temperature_unit, "precipitation": "mm/month"} if input_mode == "monthly" else None,
        "input_variables": REQUIRED_COLUMNS,
        "variable_mapping": _mapping_report,
    },
}
_serialized_result = json.dumps(_run_result, allow_nan=False)
_input_frame = _source_frame
_serialized_result
`);
  const parsed = JSON.parse(result);
  currentPrediction = { kind: "table", payload, configuration: parsed.configuration };
  status("Preparing preview…", 94);
  return parsed;
}

async function exportPrediction(format) {
  if (!currentPrediction) throw new Error("Run PaleoVeg before requesting a download.");
  const pyodide = await getPyodide();
  if (currentPrediction.kind === "netcdf") {
    const prediction = currentPrediction;
    if (format === "dominant-csv") {
      status("Preparing dominant-vegetation CSV…", 96);
      return { content: buildNetcdfDominantCsv(prediction.validIndices, prediction.dominant, prediction.selectedLayers), type: "text/csv" };
    }
    if (format === "probabilities-npy") {
      status("Preparing NumPy probability array…", 96);
      pyodide.globals.set("netcdf_export_rows", prediction.probabilities.length / CLASS_NAMES.length);
      pyodide.FS.writeFile("/tmp/paleoveg-export-probabilities.f32", new Uint8Array(prediction.probabilities.buffer));
      await pyodide.runPythonAsync(`
import numpy as np
np.save("/tmp/paleoveg-export-probabilities.npy", np.fromfile("/tmp/paleoveg-export-probabilities.f32", dtype=np.float32).reshape(netcdf_export_rows, 11))
`);
      return { content: pyodide.FS.readFile("/tmp/paleoveg-export-probabilities.npy"), type: "application/octet-stream" };
    }
    if (format === "netcdf") {
      status("Writing NetCDF result…", 96);
      return { content: buildNetcdfResult(prediction.dominantGrid, prediction.probabilityGrid, prediction.payload), type: "application/x-netcdf" };
    }
  }
  if (format !== "dominant-csv" && format !== "probabilities-csv") throw new Error("Unsupported download format.");
  status(`Preparing ${format === "dominant-csv" ? "dominant vegetation" : "class probabilities"} CSV…`, 96);
  pyodide.globals.set("paleoveg_export_format", format);
  const content = await pyodide.runPythonAsync(`
_dominant_frame.to_csv(index=False) if paleoveg_export_format == "dominant-csv" else _probability_frame.to_csv(index=False)
`);
  return { content, type: "text/csv" };
}

self.onmessage = async (event) => {
  const { id, action, payload = {} } = event.data;
  try {
    let result;
    if (action === "analyze") result = await analyze(payload);
    else if (action === "warmup") result = await warmup();
    else if (action === "predict") result = await predict(payload);
    else if (action === "export") result = await exportPrediction(payload.format);
    else throw new Error(`Unknown worker action: ${action}`);
    self.postMessage({ type: "result", id, result });
  } catch (error) {
    self.postMessage({
      type: "error",
      id,
      error: error?.message || String(error),
      detail: error?.stack || "",
    });
  }
};
