# Dockerfile — OGC API Features server via pygeoapi
# pygeoapi is the reference Python implementation of OGC API Features (OGC 17-069r4)
# Used by EU geospatial agencies (INSPIRE, EUMETSAT). Replaces custom Flask layer.
FROM python:3.12-slim

# ── Python deps ───────────────────────────────────────────────────────────────
RUN pip install pygeoapi gunicorn

# ── Data files ────────────────────────────────────────────────────────────────
COPY cipa_sites.geojson      /data/cipa_sites.geojson
COPY h3_stress_test.geojson  /data/h3_stress_test.geojson

# ── pygeoapi config ───────────────────────────────────────────────────────────
COPY pygeoapi-config.yml /config/pygeoapi-config.yml

# ── Environment ───────────────────────────────────────────────────────────────
ENV PYGEOAPI_CONFIG=/config/pygeoapi-config.yml
ENV PYGEOAPI_OPENAPI=/tmp/pygeoapi-openapi.yml
ENV PYTHONUNBUFFERED=1

EXPOSE 80

# Generate OpenAPI spec, then serve via gunicorn
CMD ["sh", "-c", \
     "pygeoapi openapi generate $PYGEOAPI_CONFIG > $PYGEOAPI_OPENAPI && \
      gunicorn --workers 4 --bind 0.0.0.0:80 --timeout 120 pygeoapi.flask_app:APP"]
