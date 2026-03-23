# GeoJSON → OGC API Features Pipeline Demo

Demonstrates how a small GeoJSON file is exposed as a live **OGC API Features** service using [pygeoapi](https://pygeoapi.io), then stress-tested with a synthetic H3 hexagon dataset to reveal the real limits of vector data pipelines.

**Stack:** Python · [pygeoapi](https://pygeoapi.io) · Docker · Google Cloud Run · MapLibre GL JS · GitHub Pages

**Live service:** https://wfs-demo-746476722093.europe-west1.run.app

---

## Why not WMTS or WMS?

| Protocol | Returns | Requires |
|---|---|---|
| **OGC API Features / WFS** | Vector data (GeoJSON) | Server |
| **WMS** | Rendered PNG images | Server + image renderer |
| **WMTS** | Pre-rendered PNG tile grid | Server (or static tiles) |

For a 3-point GeoJSON, **OGC API Features is the right tool**: it returns raw vector features that clients can style, filter, and query. WMTS/WMS add server-side raster rendering complexity with no benefit for small vector datasets.

---

## Repository Structure

```
geojson-to-wms-etc/
├── CIPA TRIAL00.geojson       ← source data (3 heritage sites)
├── cipa_sites.geojson         ← cleaned copy (baked into container)
├── h3_stress_test.geojson     ← generated H3 stress-test data (baked into container)
├── generate_stress_test.py    ← H3 polygon generator
├── requirements.txt           ← Python deps for generator (h3, shapely)
├── pygeoapi-config.yml        ← pygeoapi server configuration
├── wfs_server.py              ← legacy Flask reference (not deployed)
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
H3 Resolution 6: 144,462 polygons generated
File size: 55.9 MB → h3_stress_test.geojson
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
docker run -p 80:80 wfs-demo
```

Verify endpoints:
- Landing page: http://localhost/
- Collections list: http://localhost/collections
- Heritage sites: http://localhost/collections/cipa_sites/items
- H3 stress test: http://localhost/collections/h3_stress_test/items?limit=100
- Conformance: http://localhost/conformance
- OpenAPI spec: http://localhost/openapi

---

## Step 3 — Deploy to Cloud Run

```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/<PROJECT_ID>/wfs-demo

# Deploy (europe-west1 recommended for EU data)
gcloud run deploy wfs-demo \
  --image gcr.io/<PROJECT_ID>/wfs-demo \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --port 80
```

After deploy, update `server.url` in `pygeoapi-config.yml` with your Cloud Run URL, then rebuild and redeploy.

---

## Step 4 — Deploy the frontend to GitHub Pages

1. Push this repo to GitHub
2. Go to **Settings → Pages → Source** → select `Deploy from branch` → branch `main`, folder `/docs`
3. The frontend will be live at `https://<your-username>.github.io/<repo-name>/`

---

## Using the service in GIS tools

### QGIS (recommended)
1. Layer → Add Layer → Add WFS Layer
2. New connection → URL: `https://wfs-demo-746476722093.europe-west1.run.app`
3. Set version/protocol to **OGC API - Features**
4. Connect → both collections appear → Add to map

### Any OGC API Features client
```
https://wfs-demo-746476722093.europe-west1.run.app/collections/cipa_sites/items
https://wfs-demo-746476722093.europe-west1.run.app/collections/h3_stress_test/items
```

---

## Pipeline limits demonstrated

| Dataset | Features | Notes |
|---|---|---|
| CIPA sites | 3 | Instant at any scale |
| H3 Res 5 | ~20k | Noticeable but fast |
| H3 Res 6 | ~140k | Real-world stress (~10–15 s) |
| H3 Res 7 | ~1M | Crashes browser tabs |

This is why tiled services (WMTS/MVT) exist: they avoid sending all features to the client at once.

---

## About pygeoapi

[pygeoapi](https://pygeoapi.io) is an OSGeo-incubated Python server implementing OGC API standards. It is the reference implementation of **OGC API - Features** (OGC 17-069r4), which is the current standard replacing WFS 2.0. Developed with contributions from European institutions (Norwegian Met, Dutch Kadaster, EURAC Research) and used across EU INSPIRE-compliant deployments.
