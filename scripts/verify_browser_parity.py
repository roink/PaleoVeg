"""Compare native and Pyodide predictions for a fixed reference observation.

Run this after placing model.pkl.bz2 in docs/assets. Selenium requires a local
Chrome/Chromium installation. The script serves docs/ on an ephemeral port and
executes the same checked-in wheel used by GitHub Pages.
"""

import io
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from paleoveg import CLASS_NAMES, load_model, predict


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
MODEL_PATH = DOCS / "assets" / "model.pkl.bz2"
INPUT_COLUMNS = [
    "latitude", "longitude", "Bio01", "bio04", "bio5", "bio6", "bio7",
    "bio8", "bio9", "bio10", "bio11", "bio12", "bio13", "bio14",
    "bio15", "bio16", "bio17", "bio18", "bio19",
]
INPUT_VALUES = [
    50, 10, 10, 500, 20, 0, 20, 10, 10, 12, 5, 700, 100, 20, 30, 250,
    80, 150, 120,
]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def main():
    if not MODEL_PATH.exists():
        raise SystemExit(
            "Missing docs/assets/model.pkl.bz2; download the v0.1.2 release asset first."
        )

    source = pd.DataFrame([INPUT_VALUES], columns=INPUT_COLUMNS)
    scenarios = [
        {"correction": False, "co2_ppm": None, "age_ka_bp": None},
        {"correction": True, "co2_ppm": None, "age_ka_bp": None},
        {"correction": True, "co2_ppm": 247.5, "age_ka_bp": None},
        {"correction": True, "co2_ppm": 310, "age_ka_bp": None},
        {"correction": True, "co2_ppm": None, "age_ka_bp": 20},
    ]
    model = load_model(MODEL_PATH)
    native = [
        predict(
            source,
            model=model,
            c3_c4_correction=scenario["correction"],
            co2_ppm=scenario["co2_ppm"],
            age_ka_bp=scenario["age_ka_bp"],
        )[CLASS_NAMES]
        for scenario in scenarios
    ]
    csv_text = source.to_csv(index=False)

    handler = lambda *args, **kwargs: QuietHandler(  # noqa: E731
        *args, directory=str(DOCS), **kwargs
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--js-flags=--max-old-space-size=4096")
    driver = webdriver.Chrome(options=options)
    driver.set_script_timeout(600)
    try:
        driver.get(f"http://127.0.0.1:{server.server_port}/index.html")
        browser_result = driver.execute_async_script(
            """
            const [csvText, scenarios, done] = arguments;
            const worker = new Worker("pyodide-worker.mjs", {type: "module"});
            const csvResults = [];
            let scenarioIndex = 0;
            let columnMapping = [];
            const runScenario = () => {
              const scenario = scenarios[scenarioIndex];
              worker.postMessage({
                id: 100 + scenarioIndex,
                action: "predict",
                payload: {output: "probabilities", inputMode: "bioclim", columnMapping, ...scenario},
              });
            };
            worker.onmessage = ({data}) => {
              if (data.type === "result" && data.id === 1) {
                const analysis = data.result.sources?.bioclim || data.result;
                columnMapping = analysis.mapping.map(item => item.target);
                worker.postMessage({id: 2, action: "warmup", payload: {}});
              } else if (data.type === "result" && data.id === 2) {
                runScenario();
              } else if (data.type === "result" && data.id === 100 + scenarioIndex) {
                worker.postMessage({id: 200 + scenarioIndex, action: "export", payload: {format: "probabilities-csv"}});
              } else if (data.type === "result" && data.id === 200 + scenarioIndex) {
                csvResults.push(data.result.content);
                scenarioIndex += 1;
                if (scenarioIndex < scenarios.length) runScenario();
                else done(JSON.stringify({csvResults}));
              } else if (data.type === "error") {
                done(JSON.stringify({error: data.error}));
              }
            };
            worker.postMessage({id: 1, action: "analyze", payload: {name: "parity.csv", text: csvText}});
            """,
            csv_text,
            scenarios,
        )
    finally:
        driver.quit()
        server.shutdown()

    payload = json.loads(browser_result)
    if "error" in payload:
        raise RuntimeError(payload["error"])
    for expected, csv_result in zip(native, payload["csvResults"]):
        browser = pd.read_csv(io.StringIO(csv_result))[CLASS_NAMES]
        np.testing.assert_allclose(expected, browser, rtol=1e-12, atol=1e-12)
    print("Native/Pyodide parity passed for legacy, manual, modern, and time-derived CO2.")


if __name__ == "__main__":
    main()
