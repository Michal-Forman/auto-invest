# Standard library
from typing import Dict

# Local
from core.db.orders import Currency, InstrumentType

T212_TO_YF: Dict[str, str] = {
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

INSTRUMENT_CAPS: Dict[str, str] = {
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

INSTRUMENT_NAMES: Dict[str, str] = {
    "VWCEd_EQ": "Vanguard FTSE All-World UCITS ETF (Acc)",
    "CSPX_EQ": "Ishares core S&P 500 (Acc)",
    "EMIMl_EQ": "Ishares core MSCI EM IMI (Acc)",
    "SC0Ud_EQ": "Invesco STOXX Europe 600 optimised banks (Acc)",
    "XNAQl_EQ": "Xtrackers NASDAQ 100 (Acc)",
    "VERGl_EQ": "Vanguard FTSE developed Europe ex UK (Acc)",
    "BX_US_EQ": "Blackstone",
    "KKR_US_EQ": "KKR & Co",
    "RBOTl_EQ": "Ishares automation & robotics (Acc)",
    "BTC": "Bitcoin",
}
