# Standard library
import base64
import io

# Third-party
import qrcode  # type: ignore[import-untyped]
import qrcode.constants  # type: ignore[import-untyped]


def czech_account_to_iban(account: str) -> str:
    """Convert a Czech account number (e.g. '19-123456789/0800') to IBAN (e.g. 'CZ...')."""
    number_part, bank_code = account.strip().split("/")
    number_part, bank_code = number_part.strip(), bank_code.strip()
    if "-" in number_part:
        prefix, base_num = number_part.split("-")
    else:
        prefix, base_num = "0", number_part
    bban = f"{bank_code:0>4}{int(prefix):06d}{int(base_num):010d}"
    # IBAN check digits: rearrange as BBAN + "CZ00", replace letters, mod-97
    numeric = int(bban + "123500")  # C=12, Z=35, 00
    check = 98 - (numeric % 97)
    return f"CZ{check:02d}{bban}"


def make_spd_qr(account: str, vs: str, amount: float) -> bytes:
    """Return PNG bytes of a Czech SPD QR code for the given account, variable symbol, and amount."""
    iban = czech_account_to_iban(account)
    spd = f"SPD*1.0*ACC:{iban}*AM:{amount:.2f}*CC:CZK*X-VS:{vs}*PT:IP"
    img = qrcode.make(spd, error_correction=qrcode.constants.ERROR_CORRECT_M)
    buf = io.BytesIO()
    img.save(buf, format="PNG")  # type: ignore[call-arg]
    return buf.getvalue()


def qr_data_uri(account: str, vs: str, amount: float) -> str:
    """Return the SPD QR code as a base64 data: URI, ready for an <img src>."""
    png = make_spd_qr(account, vs, amount)
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")
