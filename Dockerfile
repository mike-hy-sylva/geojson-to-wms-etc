# Dockerfile — WFS 2.0 + OGC API Features server
# Implements OGC API Features (same standard as pygeoapi, OSGeo/EU open source)
# using a lightweight Flask serving layer.
FROM python:3.12-slim

# ── Python deps ───────────────────────────────────────────────────────────────
RUN pip install flask flask-cors gunicorn gevent

# ── Data files ────────────────────────────────────────────────────────────────
COPY cipa_sites.geojson      /data/cipa_sites.geojson
COPY h3_stress_test.geojson  /data/h3_stress_test.geojson

# ── WFS server app ────────────────────────────────────────────────────────────
COPY wfs_server.py /app/wfs_server.py

# ── Environment ───────────────────────────────────────────────────────────────
ENV DATA_DIR=/data
ENV SERVICE_BASE_URL=https://wfs-demo-176063489463.europe-west1.run.app
ENV PYTHONUNBUFFERED=1

EXPOSE 80

# Run with gunicorn: 4 workers, gevent async, port 80
CMD ["gunicorn", "--workers", "4", "--worker-class", "gevent", \
     "--bind", "0.0.0.0:80", "--timeout", "120", \
     "--chdir", "/app", "wfs_server:app"]
