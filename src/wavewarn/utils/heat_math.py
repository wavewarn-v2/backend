# src/wavewarn/utils/heat_math.py
from typing import Optional

def c_to_f(c: float) -> float:
    return c * 9/5 + 32.0

def f_to_c(f: float) -> float:
    return (f - 32.0) * 5/9

def heat_index_c(t_c: Optional[float], rh: Optional[float]) -> Optional[float]:
    """
    Rothfusz regression (NWS) with Celsius I/O.
    If outside validity (t_f<80F or rh<40%), use Steadman/simple adjustment.
    """
    if t_c is None or rh is None: return None
    t_f = c_to_f(t_c)
    R = rh

    # If mild, return temp itself (approx Steadman)
    if t_f < 80 or R < 40:
        # Simple adjustment (Anderson/Rothfusz guidance)
        # increase feels-like slightly with humidity
        adj_f = t_f + 0.2 * (R/10.0)
        return f_to_c(adj_f)

    # Rothfusz (Fahrenheit)
    c1 = -42.379
    c2 = 2.04901523
    c3 = 10.14333127
    c4 = -0.22475541
    c5 = -0.00683783
    c6 = -0.05481717
    c7 = 0.00122874
    c8 = 0.00085282
    c9 = -0.00000199

    HI_f = (c1 + c2*t_f + c3*R + c4*t_f*R + c5*(t_f**2)
            + c6*(R**2) + c7*(t_f**2)*R + c8*t_f*(R**2) + c9*(t_f**2)*(R**2))

    # Low RH adjustment (NWS)
    if R < 13 and 80 <= t_f <= 112:
        adj = ((13 - R)/4) * ((17 - abs(t_f - 95.0))/17) ** 0.5
        HI_f -= adj
    # High RH adjustment
    if R > 85 and 80 <= t_f <= 87:
        HI_f += 0.02 * (R - 85) * (87 - t_f)

    return f_to_c(HI_f)

def wbgt_shade_c(t_c: Optional[float], rh: Optional[float]) -> Optional[float]:
    """
    Simple WBGT-shade approximation (no solar input):
    WBGT ≈ 0.7*Tnwb + 0.3*Tg; with no globe temp or wind/solar,
    use a practical proxy from HI and T. This is a conservative shade-only estimate.
    """
    if t_c is None or rh is None: return None
    # proxy: lean on T and humidity; keep it conservative
    # Many field rules-of-thumb put WBGT_shade a few °C below HI_c in hot/humid air.
    hi = heat_index_c(t_c, rh)
    if hi is None: return None
    # pull slightly toward ambient to avoid overstatement
    return 0.6*hi + 0.4*t_c

def tier_from_heat(hi_c: Optional[float], wbgt_c: Optional[float]) -> str:
    """
    Combine HI and WBGT; pick the worse tier.
    Thresholds (approx; adjust for your locale if needed):
      - safe:       HI<27 & WBGT<25
      - caution:    HI 27–32 or WBGT 25–28
      - risk:       HI 33–40 or WBGT 28–30.5
      - extreme:    HI>40 or WBGT>30.5
    """
    if hi_c is None and wbgt_c is None: return "unknown"

    tier_hi = (
        "safe" if (hi_c is not None and hi_c < 27) else
        "caution" if (hi_c is not None and hi_c < 33) else
        "risk" if (hi_c is not None and hi_c < 41) else
        ("extreme" if hi_c is not None else "unknown")
    )
    tier_wb = (
        "safe" if (wbgt_c is not None and wbgt_c < 25) else
        "caution" if (wbgt_c is not None and wbgt_c < 28) else
        "risk" if (wbgt_c is not None and wbgt_c < 30.5) else
        ("extreme" if wbgt_c is not None else "unknown")
    )
    order = {"unknown": 0, "safe": 1, "caution": 2, "risk": 3, "extreme": 4}
    return max([tier_hi, tier_wb], key=lambda k: order[k])

