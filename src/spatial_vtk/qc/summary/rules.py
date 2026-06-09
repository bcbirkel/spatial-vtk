"""Shared QC classification and reject-rule helpers."""

from __future__ import annotations

import numpy as np

INVENTORY_STANDARD_BANDS: tuple[tuple[str, float, float], ...] = (
    ("1-3s", 1.0, 3.0),
    ("3-5s", 3.0, 5.0),
    ("5-10s", 5.0, 10.0),
)

INVENTORY_REJECT_REASON_CODES: tuple[str, ...] = (
    "record_too_short",
    "end_before_origin_plus_60s",
    "no_clear_horizontal_onset",
    "signal_before_origin",
    "horizontal_onset_inconsistent",
    "insufficient_noise_window",
    "insufficient_signal_window",
    "insufficient_preorigin_window",
    "low_snr",
    "high_preorigin_energy",
    "high_origin_energy",
)


def station_code_has_letters(station: str) -> bool:
    """Return whether one station code contains at least one alphabetic character."""

    return any(char.isalpha() for char in str(station or "").strip().upper())


def classify_station_family(network: str, station: str) -> str:
    """Classify one station as broadband, strong-motion, or unknown."""

    station_text = str(station or "").strip().upper()
    if not station_text:
        return "unknown"
    network_key = str(network or "").strip().upper()
    if "." in station_text:
        station_text = station_text.split(".")[-1]
    alnum = "".join(char for char in station_text if char.isalnum())
    if not alnum:
        return "unknown"
    if len(alnum) >= 2 and alnum[:2].isalpha():
        return "broadband"
    if network_key == "CE":
        return "strong_motion"
    letter_count = sum(char.isalpha() for char in alnum)
    digit_count = sum(char.isdigit() for char in alnum)
    if digit_count > letter_count:
        return "strong_motion"
    if 3 <= len(alnum) <= 4 and letter_count >= max(1, digit_count):
        return "broadband"
    if not station_code_has_letters(alnum):
        return "strong_motion"
    return "broadband"


def dedupe_reason_codes(reasons: list[str]) -> list[str]:
    """Deduplicate reject reason codes while preserving first-seen order."""

    out: list[str] = []
    seen: set[str] = set()
    for reason in reasons:
        text = str(reason).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def global_trace_reject_reasons(
    *,
    record_length_s: float,
    end_rel_s: float,
    onset_reasons: list[str],
    min_end_after_origin_s: float,
    min_record_length_s: float,
) -> tuple[bool, list[str]]:
    """Apply station-level reject rules shared by every passband."""

    reasons: list[str] = []
    if not np.isfinite(record_length_s) or float(record_length_s) < float(min_record_length_s):
        reasons.append("record_too_short")
    if not np.isfinite(end_rel_s) or float(end_rel_s) < float(min_end_after_origin_s):
        reasons.append("end_before_origin_plus_60s")
    reasons.extend([str(reason).strip() for reason in onset_reasons if str(reason).strip()])
    reasons = dedupe_reason_codes(reasons)
    return bool(reasons), reasons


def reject_passband(
    *,
    global_reasons: list[str],
    snr_rms: float,
    snr_threshold: float,
    noise_window_valid: bool,
    signal_window_valid: bool,
    pre_origin_window_valid: bool,
    pre_origin_signal_ratio: float,
    pre_origin_signal_ratio_threshold: float,
    origin_window_valid: bool,
    origin_signal_ratio: float,
) -> tuple[bool, list[str]]:
    """Apply passband-specific reject rules and merge shared global reasons."""

    reasons = list(global_reasons)
    if not bool(noise_window_valid):
        reasons.append("insufficient_noise_window")
    if not bool(signal_window_valid):
        reasons.append("insufficient_signal_window")
    if bool(noise_window_valid) and bool(signal_window_valid):
        if not np.isfinite(snr_rms) or float(snr_rms) < float(snr_threshold):
            reasons.append("low_snr")
    if bool(pre_origin_window_valid) and bool(signal_window_valid):
        if not np.isfinite(pre_origin_signal_ratio) or float(pre_origin_signal_ratio) > float(pre_origin_signal_ratio_threshold):
            reasons.append("high_preorigin_energy")
    if bool(origin_window_valid) and bool(signal_window_valid):
        if not np.isfinite(origin_signal_ratio) or float(origin_signal_ratio) > float(pre_origin_signal_ratio_threshold):
            reasons.append("high_origin_energy")
    reasons = dedupe_reason_codes(reasons)
    return bool(reasons), reasons


def dominant_energy_band(
    freqs_hz: np.ndarray,
    power: np.ndarray,
    band_edges_hz: dict[str, tuple[float, float]],
) -> tuple[str, dict[str, float]]:
    """Resolve which standard band carries the most spectral power."""

    freqs = np.asarray(freqs_hz, dtype=float)
    power_arr = np.asarray(power, dtype=float)
    finite = np.isfinite(freqs) & np.isfinite(power_arr) & (freqs > 0.0) & (power_arr >= 0.0)
    if not np.any(finite):
        return "unknown", {str(label): 0.0 for label in band_edges_hz}
    freqs = freqs[finite]
    power_arr = power_arr[finite]
    totals: dict[str, float] = {}
    for label, (fmin_hz, fmax_hz) in band_edges_hz.items():
        mask = (freqs >= float(fmin_hz)) & (freqs <= float(fmax_hz))
        totals[str(label)] = float(np.sum(power_arr[mask])) if np.any(mask) else 0.0
    total_power = float(sum(totals.values()))
    if not np.isfinite(total_power) or total_power <= 0.0:
        return "unknown", {label: 0.0 for label in totals}
    fractions = {label: (value / total_power) for label, value in totals.items()}
    return max(fractions.items(), key=lambda item: item[1])[0], fractions
