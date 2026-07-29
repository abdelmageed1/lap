from app.services import auto_calc


def test_calculate_cbc_matches_documented_vba_findings():
    """HB=14, RBC=5, WBC=8 with sample differential percentages - see info/01-BUSINESS-LOGIC.md."""
    params = {
        "hb": 14.0, "rbc": 5.0, "wbc": 8.0,
        "seg_pct": 60.0, "lymph_pct": 30.0, "mono_pct": 5.0, "eso_pct": 3.0, "baso_pct": 2.0,
    }
    results = auto_calc.calculate_cbc(params)

    assert results["hct"] == round(14.0 * 3.1, 1)
    assert results["color_index"] == round((14.0 / 16.0) * 100.0, 1)
    assert results["mch"] == round((14.0 * 10.0) / 5.0, 1)
    hct = round(14.0 * 3.1, 1)
    assert results["mchc"] == round((14.0 * 100.0) / hct, 1)
    assert results["mcv"] == round((hct * 10.0) / 5.0, 1)
    assert results["seg_abs"] == round(60.0 * 8.0 * 10.0, 1)
    assert results["lymph_abs"] == round(30.0 * 8.0 * 10.0, 1)
    assert results["mono_abs"] == round(5.0 * 8.0 * 10.0, 1)
    assert results["eso_abs"] == round(3.0 * 8.0 * 10.0, 1)
    assert results["baso_abs"] == round(2.0 * 8.0 * 10.0, 1)


def test_calculate_cbc_missing_inputs_are_skipped():
    results = auto_calc.calculate_cbc({"hb": "14"})
    assert results["hct"] == round(14.0 * 3.1, 1)
    assert "mch" not in results  # RBC missing
    assert "seg_abs" not in results  # WBC/percentages missing


def test_calculate_cbc_accepts_string_values():
    results = auto_calc.calculate_cbc({"hb": " 14 ", "rbc": "5"})
    assert results["mch"] == round((14.0 * 10.0) / 5.0, 1)


def test_calculate_creatinine_clearance_matches_formula():
    params = {"s_creat": 1.0, "u_creat": 100.0, "vol": 1440.0}
    results = auto_calc.calculate_creatinine_clearance(params)
    assert results["clearance"] == round((100.0 * 1440.0) / (1.0 * 1440.0), 2)
    assert results["ucrea"] == round((100.0 * 1440.0) / 100000.0, 2)


def test_calculate_creatinine_clearance_without_serum_creatinine_skips_clearance():
    results = auto_calc.calculate_creatinine_clearance({"u_creat": 100.0, "vol": 1440.0})
    assert "ucrea" in results
    assert "clearance" not in results


def test_is_cbc_test_and_is_creatinine_clearance_test():
    assert auto_calc.is_cbc_test("CBC")
    assert auto_calc.is_cbc_test("صورة دم كاملة CBC")
    assert not auto_calc.is_cbc_test("Creatinine Clearance")
    assert auto_calc.is_creatinine_clearance_test("Creatinine Clearance")
    assert not auto_calc.is_creatinine_clearance_test("CBC")


def test_normalize_param_key_covers_catalog_names():
    """These are the exact parameter names seeded for CBC and Creatinine Clearance - if any of
    these stop matching, the auto-calc wiring in results_view.py silently stops working for that
    field even though the calculation functions themselves are correct."""
    assert auto_calc.normalize_param_key("HB") == "hb"
    assert auto_calc.normalize_param_key("RBC") == "rbc"
    assert auto_calc.normalize_param_key("WBC") == "wbc"
    assert auto_calc.normalize_param_key("HCT") == "hct"
    assert auto_calc.normalize_param_key("MCV") == "mcv"
    assert auto_calc.normalize_param_key("MCH") == "mch"
    assert auto_calc.normalize_param_key("MCHC") == "mchc"
    assert auto_calc.normalize_param_key("Color Index") == "color_index"
    assert auto_calc.normalize_param_key("Segmented Count") == "seg_abs"
    assert auto_calc.normalize_param_key("Lymphocyte Count") == "lymph_abs"
    assert auto_calc.normalize_param_key("Monocyte Count") == "mono_abs"
    assert auto_calc.normalize_param_key("Eosinophil Count") == "eso_abs"
    assert auto_calc.normalize_param_key("Basophil Count") == "baso_abs"
    assert auto_calc.normalize_param_key("Neutrophils %") == "seg_pct"
    assert auto_calc.normalize_param_key("Lymphocytes %") == "lymph_pct"
    assert auto_calc.normalize_param_key("Serum Creatinine") == "s_creat"
    assert auto_calc.normalize_param_key("Urine Creatinine") == "u_creat"
    assert auto_calc.normalize_param_key("Urine Volume") == "vol"
    assert auto_calc.normalize_param_key("Creatinine Clearance") == "clearance"
