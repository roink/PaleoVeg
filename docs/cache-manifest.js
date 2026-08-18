// Keep this version in sync whenever a deployed runtime asset changes.
self.PALEOVEG_CACHE_VERSION = "runtime-cache-4";
self.PALEOVEG_RUNTIME_CACHE = `paleoveg-runtime-${self.PALEOVEG_CACHE_VERSION}`;
self.PALEOVEG_APP_CACHE = `paleoveg-app-${self.PALEOVEG_CACHE_VERSION}`;
self.PALEOVEG_PYODIDE_PREFIX = "https://cdn.jsdelivr.net/pyodide/v314.0.2/full/";
self.PALEOVEG_PRECACHE = [
  "./",
  "index.html",
  "styles.css",
  "app.js?v=runtime-cache-4",
  "pyodide-worker.mjs?v=runtime-cache-4",
  "cache-manifest.js",
  "assets/PaleoVeg-0.2.0-py3-none-any.whl",
  "assets/co2_ipcc_ar6.csv",
];
