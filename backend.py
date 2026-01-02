from flask import Flask, jsonify
from flask_cors import CORS
import requests
import xml.etree.ElementTree as ET

app = Flask(__name__)

# 🔥 SALLI CORS KAIKILLE POLUILLE
CORS(app, resources={r"/api/*": {"origins": "*"}})

FMI_WFS = "https://opendata.fmi.fi/wfs"

# ✅ PAKOLLINEN USER-AGENT FMI:lle (Render / pilvipalvelut)
HEADERS = {
    "User-Agent": "mle-saa-kartta/1.0 (https://mlevonen.github.io)"
}

# ---------------------------
# HAVAINNOT
# ---------------------------
@app.route("/api/observations")
def observations():
    url = (
        f"{FMI_WFS}?service=WFS&version=2.0.0&request=GetFeature&"
        "storedquery_id=fmi::observations::weather::simple&"
        "parameters=t2m,ws_10min&latest=true"
    )

    # 🔑 USER-AGENT LISÄTTY
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()

    root = ET.fromstring(r.text)
    ns = {
        "wfs": "http://www.opengis.net/wfs/2.0",
        "gml": "http://www.opengis.net/gml/3.2",
        "bs": "http://xml.fmi.fi/schema/wfs/2.0"
    }

    data = {}
    for m in root.findall(".//wfs:member", ns):
        pos = m.find(".//gml:pos", ns)
        pname = m.find(".//bs:ParameterName", ns)
        pval = m.find(".//bs:ParameterValue", ns)

        if pos is None or pname is None or pval is None:
            continue

        lat, lon = map(float, pos.text.split())
        key = (round(lat, 4), round(lon, 4))

        if key not in data:
            data[key] = {"lat": lat, "lon": lon, "t2m": None, "ws": None}

        if pname.text == "t2m" and pval.text != "NaN":
            data[key]["t2m"] = float(pval.text)

        if pname.text == "ws_10min" and pval.text != "NaN":
            data[key]["ws"] = float(pval.text)

    features = []
    for s in data.values():
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [s["lon"], s["lat"]]
            },
            "properties": {
                "name": f"Sääasema {s['lat']:.2f}, {s['lon']:.2f}",
                "t2m": s["t2m"],
                "ws": s["ws"]
            }
        })

    return jsonify({
        "type": "FeatureCollection",
        "features": features
    })


# ---------------------------
# ENNUSTE
# ---------------------------
@app.route("/api/forecast")
def forecast():
    url = (
        f"{FMI_WFS}?service=WFS&version=2.0.0&request=GetFeature&"
        "storedquery_id=fmi::forecast::harmonie::surface::grid&"
        "parameters=t2m&bbox=19,59,32,71&timestep=360"
    )

    # 🔑 USER-AGENT LISÄTTY
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()

    root = ET.fromstring(r.text)
    ns = {
        "wfs": "http://www.opengis.net/wfs/2.0",
        "gml": "http://www.opengis.net/gml/3.2",
        "bs": "http://xml.fmi.fi/schema/wfs/2.0"
    }

    features = []
    for m in root.findall(".//wfs:member", ns):
        pos = m.find(".//gml:pos", ns)
        val = m.find(".//bs:ParameterValue", ns)

        if pos is None or val is None:
            continue

        lat, lon = map(float, pos.text.split())
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat]
            },
            "properties": {
                "t2m": float(val.text)
            }
        })

    return jsonify({
        "type": "FeatureCollection",
        "features": features
    })


if __name__ == "__main__":
    app.run(port=8002, debug=True)
