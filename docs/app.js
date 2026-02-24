/**
 * app.js
 * GeoJSON → WFS Pipeline Demo
 *
 * Loads collections from a live pygeoapi (OGC API Features) server,
 * times the full fetch + render cycle, and displays results in the sidebar.
 *
 * CONFIGURATION: Set PYGEOAPI_BASE_URL to your Cloud Run service URL after deploy.
 */

// ── Configuration ─────────────────────────────────────────────────────────────
// Replace with your Cloud Run URL after deploying.
// For local testing: 'http://localhost:5000'
const PYGEOAPI_BASE_URL = 'https://wfs-demo-176063489463.europe-west1.run.app';

// Layer style definitions
const LAYER_STYLES = {
  cipa_sites: {
    circleColor: '#4f8ef7',
    circleRadius: 10,
    circleStrokeColor: '#ffffff',
    circleStrokeWidth: 2,
  },
  h3_stress_test: {
    fillColor: '#f5a442',
    fillOpacity: 0.35,
    lineColor: '#f5a442',
    lineWidth: 0.5,
    lineOpacity: 0.7,
  },
};

// Track which layers are currently on the map
const activeLayers = new Set();

// ── Map initialisation ────────────────────────────────────────────────────────
const map = new maplibregl.Map({
  container: 'map',
  style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
  center: [-8.4, 24.8],   // centre of the bounding box
  zoom: 3,
  attributionControl: true,
});

map.addControl(new maplibregl.NavigationControl(), 'top-right');
map.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-right');

// ── Sidebar URL population ────────────────────────────────────────────────────
document.getElementById('url-root').textContent = PYGEOAPI_BASE_URL + '/collections';
document.getElementById('url-wfs').textContent =
  PYGEOAPI_BASE_URL + '/collections/cipa_sites/items?f=json';

// Copy-to-clipboard buttons
document.querySelectorAll('.copy-btn').forEach((btn) => {
  btn.addEventListener('click', () => {
    const targetId = btn.dataset.copyId;
    const text = document.getElementById(targetId).textContent;
    navigator.clipboard.writeText(text).then(() => {
      btn.textContent = '✓';
      setTimeout(() => (btn.textContent = '⎘'), 1500);
    });
  });
});

// ── Status helpers ────────────────────────────────────────────────────────────
function setStatus(state, count, fetchMs, renderMs) {
  const stateEl = document.getElementById('st-state');
  stateEl.textContent = state;
  stateEl.className = 'status-val ' + (state === 'Idle' ? 'idle' : state === 'Loading…' ? 'loading' : 'done');

  document.getElementById('st-count').textContent = count !== null ? count.toLocaleString() : '—';
  document.getElementById('st-fetch').textContent = fetchMs !== null ? (fetchMs / 1000).toFixed(2) + ' s' : '—';
  document.getElementById('st-render').textContent = renderMs !== null ? (renderMs / 1000).toFixed(2) + ' s' : '—';

  const total = fetchMs !== null && renderMs !== null ? (fetchMs + renderMs) / 1000 : null;
  document.getElementById('st-total').textContent = total !== null ? total.toFixed(2) + ' s' : '—';

  document.getElementById('status-error').style.display = 'none';
}

function setError(message) {
  const stateEl = document.getElementById('st-state');
  stateEl.textContent = 'Error';
  stateEl.className = 'status-val error';
  const errEl = document.getElementById('status-error');
  errEl.textContent = message;
  errEl.style.display = 'block';
}

function setButtonsDisabled(disabled) {
  document.getElementById('btn-simple').disabled = disabled;
  document.getElementById('btn-stress').disabled = disabled;
}

// ── Layer management ──────────────────────────────────────────────────────────
function removeLayerIfExists(id) {
  if (map.getLayer(id + '-fill')) map.removeLayer(id + '-fill');
  if (map.getLayer(id + '-line')) map.removeLayer(id + '-line');
  if (map.getLayer(id + '-circle')) map.removeLayer(id + '-circle');
  if (map.getSource(id)) map.removeSource(id);
  activeLayers.delete(id);
}

function clearLayers() {
  for (const id of [...activeLayers]) {
    removeLayerIfExists(id);
  }
  setStatus('Idle', null, null, null);
}

// ── Main load function ────────────────────────────────────────────────────────
async function loadCollection(collectionId) {
  setButtonsDisabled(true);
  setStatus('Loading…', null, null, null);

  // Remove existing layer for this collection
  removeLayerIfExists(collectionId);

  const url =
    PYGEOAPI_BASE_URL +
    `/collections/${collectionId}/items?f=json&limit=200000`;

  let fetchMs, geojson;

  // ── Fetch ──
  try {
    const t0 = performance.now();
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    geojson = await response.json();
    fetchMs = performance.now() - t0;
  } catch (err) {
    setError(`Fetch failed: ${err.message}\n\nMake sure the pygeoapi server is running and PYGEOAPI_BASE_URL is set correctly in app.js.`);
    setButtonsDisabled(false);
    return;
  }

  const featureCount = geojson.features ? geojson.features.length : 0;

  // ── Add to map ──
  const t1 = performance.now();

  map.addSource(collectionId, {
    type: 'geojson',
    data: geojson,
    // Enable clustering only for the small dataset (points)
    ...(collectionId === 'cipa_sites' ? {} : {}),
  });

  const style = LAYER_STYLES[collectionId];

  if (collectionId === 'cipa_sites') {
    // Point layer → circle
    map.addLayer({
      id: collectionId + '-circle',
      type: 'circle',
      source: collectionId,
      paint: {
        'circle-color': style.circleColor,
        'circle-radius': style.circleRadius,
        'circle-stroke-color': style.circleStrokeColor,
        'circle-stroke-width': style.circleStrokeWidth,
        'circle-opacity': 0.9,
      },
    });

    // Popup on click
    map.on('click', collectionId + '-circle', (e) => {
      const props = e.features[0].properties;
      const coords = e.features[0].geometry.coordinates;
      new maplibregl.Popup()
        .setLngLat(coords)
        .setHTML(
          `<strong>${props.NAM || props.ID}</strong><br/>
           <em>${props.TYP || ''}</em><br/>
           ${props.STA_CON || ''}`
        )
        .addTo(map);
    });

    map.on('mouseenter', collectionId + '-circle', () => {
      map.getCanvas().style.cursor = 'pointer';
    });
    map.on('mouseleave', collectionId + '-circle', () => {
      map.getCanvas().style.cursor = '';
    });

    // Zoom to features
    const coords = geojson.features.map((f) => f.geometry.coordinates);
    if (coords.length > 0) {
      const lons = coords.map((c) => c[0]);
      const lats = coords.map((c) => c[1]);
      map.fitBounds(
        [
          [Math.min(...lons) - 2, Math.min(...lats) - 2],
          [Math.max(...lons) + 2, Math.max(...lats) + 2],
        ],
        { padding: 40, duration: 800 }
      );
    }
  } else {
    // Polygon layer → fill + outline
    map.addLayer({
      id: collectionId + '-fill',
      type: 'fill',
      source: collectionId,
      paint: {
        'fill-color': style.fillColor,
        'fill-opacity': style.fillOpacity,
      },
    });
    map.addLayer({
      id: collectionId + '-line',
      type: 'line',
      source: collectionId,
      paint: {
        'line-color': style.lineColor,
        'line-width': style.lineWidth,
        'line-opacity': style.lineOpacity,
      },
    });

    // Zoom to bounding box
    map.fitBounds(
      [[-16.45, 10.35], [-0.32, 39.31]],
      { padding: 40, duration: 800 }
    );
  }

  activeLayers.add(collectionId);

  // ── Wait for render-idle to measure render time ──
  map.once('idle', () => {
    const renderMs = performance.now() - t1;
    setStatus('Done', featureCount, fetchMs, renderMs);
    setButtonsDisabled(false);

    // Update the hardcoded benchmark reference for stress test
    if (collectionId === 'h3_stress_test') {
      const totalS = ((fetchMs + renderMs) / 1000).toFixed(1);
      document.getElementById('bench-stress-time').textContent = totalS + ' s';
    }
  });
}
