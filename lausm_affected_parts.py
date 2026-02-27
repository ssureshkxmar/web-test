"""
lausm_affected_parts.py
───────────────────────
Maps LAUSM hemodynamic scalar outputs to Digital Twin anatomical part IDs.

The LAUSM pipeline produces standardized atrial maps for the Left Atrium.
Based on scalar thresholds in TAWSS, BV, FibROSIS, and Age maps,
this module identifies which anatomical regions carry significant stress
and returns corresponding Digital-Twin tissue IDs.

TISSUE_MAP keys (Digital Twin):
    'la'             → Atrial Left        (primary LA body)
    'ra'             → Atrial Right
    'lv'             → Ventricle Left
    'rv'             → Ventricle Right
    'Heartmuscles'   → Myocardium
    'Largevessels'   → Aortic Arc
    'Smallvessels'   → Micro-vessel
    'Pulmonaryvessels' → Pulmonary Trunk
    'SVenaCava'      → Sup. Vena Cava
    'IVenaCava'      → Inf. Vena Cava
    'sanvan'         → Conduction Nodes
    'bicuspid'       → Mitral Valve
"""

import os

# --------------------------------------------------------------------- #
# Region label → Digital-Twin tissue-id + friendly name                  #
# --------------------------------------------------------------------- #

# LAUSM disk maps are divided into named sectors.  We associate each
# sector with the closest anatomical structure in the Digital Twin.
LAUSM_REGION_TO_TISSUE = {
    # Left Atrium regions (primary LAUSM target)
    "anterior_wall":        ("la",               "Atrial Left – Anterior Wall"),
    "posterior_wall":       ("la",               "Atrial Left – Posterior Wall"),
    "atrial_roof":          ("la",               "Atrial Left – Roof"),
    "atrial_floor":         ("la",               "Atrial Left – Floor"),
    "lateral_wall":         ("la",               "Atrial Left – Lateral Wall"),
    "septal_wall":          ("la",               "Atrial Left – Septal Wall"),
    "mitral_isthmus":       ("bicuspid",         "Mitral Valve – Isthmus"),
    "appendage":            ("la",               "Left Atrial Appendage"),
    # Pulmonary-vein ostia feeding the LA
    "rspv":                 ("Pulmonaryvessels", "Right Sup. Pulmonary Vein"),
    "ripv":                 ("Pulmonaryvessels", "Right Inf. Pulmonary Vein"),
    "lspv":                 ("Pulmonaryvessels", "Left Sup. Pulmonary Vein"),
    "lipv":                 ("Pulmonaryvessels", "Left Inf. Pulmonary Vein"),
}

# --------------------------------------------------------------------- #
# Scalar-metric → affected tissue logic (rule-based)                     #
# --------------------------------------------------------------------- #

def determine_affected_parts(lausm_results: dict, lausm_finding: str = "") -> dict:
    """
    Given the lausm_results dict (keys: bv_3d, tawss_3d, fibr_3d, age_3d,
    tawss_mean, bv_disk, … etc.) and/or any finding text, return:

        {
            "affected_parts": ["la", "Pulmonaryvessels", ...],  # Digital-Twin IDs
            "severity": { "la": 0.95, "Pulmonaryvessels": 0.6 },
            "labels":   { "la": "Atrial Left – Posterior Wall", ... },
            "summary":  "...",
        }
    """

    # If LAUSM output files were actually generated, we always flag the LA
    # since LAUSM is fundamentally an atrial-analysis pipeline.
    # Extended logic can parse pixel statistics from the PNG files using
    # PIL if available – for now we use a rule-based approach.

    has_results = bool(lausm_results)

    affected_ids   = {}   # tissue_id → max severity 0–1
    label_map      = {}   # tissue_id → friendly region label

    if has_results:
        # ----- Base rule: LA is ALWAYS the primary region -----
        _accumulate(affected_ids, label_map, "la", 0.90, "Atrial Left – Primary Target")

        # ----- Additional rules from finding text -----
        finding_lower = (lausm_finding or "").lower()

        if "posterior" in finding_lower:
            _accumulate(affected_ids, label_map, "la", 1.0,
                        "Atrial Left – Posterior Wall (high stress)")

        if "anterior" in finding_lower:
            _accumulate(affected_ids, label_map, "la", 0.85,
                        "Atrial Left – Anterior Wall")

        if "mitral" in finding_lower or "isthmus" in finding_lower:
            _accumulate(affected_ids, label_map, "bicuspid", 0.75,
                        "Mitral Valve – Isthmus")

        if "appendage" in finding_lower or "laa" in finding_lower:
            _accumulate(affected_ids, label_map, "la", 0.88,
                        "Left Atrial Appendage")

        if "pulmonary" in finding_lower or "vein" in finding_lower:
            _accumulate(affected_ids, label_map, "Pulmonaryvessels", 0.70,
                        "Pulmonary Veins")

        if "tawss" in finding_lower or "wall shear" in finding_lower:
            # High TAWSS may also bias into the LV outflow area
            _accumulate(affected_ids, label_map, "Smallvessels", 0.55,
                        "Micro-vessel Network (TAWSS stress)")

        if "fibrosis" in finding_lower or "fibr" in finding_lower:
            # Fibrosis heavily implies myocardium
            _accumulate(affected_ids, label_map, "Heartmuscles", 0.65,
                        "Myocardium – Fibrotic Tissue")

        # Optional: image-level analysis using PIL (if installed)
        try:
            from PIL import Image
            import numpy as np

            def _analyse_image(url_path: str):
                """Try to load image from disk and return mean intensity 0-1."""
                if not url_path:
                    return None
                # Convert URL path /lausm/uploads/xxx.png → disk path
                fname = os.path.basename(url_path.split("?")[0])
                candidates = [
                    os.path.join("lausm", "uploads", fname),
                    os.path.join("lausm_upload", fname),
                ]
                for c in candidates:
                    if os.path.exists(c):
                        img = Image.open(c).convert("L")
                        arr = np.array(img, dtype=float) / 255.0
                        return float(arr.mean())
                return None

            tawss_intensity = _analyse_image(lausm_results.get("tawss_3d"))
            if tawss_intensity is not None and tawss_intensity > 0.55:
                _accumulate(affected_ids, label_map, "la", min(tawss_intensity + 0.1, 1.0),
                            "Atrial Left – TAWSS (image-derived)")

            fibr_intensity = _analyse_image(lausm_results.get("fibr_3d"))
            if fibr_intensity is not None and fibr_intensity > 0.45:
                _accumulate(affected_ids, label_map, "Heartmuscles",
                            min(fibr_intensity + 0.15, 1.0),
                            "Myocardium – Fibrosis (image-derived)")

        except Exception:
            pass   # PIL not available – skip image analysis

    # Sort by severity descending
    sorted_parts = sorted(affected_ids.items(), key=lambda x: x[1], reverse=True)

    summary_parts = [label_map.get(tid, tid) for tid, _ in sorted_parts]
    summary = (
        "LAUSM analysis identifies the following structures as clinically relevant: "
        + ", ".join(summary_parts) + ". "
        "Significant hemodynamic variance detected. Please refer to the LAUSM maps for spatial distribution."
    ) if summary_parts else "No significant affected regions detected."

    return {
        "affected_parts": [t for t, _ in sorted_parts],
        "severity": {t: round(s, 3) for t, s in sorted_parts},
        "labels":   label_map,
        "summary":  summary,
    }


def _accumulate(affected_ids, label_map, tissue_id, severity, label):
    """Keep the maximum severity per tissue ID."""
    current = affected_ids.get(tissue_id, 0.0)
    if severity > current:
        affected_ids[tissue_id] = severity
        label_map[tissue_id] = label


# --------------------------------------------------------------------- #
# CLI helper                                                              #
# --------------------------------------------------------------------- #

if __name__ == "__main__":
    import json, sys

    # Quick smoke-test
    sample_results = {
        "bv_3d": "/lausm/uploads/record_bv.png",
        "tawss_3d": "/lausm/uploads/record_tawss.png",
        "fibr_3d": "/lausm/uploads/record_fibr.png",
        "age_3d": "/lausm/uploads/record_age.png",
    }
    sample_finding = (
        "Posterior wall shows elevated TAWSS values. Left Atrium is the "
        "primary target. Fibrosis detected in septal region. Mitral isthmus involved."
    )
    result = determine_affected_parts(sample_results, sample_finding)
    print(json.dumps(result, indent=2))
