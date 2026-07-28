"""Tests for auto-calculation functions in auto_calc.py."""
import pytest
from app.services import auto_calc


def test_calculate_cbc_basic():
    params = {
        "hb": 14.0,
        "rbc": 4.5,
        "wbc": 7.0,
        "seg_pct": 60,
        "lymph_pct": 30,
        "mono_pct": 6,
        "eso_pct": 3,
        "baso_pct": 1,
    }
    res = auto_calc.calculate_cbc(params)
    
    # HCT = 14.0 * 3.1 = 43.4
    assert res["hct"] == 43.4
    # Color Index = (14.0 / 16) * 100 = 87.5
    assert res["color_index"] == 87.5
    # MCH = (14.0 * 10) / 4.5 = 31.1
    assert res["mch"] == 31.1
    # MCHC = (14.0 * 100) / 43.4 = 32.3
    assert res["mchc"] == 32.3
    # MCV = (43.4 * 10) / 4.5 = 96.4
    assert res["mcv"] == 96.4
    
    # Absolute counts: % * WBC * 10
    # Seg: 60 * 7 * 10 = 4200
    assert res["seg_abs"] == 4200.0
    # Lymph: 30 * 7 * 10 = 2100
    assert res["lymph_abs"] == 2100.0
    # Mono: 6 * 7 * 10 = 420
    assert res["mono_abs"] == 420.0
    # Eso: 3 * 7 * 10 = 210
    assert res["eso_abs"] == 210.0
    # Baso: 1 * 7 * 10 = 70
    assert res["baso_abs"] == 70.0


def test_calculate_cbc_missing_and_zero():
    params = {
        "hb": 10.0,
        "rbc": 0,  # zero RBC should avoid division by zero
    }
    res = auto_calc.calculate_cbc(params)
    assert res["hct"] == 31.0
    assert "mch" not in res
    assert "mcv" not in res


def test_calculate_creatinine_clearance():
    params = {
        "s_creat": 1.2,
        "u_creat": 120.0,
        "vol": 1500.0,
    }
    res = auto_calc.calculate_creatinine_clearance(params)
    # ucrea = (120 * 1500) / 100000 = 1.8
    assert res["ucrea"] == 1.8
    # clearance = (120 * 1500) / (1.2 * 1440) = 180000 / 1728 = 104.17
    assert res["clearance"] == 104.17


def test_param_key_normalization():
    assert auto_calc.normalize_param_key("HCT (Hematocrit)") == "hct"
    assert auto_calc.normalize_param_key("Color Index (دليل اللون)") == "color_index"
    assert auto_calc.normalize_param_key("MCHC") == "mchc"
    assert auto_calc.normalize_param_key("MCH") == "mch"
    assert auto_calc.normalize_param_key("MCV") == "mcv"
