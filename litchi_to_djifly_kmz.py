#!/usr/bin/env python3
# Litchi CSV -> DJI Fly KMZ (WPML) converter
# -------------------------------------------------
# See header comments in previous cell for design goals and usage.
import argparse, csv, math, os, zipfile, io, sys
import xml.etree.ElementTree as ET
from pathlib import Path

NS_KML = "http://www.opengis.net/kml/2.2"
NS_WP = "http://www.dji.com/wpmz/1.0.2"
ET.register_namespace("", NS_KML)
ET.register_namespace("wpml", NS_WP)

SUPPORTED_ACTIONS = {
    "gimbalRotate",
    "gimbalEvenlyRotate",
    "takePhoto",
    "startRecord",
    "stopRecord",
    "rotateYaw",
    "hover"
}

def ft_to_m(ft):
    return float(ft) * 0.3048

def parse_csv(csv_path: Path):
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        for r in reader:
            rows.append(r)
    return headers, rows

def float_or_none(v):
    try:
        return float(v)
    except:
        return None

def int_or_none(v):
    try:
        return int(float(v))
    except:
        return None

def build_wpml(doc_name="Mission"):
    kml = ET.Element(ET.QName(NS_KML, "kml"))
    doc = ET.SubElement(kml, "Document")
    mc = ET.SubElement(doc, ET.QName(NS_WP, "missionConfig"))
    return kml, doc, mc

def set_mission_config(mc, args):
    flyTo = ET.SubElement(mc, ET.QName(NS_WP, "flyToWaylineMode"))
    flyTo.text = "safely"
    finish = ET.SubElement(mc, ET.QName(NS_WP, "finishAction"))
    finish.text = args.finish_action
    exit_on_rc = ET.SubElement(mc, ET.QName(NS_WP, "exitOnRCLost"))
    exit_on_rc.text = "executeLostAction"
    lost_action = ET.SubElement(mc, ET.QName(NS_WP, "executeRCLostAction"))
    lost_action.text = "goBack"
    gts = ET.SubElement(mc, ET.QName(NS_WP, "globalTransitionalSpeed"))
    gts.text = str(args.global_transitional_speed)
    dr = ET.SubElement(mc, ET.QName(NS_WP, "droneInfo"))
    val = ET.SubElement(dr, ET.QName(NS_WP, "droneEnumValue"))
    val.text = "68"
    sub = ET.SubElement(dr, ET.QName(NS_WP, "droneSubEnumValue"))
    sub.text = "0"

def add_folder_with_template(doc):
    folder = ET.SubElement(doc, "Folder")
    tid = ET.SubElement(folder, ET.QName(NS_WP, "templateId"))
    tid.text = "0"
    return folder

def add_waypoint(folder, idx, lat, lon, alt_m, speed, poi_tuple, heading_deg, gimbal_pitch_deg):
    pm = ET.SubElement(folder, "Placemark")
    pt = ET.SubElement(pm, "Point")
    coords = ET.SubElement(pt, "coordinates")
    coords.text = f"{lon:.6f},{lat:.6f}"
    widx = ET.SubElement(pm, ET.QName(NS_WP, "index"))
    widx.text = str(idx)
    exec_h = ET.SubElement(pm, ET.QName(NS_WP, "executeHeight"))
    exec_h.text = f"{alt_m:.6f}"
    wps = ET.SubElement(pm, ET.QName(NS_WP, "waypointSpeed"))
    wps.text = f"{speed:.2f}" if speed is not None else "0"
    whp = ET.SubElement(pm, ET.QName(NS_WP, "waypointHeadingParam"))
    mode = ET.SubElement(whp, ET.QName(NS_WP, "waypointHeadingMode"))
    mode.text = "manually"
    angle = ET.SubElement(whp, ET.QName(NS_WP, "waypointHeadingAngle"))
    angle.text = f"{heading_deg:.2f}" if heading_deg is not None else "0"
    angle_en = ET.SubElement(whp, ET.QName(NS_WP, "waypointHeadingAngleEnable"))
    angle_en.text = "1" if heading_deg is not None else "0"
    poi_lat, poi_lon, poi_alt_m = poi_tuple if poi_tuple else (None, None, None)
    if poi_lat is not None and poi_lon is not None and poi_alt_m is not None:
        poi_pt = ET.SubElement(whp, ET.QName(NS_WP, "waypointPoiPoint"))
        poi_pt.text = f"{poi_lat:.12f},{poi_lon:.12f},{poi_alt_m:.12f}"
    wtp = ET.SubElement(pm, ET.QName(NS_WP, "waypointTurnParam"))
    tmode = ET.SubElement(wtp, ET.QName(NS_WP, "waypointTurnMode"))
    tmode.text = "toPointAndPassWithContinuityCurvature"
    tdd = ET.SubElement(wtp, ET.QName(NS_WP, "waypointTurnDampingDist"))
    tdd.text = "0"
    return pm

SUPPORTED_ACTIONS = set(SUPPORTED_ACTIONS)

def add_action_group(doc, trigger_type, start_idx, end_idx, actions):
    ag = ET.SubElement(doc, ET.QName(NS_WP, "actionGroup"))
    agid = ET.SubElement(ag, ET.QName(NS_WP, "actionGroupId"))
    agid.text = "0"
    ags = ET.SubElement(ag, ET.QName(NS_WP, "actionGroupStartIndex"))
    ags.text = str(start_idx)
    age = ET.SubElement(ag, ET.QName(NS_WP, "actionGroupEndIndex"))
    age.text = str(end_idx)
    agm = ET.SubElement(ag, ET.QName(NS_WP, "actionGroupMode"))
    agm.text = "parallel"
    trig = ET.SubElement(ag, ET.QName(NS_WP, "actionTrigger"))
    ttype = ET.SubElement(trig, ET.QName(NS_WP, "actionTriggerType"))
    ttype.text = trigger_type
    for func, params in actions:
        if func not in SUPPORTED_ACTIONS:
            raise ValueError(f"Action '{func}' not supported in DJI Fly workflow")
        a = ET.SubElement(ag, ET.QName(NS_WP, "action"))
        aid = ET.SubElement(a, ET.QName(NS_WP, "actionId"))
        aid.text = "0"
        fn = ET.SubElement(a, ET.QName(NS_WP, "actionActuatorFunc"))
        fn.text = func
        fparams = ET.SubElement(a, ET.QName(NS_WP, "actionActuatorFuncParam"))
        for k, v in (params or {}).items():
            ET.SubElement(fparams, ET.QName(NS_WP, k)).text = str(v)

def build_template_kml(doc_name="Mission"):
    kml = ET.Element(ET.QName(NS_KML, "kml"))
    d = ET.SubElement(kml, "Document")
    name = ET.SubElement(d, "name")
    name.text = doc_name
    return kml

def write_kmz(out_path: Path, waylines_root, template_root):
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as z:
        waylines_bytes = ET.tostring(waylines_root, encoding="utf-8", xml_declaration=True)
        z.writestr("wpmz/waylines.wpml", waylines_bytes)
        template_bytes = ET.tostring(template_root, encoding="utf-8", xml_declaration=True)
        z.writestr("wpmz/template.kml", template_bytes)
    out_path.write_bytes(mem.getvalue())

def float_or_none(v):
    try:
        return float(v)
    except:
        return None

def int_or_none(v):
    try:
        return int(float(v))
    except:
        return None

def main():
    import argparse, sys
    parser = argparse.ArgumentParser(description="Convert Litchi CSV to DJI Fly KMZ (WPML)")
    parser.add_argument("--csv", required=True, help="Path to Litchi mission CSV")
    parser.add_argument("--out", required=True, help="Output KMZ path")
    parser.add_argument("--finish-action", default="goHome",
                        choices=["goHome","land","hover","returnToStartPoint"],
                        help="Mission finish action in DJI Fly")
    parser.add_argument("--global-transitional-speed", type=float, default=3.0,
                        help="globalTransitionalSpeed (m/s) for missionConfig")
    parser.add_argument("--set-heading-from-csv", action="store_true",
                        help="Emit rotateYaw / headingAngle from CSV heading(deg)")
    parser.add_argument("--emit-per-waypoint-photo", action="store_true",
                        help="If CSV has photo_timeinterval>0, emit takePhoto at each waypoint")
    parser.add_argument("--assume-agl", action="store_true",
                        help="Treat CSV altitudemode=1 (AGL) as ATO (warn). DEM conversion not implemented here.")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    out_path = Path(args.out)

    headers, rows = parse_csv(csv_path)
    if not rows:
        print("CSV is empty.", file=sys.stderr); sys.exit(1)

    waylines_root, document, mission_config = build_wpml(doc_name=csv_path.stem)
    set_mission_config(mission_config, args)
    folder = add_folder_with_template(document)

    parsed = []
    agl_warned = False
    for i, r in enumerate(rows):
        lat = float_or_none(r.get("latitude"))
        lon = float_or_none(r.get("longitude"))
        alt_ft = float_or_none(r.get("altitude(ft)"))
        heading = float_or_none(r.get("heading(deg)"))
        speed = float_or_none(r.get("speed(m/s)"))
        gimbalmode = int_or_none(r.get("gimbalmode"))
        gimbal_pitch = float_or_none(r.get("gimbalpitchangle"))
        alt_mode = int_or_none(r.get("altitudemode"))
        poi_lat = float_or_none(r.get("poi_latitude"))
        poi_lon = float_or_none(r.get("poi_longitude"))
        poi_alt_ft = float_or_none(r.get("poi_altitude(ft)"))
        poi_alt_mode = int_or_none(r.get("poi_altitudemode"))
        photo_t = float_or_none(r.get("photo_timeinterval"))

        if alt_ft is None:
            print(f"Row {i}: altitude(ft) missing", file=sys.stderr); sys.exit(2)
        alt_m = ft_to_m(alt_ft)
        poi_alt_m = ft_to_m(poi_alt_ft) if poi_alt_ft is not None else None

        if alt_mode == 1 and not agl_warned and not args.assume_agl:
            print("WARNING: CSV reports AGL altitudes; this script treats heights as ATO. Use --assume-agl to acknowledge.", file=sys.stderr)
            agl_warned = True

        parsed.append({
            "idx": i,
            "lat": lat, "lon": lon, "alt_m": alt_m,
            "speed": speed,
            "heading": heading if args.set_heading_from_csv else None,
            "gimbalmode": gimbalmode,
            "gimbal_pitch": gimbal_pitch,
            "poi": (poi_lat, poi_lon, poi_alt_m) if (poi_lat is not None and poi_lon is not None and poi_alt_m is not None) else None,
            "photo_timeinterval": photo_t
        })

    for p in parsed:
        add_waypoint(folder, p["idx"], p["lat"], p["lon"], p["alt_m"], p["speed"], p["poi"], p["heading"], p["gimbal_pitch"])

    if parsed and parsed[0]["gimbal_pitch"] is not None:
        add_action_group(document, "reachPoint", parsed[0]["idx"], parsed[0]["idx"], [
            ("gimbalRotate", {
                "gimbalRotateMode": "absoluteAngle",
                "gimbalRotateTimeEnable": "0",
                "gimbalRotateTime": "0",
                "gimbalHeadingYawBase": "aircraft",
                "gimbalYawRotateEnable": "0",
                "gimbalYawRotateAngle": "0",
                "gimbalPitchRotateEnable": "1",
                "gimbalPitchRotateAngle": f"{parsed[0]['gimbal_pitch']}",
                "gimbalRollRotateEnable": "0",
                "gimbalRollRotateAngle": "0",
                "payloadPositionIndex": "0"
            })
        ])

    for i in range(len(parsed)-1):
        p0 = parsed[i]
        p1 = parsed[i+1]
        if p1["gimbal_pitch"] is not None:
            add_action_group(document, "betweenAdjacentPoints", p0["idx"], p1["idx"], [
                ("gimbalEvenlyRotate", {
                    "gimbalPitchRotateAngle": f"{p1['gimbal_pitch']}",
                    "payloadPositionIndex": "0"
                })
            ])

    if args.emit_per_waypoint_photo:
        for p in parsed:
            if p["photo_timeinterval"] and p["photo_timeinterval"] > 0:
                add_action_group(document, "multipleTiming", p["idx"], p["idx"], [
                    ("takePhoto", {
                        "payloadPositionIndex": "0",
                        "useGlobalPayloadLensIndex": "0"
                    })
                ])

    if args.set_heading_from_csv:
        for p in parsed:
            if p["heading"] is not None:
                add_action_group(document, "reachPoint", p["idx"], p["idx"], [
                    ("rotateYaw", {
                        "relative": "false",
                        "yawAngle": f"{p['heading']}"
                    })
                ])

    template_root = build_template_kml(doc_name=Path(args.csv).stem)
    write_kmz(out_path, waylines_root, template_root)

if __name__ == "__main__":
    main()
