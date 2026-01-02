from flask import Flask, jsonify
from flask_cors import CORS
import requests
import xml.etree.ElementTree as ET

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

FMI_WFS = "https://opendata.fmi.fi/wfs"

HEADERS = {
    "User-Agent": "mle-saa-kartta/1.0 (contact: github.com/mlevonen)"
}

# -------------------------------------------------
# APU: hae elementti riippumatta namespacesta
# -------------------------------------------------
def find_any(elem, tag):
    for e in elem.iter():
        if e.tag.endswith(tag):
            return e
    return None


# -------------------------------------------------
# HAVAINNOT
# -------------------------------------------------
@app.route("/api/observations")
def observations():
    url = (
        f"{FMI_WFS}?service=WFS&version=2.0.0&request=GetFeature&"
        "storedquery_id=fmi::observations::weather::simple&"
        "parameters=t2m,ws_10min&latest=true"
    )

    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()

    root = ET.fromstring(r.text)
    data = {}

    for member in root.iter():
        if not member.tag.endswith("member"):
            continue

        pos = find_any(member, "pos")
        pname = find_any(member, "ParameterName")
        pval = find_any(member, "ParameterValue")

        if not pos or not pname or not pval:
            continue
        if pval.text == "NaN":
            continue

        lat, lon = map(float, pos.text.split())
        key = (round(lat, 4), round(lon, 4))

        if key not in data:
            data[key] = {
                "lat": lat,
                "lon": lon,
                "t2m": None,
                "ws": None
            }

        if pname.text == "t2m":
            data[key]["t2m"] = float(pval.text)
        elif pname.text == "ws_10min":
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

    print("OBS FEATURES:", len(features))
    return jsonify({"type": "FeatureCollection", "features": features})


# -------------------------------------------------
# ENNUSTE (grid → harvennetaan frontendissä)
# -------------------------------------------------
@app.route("/api/forecast")
def forecast():
    url = (
        f"{FMI_WFS}?service=WFS&version=2.0.0&request=GetFeature&"
        "storedquery_id=fmi::forecast::harmonie::surface::grid&"
        "parameters=t2m&bbox=19,59,32,71&timestep=360"
    )

    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()

    root = ET.fromstring(r.text)
    features = []

    for member in root.iter():
        if not member.tag.endswith("member"):
            continue

        pos = find_any(member, "pos")
        val = find_any(member, "ParameterValue")

        if not pos or not val or val.text == "NaN":
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

    print("FC FEATURES:", len(features))
    return jsonify({"type": "FeatureCollection", "features": features})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8002, debug=True)
