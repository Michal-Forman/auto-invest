from db.orders import InstrumentType, Currency
from typing import Dict

T212_TO_YF = {
    "VWCEd_EQ": "VWCE.DE",
    "CSPX_EQ": "CSPX.L",
    "EMIMl_EQ": "EMIM.L",
    "SC0Ud_EQ": "X7PS.L",
    "XNAQl_EQ": "XNAQ.L",
    "VERGl_EQ": "VERG.L",
    "BX_US_EQ": "BX",
    "KKR_US_EQ": "KKR",
    "RBOTl_EQ": "RBOT.L",
    "BTC": "BTC-USD",
}

INSTRUMENT_CAPS = {
    "VWCEd_EQ": "none",
    "CSPX_EQ": "none",
    "EMIMl_EQ": "none",
    "SC0Ud_EQ": "soft",
    "XNAQl_EQ": "none",
    "VERGl_EQ": "none",
    "BX_US_EQ": "soft",
    "KKR_US_EQ": "soft",
    "RBOTl_EQ": "none",
    "BTC": "hard",
}

INSTRUMENT_CURRENCIES: Dict[str, Currency] = {
    "VWCEd_EQ": "EUR",
    "CSPX_EQ": "USD",
    "EMIMl_EQ": "GBX",
    "SC0Ud_EQ": "EUR",
    "XNAQl_EQ": "GBP",
    "VERGl_EQ": "GBP",
    "BX_US_EQ": "USD",
    "KKR_US_EQ": "USD",
    "RBOTl_EQ": "USD",
    "BTC": "CZK",
}

INSTRUMENT_TYPES: Dict[str, InstrumentType] = {
    "VWCEd_EQ": "ETF",
    "CSPX_EQ": "ETF",
    "EMIMl_EQ": "ETF",
    "SC0Ud_EQ": "ETF",
    "XNAQl_EQ": "ETF",
    "VERGl_EQ": "ETF",
    "BX_US_EQ": "STOCK",
    "KKR_US_EQ": "STOCK",
    "RBOTl_EQ": "ETF",
    "BTC": "CRYPTO",
}


