# GeoJSON → WFS Pipeline Demo

Demonstrates how a small GeoJSON file is exposed as a live **OGC API Features** (WFS-compatible) service, then stress-tested with a synthetic H3 hexagon dataset to reveal the real limits of vector data pipelines.

**Stack:** Python · [pygeoapi](https://pygeoapi.io) · Docker · Google Cloud Run · MapLibre GL JS · GitHub Pages

---

## Why not WMTS or WMS?

| Protocol | Returns | Requires |
|---|---|---|
| **WFS / OGC API Features** | Vector data (GeoJSON/GML) | Server |
| **WMS** | Rendered PNG images | Server + image renderer |
| **WMTS** | Pre-rendered PNG tile grid | Server (or static tiles) |

For a 3-point GeoJSON, **WFS is the right tool**: it returns the raw vector features that clients can style, filter, and query. WMTS/WMS add server-side raster rendering complexity with no benefit for small vector datasets.

---

## Repository Structure

```
geojson-to-wms-etc/
├── CIPA TRIAL00.geojson       ← source data (3 heritage sites)
├── generate_stress_test.py    ← H3 polygon generator
├── requirements.txt           ← Python deps for generator
├── pygeoapi-config.yml        ← pygeoapi server config
├── Dockerfile                 ← container for Cloud Run
├── cors.json                  ← GCS CORS policy
└── docs/                      ← GitHub Pages frontend
    ├── index.html
    ├── app.js
    └── style.css
```

---

## Step 1 — Generate the H3 stress-test GeoJSON

```bash
pip install -r requirements.txt
python generate_stress_test.py
```

Expected output:
```
H3 Resolution 6: 142,381 polygons generated in 4,210 ms
File size: 43.2 MB → h3_stress_test.geojson
```

To test different resolutions:
```bash
python generate_stress_test.py --res 5   # ~20k cells (light)
python generate_stress_test.py --res 6   # ~140k cells (default)
python generate_stress_test.py --res 7   # ~1M cells  (crashes browsers)
```

---

## Step 2 — Test locally with Docker

```bash
docker build -t wfs-demo .
docker run -p 5000:5000 wfs-demo
```

Verify endpoints:
- Collections list: http://localhost:5000/collections
- Heritage sites: http://localhost:5000/collections/cipa_sites/items
- H3 stress test: http://localhost:5000/collections/h3_stress_test/items?limit=100
- WFS 2.0 XML: http://localhost:5000/wfs?SERVICE=WFS&REQUEST=GetCapabilities

---

## Step 3 — Deploy to Cloud Run

```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/general-tasks-454208/wfs-demo

# Deploy (europe-west1 recommended for EU data)
gcloud run deploy wfs-demo \
  --image gcr.io/general-tasks-454208/wfs-demo \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --memory 512Mi
```

After deploy, you'll receive a URL like `https://wfs-demo-176063489463.europe-west1.run.app`.

**Update the config with your URL:**
1. Edit `pygeoapi-config.yml` → replace `YOUR-CLOUD-RUN-URL`
2. Edit `docs/app.js` → replace `YOUR-CLOUD-RUN-URL`
3. Rebuild and redeploy: `gcloud builds submit ... && gcloud run deploy ...`

---

## Step 4 — Deploy the frontend to GitHub Pages

1. Push this repo to GitHub
2. Go to **Settings → Pages → Source** → select `Deploy from branch` → branch `main`, folder `/docs`
3. The frontend will be live at `https://<your-username>.github.io/<repo-name>/`

---

## Using the WFS URL in external GIS tools

Paste either of these into the "External services" panel of any OGC-compatible tool (QGIS, ArcGIS Online, etc.):

```
# OGC API Features root (modern WFS)
https://wfs-demo-176063489463.europe-west1.run.app/

# Traditional WFS 2.0 GetCapabilities
https://wfs-demo-176063489463.europe-west1.run.app/wfs?SERVICE=WFS&REQUEST=GetCapabilities
```

Select layers:
- `cipa_sites` — 3 heritage site points
- `h3_stress_test` — ~140k H3 hexagon polygons

---

## Pipeline limits demonstrated

| Dataset | Features | Load time | Notes |
|---|---|---|---|
| CIPA sites | 3 | ~0.1 s | Instant at any scale |
| H3 Res 5 | ~20k | ~2 s | Noticeable but fast |
| H3 Res 6 | ~140k | ~10–15 s | Real-world stress |
| H3 Res 7 | ~1M | Crashes | Hard browser limit |

This is why tiled services (WMTS/MVT) exist: they avoid sending all features to the client at once. For large datasets, vector tiles (`/{z}/{x}/{y}.pbf`) are the production-grade solution.

---

## About pygeoapi

[pygeoapi](https://pygeoapi.io) is an OSGeo-incubated Python server implementing OGC API standards. It is developed with significant contributions from European institutions (Norwegian Met, Dutch Kadaster, EURAC Research) and is the recommended modern alternative to GeoServer/MapServer for OGC API Features deployments.
