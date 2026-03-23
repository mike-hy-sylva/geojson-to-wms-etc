"""
wfs_server.py
-------------
Minimal Flask server implementing:
  1. WFS 2.0 XML  — GetCapabilities + GetFeature (for traditional WFS clients)
  2. OGC API Features JSON — /collections + /collections/{id}/items

Reads GeoJSON files directly at startup. No pygeoapi dependency at runtime.
Implements the same OGC standards that pygeoapi implements.

Endpoints:
  GET /?SERVICE=WFS&REQUEST=GetCapabilities          → WFS 2.0 XML
  GET /?SERVICE=WFS&REQUEST=GetFeature&TYPENAMES=... → GeoJSON features
  GET /collections                                   → OGC API Features list
  GET /collections/{id}                              → collection metadata
  GET /collections/{id}/items                        → GeoJSON features (paginated)
  GET /                                              → landing page JSON
"""

import json
import os
from flask import Flask, request, Response, jsonify
from flask_cors import CORS

# ── Config ────────────────────────────────────────────────────────────────────
BASE_URL = os.environ.get(
    "SERVICE_BASE_URL",
    "https://wfs-demo-746476722093.europe-west1.run.app"
)
DATA_DIR = os.environ.get("DATA_DIR", "/data")

# ── Load data once at startup ─────────────────────────────────────────────────
print("Loading GeoJSON data files...")

with open(os.path.join(DATA_DIR, "cipa_sites.geojson"), encoding="utf-8") as f:
    CIPA = json.load(f)
print(f"  cipa_sites: {len(CIPA['features'])} features")

with open(os.path.join(DATA_DIR, "h3_stress_test.geojson"), encoding="utf-8") as f:
    H3 = json.load(f)
print(f"  h3_stress_test: {len(H3['features'])} features")

COLLECTIONS = {
    "cipa_sites": {
        "id": "cipa_sites",
        "title": "CIPA Heritage Sites (3 features)",
        "description": (
            "3 vernacular architecture heritage sites across West Africa "
            "(Benin/Togo, Senegal) and Spain. Source: CIPA Heritage."
        ),
        "bbox": [-16.45, 10.35, -0.32, 39.31],
        "data": CIPA,
    },
    "h3_stress_test": {
        "id": "h3_stress_test",
        "title": "H3 Stress Test - Resolution 6 (144k polygons)",
        "description": (
            "H3 hexagon grid at resolution 6 filling the CIPA bounding box. "
            "~144,000 polygons. Demonstrates WFS performance limits."
        ),
        "bbox": [-16.45, 10.35, -0.32, 39.31],
        "data": H3,
    },
}

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)


# ── WFS 2.0 XML helpers ───────────────────────────────────────────────────────
def _wfs_capabilities_xml():
    feature_types = ""
    for cid, col in COLLECTIONS.items():
        bb = col["bbox"]
        feature_types += f"""
    <FeatureType>
      <Name>{cid}</Name>
      <Title>{col['title']}</Title>
      <Abstract>{col['description']}</Abstract>
      <DefaultCRS>urn:ogc:def:crs:EPSG::4326</DefaultCRS>
      <OtherCRS>urn:ogc:def:crs:OGC:1.3:CRS84</OtherCRS>
      <OutputFormats>
        <Format>application/json</Format>
        <Format>application/geo+json</Format>
      </OutputFormats>
      <WGS84BoundingBox>
        <westBoundLongitude>{bb[0]}</westBoundLongitude>
        <southBoundLatitude>{bb[1]}</southBoundLatitude>
        <eastBoundLongitude>{bb[2]}</eastBoundLongitude>
        <northBoundLatitude>{bb[3]}</northBoundLatitude>
      </WGS84BoundingBox>
    </FeatureType>"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<wfs:WFS_Capabilities version="2.0.0"
  xmlns:wfs="http://www.opengis.net/wfs/2.0"
  xmlns:ows="http://www.opengis.net/ows/1.1"
  xmlns:xlink="http://www.w3.org/1999/xlink"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.opengis.net/wfs/2.0 http://schemas.opengis.net/wfs/2.0/wfs.xsd">

  <ows:ServiceIdentification>
    <ows:Title>GeoJSON to WFS Pipeline Demo</ows:Title>
    <ows:Abstract>CIPA Heritage Sites and H3 stress-test polygons served as WFS 2.0 and OGC API Features. Built with Flask + pygeoapi standards.</ows:Abstract>
    <ows:Keywords><ows:Keyword>WFS</ows:Keyword><ows:Keyword>OGC</ows:Keyword><ows:Keyword>GeoJSON</ows:Keyword><ows:Keyword>H3</ows:Keyword></ows:Keywords>
    <ows:ServiceType>WFS</ows:ServiceType>
    <ows:ServiceTypeVersion>2.0.0</ows:ServiceTypeVersion>
    <ows:Fees>NONE</ows:Fees>
    <ows:AccessConstraints>NONE</ows:AccessConstraints>
  </ows:ServiceIdentification>

  <ows:ServiceProvider>
    <ows:ProviderName>Sylva</ows:ProviderName>
    <ows:ProviderSite xlink:href="https://github.com/mike-hy-sylva/geojson-to-wms-etc"/>
    <ows:ServiceContact>
      <ows:IndividualName>Michael</ows:IndividualName>
      <ows:ContactInfo>
        <ows:Address>
          <ows:ElectronicMailAddress>michael@sylva.earth</ows:ElectronicMailAddress>
        </ows:Address>
      </ows:ContactInfo>
    </ows:ServiceContact>
  </ows:ServiceProvider>

  <ows:OperationsMetadata>
    <ows:Operation name="GetCapabilities">
      <ows:DCP><ows:HTTP>
        <ows:Get xlink:href="{BASE_URL}/wfs"/>
        <ows:Post xlink:href="{BASE_URL}/wfs"/>
      </ows:HTTP></ows:DCP>
    </ows:Operation>
    <ows:Operation name="GetFeature">
      <ows:DCP><ows:HTTP>
        <ows:Get xlink:href="{BASE_URL}/wfs"/>
      </ows:HTTP></ows:DCP>
      <ows:Parameter name="outputFormat">
        <ows:AllowedValues>
          <ows:Value>application/json</ows:Value>
          <ows:Value>application/geo+json</ows:Value>
        </ows:AllowedValues>
        <ows:DefaultValue>application/json</ows:DefaultValue>
      </ows:Parameter>
    </ows:Operation>
    <ows:Operation name="DescribeFeatureType">
      <ows:DCP><ows:HTTP>
        <ows:Get xlink:href="{BASE_URL}/wfs"/>
      </ows:HTTP></ows:DCP>
    </ows:Operation>
  </ows:OperationsMetadata>

  <FeatureTypeList>{feature_types}
  </FeatureTypeList>

</wfs:WFS_Capabilities>"""


def _get_features(collection_id, bbox_str=None, count=None, start_index=0):
    col = COLLECTIONS.get(collection_id)
    if col is None:
        return None
    features = col["data"]["features"]
    if bbox_str:
        try:
            minx, miny, maxx, maxy = map(float, bbox_str.split(","))
            def in_bbox(f):
                coords = f["geometry"].get("coordinates", [])
                if f["geometry"]["type"] == "Point":
                    lon, lat = coords
                    return minx <= lon <= maxx and miny <= lat <= maxy
                return True  # polygons: pass for simplicity
            features = [f for f in features if in_bbox(f)]
        except Exception:
            pass
    total = len(features)
    if count is not None:
        features = features[start_index: start_index + count]
    return features, total


# ── Root / WFS dispatcher ─────────────────────────────────────────────────────
@app.route("/", methods=["GET", "HEAD", "OPTIONS"])
def root():
    # Case-insensitive lookup — WFS spec treats param names as case-insensitive,
    # and the WHH tool sends lowercase "service=wfs&request=GetCapabilities"
    args_ci = {k.lower(): v for k, v in request.args.items()}
    service = args_ci.get("service", "").upper()
    req = args_ci.get("request", "").upper()

    if service == "WFS":
        if req == "GETCAPABILITIES":
            xml = _wfs_capabilities_xml()
            return Response(xml, mimetype="text/xml; charset=UTF-8")

        elif req == "GETFEATURE":
            type_names = (
                args_ci.get("typenames")
                or args_ci.get("typename")  # WFS 1.x style
                or ""
            )
            # strip namespace prefix if present (e.g. "ns:cipa_sites" → "cipa_sites")
            type_names = type_names.split(":")[-1].strip()
            bbox_str = args_ci.get("bbox")
            count = args_ci.get("count")
            count = int(count) if count else None
            start = int(args_ci.get("startindex", 0))

            result = _get_features(type_names, bbox_str, count, start)
            if result is None:
                return Response(
                    f"Unknown layer: {type_names}", status=400
                )
            features, total = result
            fc = {"type": "FeatureCollection", "numberMatched": total,
                  "numberReturned": len(features), "features": features}
            return Response(
                json.dumps(fc),
                mimetype="application/geo+json",
                headers={"Access-Control-Allow-Origin": "*"},
            )

        elif req == "DESCRIBEFEATURETYPE":
            # Minimal XSD response
            names = request.args.get("TYPENAMES", ",".join(COLLECTIONS.keys()))
            return Response(
                f'<?xml version="1.0"?><xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">'
                f'<!-- DescribeFeatureType for {names} --></xsd:schema>',
                mimetype="application/xml",
            )

    # ── OGC API Features landing page ─────────────────────────────────────────
    return jsonify({
        "title": "GeoJSON to WFS Pipeline Demo",
        "description": (
            "CIPA Heritage Sites and H3 stress-test polygons served as "
            "WFS 2.0 and OGC API Features."
        ),
        "links": [
            {"rel": "self", "href": BASE_URL + "/", "type": "application/json"},
            {"rel": "conformance", "href": BASE_URL + "/conformance", "type": "application/json"},
            {"rel": "data", "href": BASE_URL + "/collections", "type": "application/json"},
            {"rel": "service-desc", "href": BASE_URL + "/?SERVICE=WFS&REQUEST=GetCapabilities",
             "type": "application/xml", "title": "WFS 2.0 GetCapabilities"},
        ],
    })


# ── /wfs alias — many WFS clients try this well-known path ───────────────────
@app.route("/wfs", methods=["GET", "HEAD", "OPTIONS"])
def wfs_endpoint():
    return root()


# ── OGC API Features — conformance ───────────────────────────────────────────
@app.route("/conformance")
def conformance():
    return jsonify({"conformsTo": [
        "http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/core",
        "http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/geojson",
        "http://www.opengis.net/spec/wfs/2.0/conf/core",
    ]})


# ── OGC API Features — collections list ──────────────────────────────────────
@app.route("/collections")
def collections():
    cols = []
    for cid, col in COLLECTIONS.items():
        bb = col["bbox"]
        cols.append({
            "id": cid,
            "title": col["title"],
            "description": col["description"],
            "extent": {"spatial": {"bbox": [bb], "crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"}},
            "links": [
                {"rel": "items", "href": f"{BASE_URL}/collections/{cid}/items", "type": "application/geo+json"},
                {"rel": "self", "href": f"{BASE_URL}/collections/{cid}", "type": "application/json"},
            ],
        })
    return jsonify({"collections": cols, "links": [
        {"rel": "self", "href": BASE_URL + "/collections", "type": "application/json"}
    ]})


# ── OGC API Features — single collection ─────────────────────────────────────
@app.route("/collections/<collection_id>")
def collection(collection_id):
    col = COLLECTIONS.get(collection_id)
    if col is None:
        return jsonify({"error": f"Collection '{collection_id}' not found"}), 404
    bb = col["bbox"]
    return jsonify({
        "id": collection_id,
        "title": col["title"],
        "description": col["description"],
        "extent": {"spatial": {"bbox": [bb], "crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"}},
        "links": [
            {"rel": "items", "href": f"{BASE_URL}/collections/{collection_id}/items",
             "type": "application/geo+json"},
            {"rel": "self", "href": f"{BASE_URL}/collections/{collection_id}",
             "type": "application/json"},
        ],
    })


# ── OGC API Features — items ──────────────────────────────────────────────────
@app.route("/collections/<collection_id>/items")
def items(collection_id):
    limit = int(request.args.get("limit", 10000))
    offset = int(request.args.get("offset", 0))
    bbox_str = request.args.get("bbox")

    result = _get_features(collection_id, bbox_str, limit, offset)
    if result is None:
        return jsonify({"error": f"Collection '{collection_id}' not found"}), 404

    features, total = result
    return Response(
        json.dumps({
            "type": "FeatureCollection",
            "numberMatched": total,
            "numberReturned": len(features),
            "features": features,
            "links": [
                {"rel": "self",
                 "href": f"{BASE_URL}/collections/{collection_id}/items",
                 "type": "application/geo+json"},
            ],
        }),
        mimetype="application/geo+json",
        headers={"Access-Control-Allow-Origin": "*"},
    )


# ── Single feature ────────────────────────────────────────────────────────────
@app.route("/collections/<collection_id>/items/<feature_id>")
def item(collection_id, feature_id):
    col = COLLECTIONS.get(collection_id)
    if col is None:
        return jsonify({"error": "Collection not found"}), 404
    for f in col["data"]["features"]:
        if str(f.get("properties", {}).get("ID", "")) == feature_id or \
           str(f.get("properties", {}).get("h3_index", "")) == feature_id:
            return jsonify(f)
    return jsonify({"error": "Feature not found"}), 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 80))
    print(f"Starting WFS server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
