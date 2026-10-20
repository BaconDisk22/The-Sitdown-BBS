"""Offline v1.0 release gates. Unknown evidence always blocks release."""
REQUIRED = ("unit_tests_passed", "intel_mac_dmg_tested", "usb_radio_tested",
            "tcp_radio_tested", "centralnj_two_way_verified", "credentials_reviewed")


def evaluate_release(evidence):
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be a mapping")
    missing = [key for key in REQUIRED if evidence.get(key) is not True]
    return {"ready": not missing, "missing": missing}
