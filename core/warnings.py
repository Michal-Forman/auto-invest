# Standard library
from typing import Any, Dict, List

# Local
from core.db.orders import Order

_SLIPPAGE_THRESHOLD = 0.03  # 3% fill price vs expected price
_FEE_RATIO_THRESHOLD = 0.006  # 0.6% fee as share of fill value
_FX_DRIFT_THRESHOLD = 0.02  # 2% fill FX rate vs submission FX rate


def compute_warnings(orders: List[Order]) -> List[Dict[str, str]]:
    """Scan filled orders for anomalies: price slippage, high fees, and FX rate drift.

    Groups identical ticker+type warnings and reports count + average deviation.
    fx_rate is stored as foreign/CZK; fill_fx_rate is stored as CZK/foreign,
    so the comparable baseline is 1/fx_rate.
    """
    raw: List[Dict[str, str]] = []
    for o in orders:
        if o.status != "FILLED":
            continue

        # Order was filled for different price than ordered
        if o.fill_price and o.price and o.price > 0:
            slippage = abs(o.fill_price - o.price) / o.price
            if slippage > _SLIPPAGE_THRESHOLD:
                direction = "above" if o.fill_price > o.price else "below"
                raw.append(
                    {
                        "ticker": o.t212_ticker,
                        "type": "Price slippage",
                        "detail": f"{slippage * 100:.1f}% {direction}",
                        "pct": f"{slippage * 100:.1f}",
                    }
                )

        # Fees were too high
        if o.fee_czk and o.filled_total_czk and o.filled_total_czk > 0:
            fee_ratio = o.fee_czk / o.filled_total_czk
            if fee_ratio > _FEE_RATIO_THRESHOLD:
                raw.append(
                    {
                        "ticker": o.t212_ticker,
                        "type": "High fee",
                        "detail": f"{fee_ratio * 100:.2f}% of fill",
                        "pct": f"{fee_ratio * 100:.2f}",
                    }
                )
        # Currency rate changed severly between order creation and order fullfillment
        if o.currency != "CZK" and o.fill_fx_rate and o.fx_rate and o.fx_rate > 0:
            fx_drift = abs(o.fill_fx_rate - o.fx_rate) / o.fx_rate
            if fx_drift > _FX_DRIFT_THRESHOLD:
                direction = "better" if o.fill_fx_rate > o.fx_rate else "worse"
                raw.append(
                    {
                        "ticker": o.t212_ticker,
                        "type": "FX shift",
                        "detail": f"{fx_drift * 100:.1f}% {direction}",
                        "pct": f"{fx_drift * 100:.1f}",
                    }
                )

    # Group by ticker+type, accumulate pct values for averaging
    groups: Dict[str, Dict[str, Any]] = {}
    for w in raw:
        key = f"{w['ticker']}|{w['type']}"
        if key not in groups:
            groups[key] = {
                "ticker": w["ticker"],
                "type": w["type"],
                "pcts": [],
                "details": [],
            }
        groups[key]["pcts"].append(float(w["pct"]))
        groups[key]["details"].append(w["detail"])

    warnings: List[Dict[str, str]] = []
    for g in groups.values():
        count = len(g["pcts"])
        avg = sum(g["pcts"]) / count
        occurrences = f"{count}×" if count > 1 else ""
        # Extract direction from last detail (they should all agree)
        direction_word = g["details"][-1].split()[-1]  # "above"/"below"/"better"/"worse"
        warnings.append(
            {
                "ticker": g["ticker"],
                "type": g["type"],
                "detail": f"{occurrences} avg {avg:.1f}% {direction_word}".strip(),
            }
        )

    return warnings
