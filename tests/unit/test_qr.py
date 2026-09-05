# Local
from core.qr import czech_account_to_iban, make_spd_qr, qr_data_uri

# ---------------------------------------------------------------------------
# Tests: czech_account_to_iban (pure function)
# ---------------------------------------------------------------------------


class TestCzechAccountToIban:
    def test_returns_string_starting_with_cz(self) -> None:
        assert czech_account_to_iban("19-123456789/0800").startswith("CZ")

    def test_iban_has_correct_length(self) -> None:
        # CZ IBAN: "CZ" + 2 check digits + 20 BBAN = 24 chars
        assert len(czech_account_to_iban("19-123456789/0800")) == 24

    def test_account_without_prefix(self) -> None:
        iban = czech_account_to_iban("123456789/0800")
        assert iban.startswith("CZ")
        assert len(iban) == 24

    def test_different_base_numbers_give_different_ibans(self) -> None:
        iban1 = czech_account_to_iban("123456789/0800")
        iban2 = czech_account_to_iban("987654321/0800")
        assert iban1 != iban2

    def test_check_digits_are_valid_numerals(self) -> None:
        iban = czech_account_to_iban("19-123456789/0800")
        assert iban[2:4].isdigit()

    def test_deterministic_for_same_input(self) -> None:
        assert czech_account_to_iban("19-2000145399/0800") == czech_account_to_iban(
            "19-2000145399/0800"
        )

    def test_different_bank_codes_produce_different_ibans(self) -> None:
        iban1 = czech_account_to_iban("123456789/0800")
        iban2 = czech_account_to_iban("123456789/2010")
        assert iban1 != iban2


# ---------------------------------------------------------------------------
# Tests: make_spd_qr (pure function)
# ---------------------------------------------------------------------------


class TestMakeSpdQr:
    def test_returns_bytes(self) -> None:
        result = make_spd_qr("19-123456789/0800", "12345", 1000.0)
        assert isinstance(result, bytes)

    def test_returns_png_magic_bytes(self) -> None:
        result = make_spd_qr("19-123456789/0800", "12345", 1000.0)
        assert result[:4] == b"\x89PNG"

    def test_different_amounts_produce_different_qrs(self) -> None:
        qr1 = make_spd_qr("19-123456789/0800", "12345", 1000.0)
        qr2 = make_spd_qr("19-123456789/0800", "12345", 2000.0)
        assert qr1 != qr2

    def test_different_accounts_produce_different_qrs(self) -> None:
        qr1 = make_spd_qr("19-123456789/0800", "12345", 1000.0)
        qr2 = make_spd_qr("987654321/0800", "12345", 1000.0)
        assert qr1 != qr2

    def test_different_variable_symbols_produce_different_qrs(self) -> None:
        qr1 = make_spd_qr("19-123456789/0800", "11111", 1000.0)
        qr2 = make_spd_qr("19-123456789/0800", "99999", 1000.0)
        assert qr1 != qr2


# ---------------------------------------------------------------------------
# Tests: qr_data_uri (pure function)
# ---------------------------------------------------------------------------


class TestQrDataUri:
    def test_returns_data_uri_with_png_mime_type(self) -> None:
        uri = qr_data_uri("19-123456789/0800", "12345", 1000.0)
        assert uri.startswith("data:image/png;base64,")

    def test_base64_payload_decodes_to_same_png_bytes(self) -> None:
        import base64

        uri = qr_data_uri("19-123456789/0800", "12345", 1000.0)
        payload = uri.removeprefix("data:image/png;base64,")
        assert base64.b64decode(payload) == make_spd_qr(
            "19-123456789/0800", "12345", 1000.0
        )
