"""Auto-calculation service for derived laboratory parameters (CBC, Creatinine Clearance, etc.)
Extracted from Access VBA original business logic (Form_CBC, Form_Clerance).
"""
import re
from typing import Dict, Optional, Union


def _to_float(val: any) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        cleaned = val.strip()
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def calculate_cbc(params: Dict[str, any]) -> Dict[str, float]:
    """Calculate derived CBC parameters based on WBC, RBC, HB and differential percentages.
    
    Expected inputs in params dictionary (keyed by parameter code or normalized name):
      - hb (g/dL)
      - rbc (x10^6/uL)
      - wbc (x10^3/uL)
      - seg_pct (%)
      - lymph_pct (%)
      - mono_pct (%)
      - eso_pct (%)
      - baso_pct (%)
      
    Returns dictionary with calculated values:
      - hct
      - color_index
      - mch
      - mchc
      - mcv
      - seg_abs, lymph_abs, mono_abs, eso_abs, baso_abs
    """
    results: Dict[str, float] = {}

    hb = _to_float(params.get("hb"))
    rbc = _to_float(params.get("rbc"))
    wbc = _to_float(params.get("wbc"))

    seg_pct = _to_float(params.get("seg_pct"))
    lymph_pct = _to_float(params.get("lymph_pct"))
    mono_pct = _to_float(params.get("mono_pct"))
    eso_pct = _to_float(params.get("eso_pct"))
    baso_pct = _to_float(params.get("baso_pct"))

    # HCT = HB * 3.1
    hct = None
    if hb is not None:
        hct = round(hb * 3.1, 1)
        results["hct"] = hct

    # Color Index = (HB / 16) * 100
    if hb is not None:
        results["color_index"] = round((hb / 16.0) * 100.0, 1)

    # MCH = (HB * 10) / RBC
    if hb is not None and rbc is not None and rbc > 0:
        results["mch"] = round((hb * 10.0) / rbc, 1)

    # MCHC = (HB * 100) / HCT
    if hb is not None and hct is not None and hct > 0:
        results["mchc"] = round((hb * 100.0) / hct, 1)

    # MCV = (HCT * 10) / RBC
    if hct is not None and rbc is not None and rbc > 0:
        results["mcv"] = round((hct * 10.0) / rbc, 1)

    # Absolute differential counts: % * WBC * 10
    if wbc is not None:
        if seg_pct is not None:
            results["seg_abs"] = round(seg_pct * wbc * 10.0, 1)
        if lymph_pct is not None:
            results["lymph_abs"] = round(lymph_pct * wbc * 10.0, 1)
        if mono_pct is not None:
            results["mono_abs"] = round(mono_pct * wbc * 10.0, 1)
        if eso_pct is not None:
            results["eso_abs"] = round(eso_pct * wbc * 10.0, 1)
        if baso_pct is not None:
            results["baso_abs"] = round(baso_pct * wbc * 10.0, 1)

    return results


def calculate_creatinine_clearance(params: Dict[str, any]) -> Dict[str, float]:
    """Calculate Creatinine Clearance and Daily Excretion.
    
    Formula from Form_Clerance:
      Creatinine Clearance = (Urine Creatinine * Volume) / (Serum Creatinine * 1440)
      ucrea (Daily Excretion) = (Urine Creatinine * Volume) / 100000
    """
    results: Dict[str, float] = {}

    s_creat = _to_float(params.get("s_creat"))
    u_creat = _to_float(params.get("u_creat"))
    vol = _to_float(params.get("vol"))

    if u_creat is not None and vol is not None:
        results["ucrea"] = round((u_creat * vol) / 100000.0, 2)
        if s_creat is not None and s_creat > 0:
            results["clearance"] = round((u_creat * vol) / (s_creat * 1440.0), 2)

    return results


def is_cbc_test(test_name: str) -> bool:
    name = (test_name or "").strip().lower()
    return "cbc" in name or "صورة دم" in name or "complete blood count" in name


def is_creatinine_clearance_test(test_name: str) -> bool:
    name = (test_name or "").strip().lower()
    return "clearance" in name or "تصفية الكرياتينين" in name or "clerance" in name


def normalize_param_key(param_name: str) -> str:
    """Normalize a parameter name to a standardized key for calculation matching."""
    s = param_name.strip().lower()
    
    # CBC matching
    if "color index" in s or "دليل اللون" in s:
        return "color_index"
    if "mchc" in s:
        return "mchc"
    if "mch" in s:
        return "mch"
    if "mcv" in s:
        return "mcv"
    if "hct" in s or "hematocrit" in s or "الهيماتوكريت" in s:
        return "hct"
    if "wbc" in s or "white blood" in s or "كريات الدم البيضاء" in s:
        return "wbc"
    if "rbc" in s or "red blood" in s or "كريات الدم الحمراء" in s:
        return "rbc"
    if "hb" in s or "hgb" in s or "hemoglobin" in s or "الهيموجلوبين" in s:
        return "hb"

    # Absolute differential counts vs %
    is_abs = any(w in s for w in ["abs", "count", "مطلق", "عدد"])
    if "seg" in s or "neutrophil" in s or "متعادلة" in s:
        return "seg_abs" if is_abs else "seg_pct"
    if "lymph" in s or "ليمفاوية" in s:
        return "lymph_abs" if is_abs else "lymph_pct"
    if "mono" in s or "وحيدة" in s:
        return "mono_abs" if is_abs else "mono_pct"
    if "eso" in s or "eo" in s or "حمضية" in s:
        return "eso_abs" if is_abs else "eso_pct"
    if "baso" in s or "قاعدية" in s:
        return "baso_abs" if is_abs else "baso_pct"

    # Creatinine Clearance matching
    if "serum" in s or "دم" in s:
        return "s_creat"
    if "urine creat" in s or "u.creat" in s or "بول" in s:
        return "u_creat"
    if "vol" in s or "حجم" in s:
        return "vol"
    if "clearance" in s or "تصفية" in s:
        return "clearance"
    if "ucrea" in s or "excretion" in s or "إفراز" in s:
        return "ucrea"

    return s
