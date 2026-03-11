# Standard library
from types import SimpleNamespace
from uuid import UUID

# Third-party
import pytest
from pytest_mock import MockerFixture

# Local
from core.coinmate import Coinmate
from core.db.orders import Order
from core.db.runs import Run
from core.executor import Executor
from core.instruments import Instruments
from core.settings import PortfolioSettings
from core.trading212 import Trading212

RUN_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


def _mock_instruments(
    mocker: MockerFixture, ath: float = 150.0, current: float = 100.0
) -> None:
    """Patch Instruments class-level methods so no yfinance calls are made."""
    mocker.patch.object(
        Instruments,
        "get_ath",
        side_effect=lambda ticker: 2_000_000.0 if ticker == "BTC" else ath,
    )
    mocker.patch.object(
        Instruments,
        "get_current_price",
        side_effect=lambda ticker: 1_500_000.0 if ticker == "BTC" else current,
    )
    mocker.patch.object(Instruments, "get_btc_price", return_value=1_500_000.0)
    mocker.patch.object(Instruments, "get_fx_rate_to_czk", return_value=25.0)


def _mock_exchange_methods(
    mocker: MockerFixture,
    t212: Trading212,
    coinmate: Coinmate,
    t212_pie_response: dict,
    t212_order_place_response: dict,
    coinmate_buy_response: dict,
) -> None:
    """Patch HTTP-calling methods on the real exchange client instances."""
    mocker.patch.object(t212, "pie", return_value=t212_pie_response)
    mocker.patch.object(
        t212, "equity_order_place_market", return_value=t212_order_place_response
    )
    mocker.patch.object(coinmate, "buy_instant", return_value=coinmate_buy_response)
    mocker.patch.object(Order, "post_to_db", return_value=None)


class TestCashDistributionToOrders:
    def test_cash_distribution_to_order_amounts_are_consistent(
        self,
        mocker: MockerFixture,
        t212: Trading212,
        coinmate: Coinmate,
        portfolio_settings: PortfolioSettings,
        supabase_mocks: SimpleNamespace,
        t212_pie_response: dict,
        t212_order_place_response: dict,
        coinmate_buy_response: dict,
    ) -> None:
        """The CZK amount from distribute_cash matches Order.total_czk after executor chain."""
        _mock_instruments(mocker)
        _mock_exchange_methods(
            mocker,
            t212,
            coinmate,
            t212_pie_response,
            t212_order_place_response,
            coinmate_buy_response,
        )

        instruments = Instruments(t212, coinmate, portfolio_settings)
        executor = Executor(t212, coinmate)

        result = instruments.distribute_cash()
        orders = executor.place_orders(
            result["cash_distribution"], result["multipliers"], RUN_ID
        )

        vwce_order = next(o for o in orders if o.t212_ticker == "VWCEd_EQ")
        assert vwce_order.total_czk == pytest.approx(
            result["cash_distribution"]["VWCEd_EQ"], rel=1e-4
        )
        assert vwce_order.multiplier == pytest.approx(result["multipliers"]["VWCEd_EQ"])

    def test_multiplier_flows_from_instruments_to_order_record(
        self,
        mocker: MockerFixture,
        t212: Trading212,
        coinmate: Coinmate,
        portfolio_settings: PortfolioSettings,
        supabase_mocks: SimpleNamespace,
        t212_pie_response: dict,
        t212_order_place_response: dict,
        coinmate_buy_response: dict,
    ) -> None:
        """ATH=200, current=100 → drop=50% → multiplier=2.0 for VWCEd_EQ (cap='none')."""
        _mock_instruments(mocker, ath=200.0, current=100.0)
        _mock_exchange_methods(
            mocker,
            t212,
            coinmate,
            t212_pie_response,
            t212_order_place_response,
            coinmate_buy_response,
        )

        instruments = Instruments(t212, coinmate, portfolio_settings)
        executor = Executor(t212, coinmate)

        result = instruments.distribute_cash()
        orders = executor.place_orders(
            result["cash_distribution"], result["multipliers"], RUN_ID
        )

        vwce_order = next(o for o in orders if o.t212_ticker == "VWCEd_EQ")
        assert vwce_order.multiplier == pytest.approx(2.0, rel=0.001)

        run_update = Run.process_new_run_data(orders)
        assert run_update.multipliers is not None
        assert run_update.multipliers["VWCEd_EQ"] == pytest.approx(2.0, rel=0.001)

    def test_distribution_sums_match_invest_amount(
        self,
        mocker: MockerFixture,
        t212: Trading212,
        coinmate: Coinmate,
        portfolio_settings: PortfolioSettings,
        supabase_mocks: SimpleNamespace,
        t212_pie_response: dict,
        t212_order_place_response: dict,
        coinmate_buy_response: dict,
    ) -> None:
        """Total CZK across all placed orders ≈ INVEST_AMOUNT (5000.0)."""
        _mock_instruments(mocker)
        _mock_exchange_methods(
            mocker,
            t212,
            coinmate,
            t212_pie_response,
            t212_order_place_response,
            coinmate_buy_response,
        )

        instruments = Instruments(t212, coinmate, portfolio_settings)
        executor = Executor(t212, coinmate)

        result = instruments.distribute_cash()
        orders = executor.place_orders(
            result["cash_distribution"], result["multipliers"], RUN_ID
        )

        total = sum(o.total_czk for o in orders)
        assert total == pytest.approx(5000.0, rel=0.01)

    def test_t212_order_failure_sets_status_failed_and_run_counts_it(
        self,
        mocker: MockerFixture,
        t212: Trading212,
        coinmate: Coinmate,
        portfolio_settings: PortfolioSettings,
        supabase_mocks: SimpleNamespace,
        t212_pie_response: dict,
        coinmate_buy_response: dict,
    ) -> None:
        """T212 error response → FAILED order; process_new_run_data counts it correctly."""
        _mock_instruments(mocker)
        mocker.patch.object(t212, "pie", return_value=t212_pie_response)
        mocker.patch.object(
            t212,
            "equity_order_place_market",
            return_value={"req": {}, "res": None, "err": "timeout"},
        )
        mocker.patch.object(coinmate, "buy_instant", return_value=coinmate_buy_response)
        mocker.patch.object(Order, "post_to_db", return_value=None)

        instruments = Instruments(t212, coinmate, portfolio_settings)
        executor = Executor(t212, coinmate)

        result = instruments.distribute_cash()
        orders = executor.place_orders(
            result["cash_distribution"], result["multipliers"], RUN_ID
        )

        failed = [o for o in orders if o.status == "FAILED"]
        assert len(failed) == 1

        run_update = Run.process_new_run_data(orders)
        assert run_update.failed_orders == 1
        assert run_update.error is not None
        assert "timeout" in run_update.error

    def test_idempotency_key_generated_and_unique_per_order(
        self,
        mocker: MockerFixture,
        t212: Trading212,
        coinmate: Coinmate,
        portfolio_settings: PortfolioSettings,
        supabase_mocks: SimpleNamespace,
        t212_pie_response: dict,
        t212_order_place_response: dict,
        coinmate_buy_response: dict,
    ) -> None:
        """Every Order gets a non-null SHA-256 idempotency key unique within the run."""
        _mock_instruments(mocker)
        _mock_exchange_methods(
            mocker,
            t212,
            coinmate,
            t212_pie_response,
            t212_order_place_response,
            coinmate_buy_response,
        )

        instruments = Instruments(t212, coinmate, portfolio_settings)
        executor = Executor(t212, coinmate)

        result = instruments.distribute_cash()
        orders = executor.place_orders(
            result["cash_distribution"], result["multipliers"], RUN_ID
        )

        keys = [o.idempotency_key for o in orders]
        assert all(k is not None for k in keys)
        assert len(set(keys)) == len(keys)  # all unique
        assert all(len(k) == 64 for k in keys if k is not None)  # SHA-256 hex digest

    def test_process_new_run_data_fields_correct(
        self,
        mocker: MockerFixture,
        t212: Trading212,
        coinmate: Coinmate,
        portfolio_settings: PortfolioSettings,
        supabase_mocks: SimpleNamespace,
        t212_pie_response: dict,
        t212_order_place_response: dict,
        coinmate_buy_response: dict,
    ) -> None:
        """process_new_run_data builds a correctly populated RunUpdate."""
        _mock_instruments(mocker)
        _mock_exchange_methods(
            mocker,
            t212,
            coinmate,
            t212_pie_response,
            t212_order_place_response,
            coinmate_buy_response,
        )

        instruments = Instruments(t212, coinmate, portfolio_settings)
        executor = Executor(t212, coinmate)

        result = instruments.distribute_cash()
        orders = executor.place_orders(
            result["cash_distribution"], result["multipliers"], RUN_ID
        )

        run_update = Run.process_new_run_data(orders)

        assert run_update.status == "FINISHED"
        assert run_update.total_orders == len(orders)
        assert run_update.successful_orders is not None
        assert run_update.failed_orders is not None
        assert (run_update.successful_orders or 0) + (
            run_update.failed_orders or 0
        ) == len(orders)
        assert run_update.distribution is not None
        assert set(run_update.distribution.keys()) == {o.t212_ticker for o in orders}
        assert run_update.planned_total_czk == pytest.approx(
            sum(o.total_czk for o in orders)
        )


class TestExchangeApiCallArguments:
    def test_t212_called_with_correct_ticker_and_quantity(
        self,
        mocker: MockerFixture,
        t212: Trading212,
        coinmate: Coinmate,
        portfolio_settings: PortfolioSettings,
        t212_order_place_response: dict,
    ) -> None:
        """equity_order_place_market receives the right ticker and exact share quantity."""
        mocker.patch.object(Instruments, "get_fx_rate_to_czk", return_value=25.0)
        mocker.patch.object(Instruments, "get_current_price", return_value=100.0)
        mock_eq_order = mocker.patch.object(
            t212, "equity_order_place_market", return_value=t212_order_place_response
        )
        mocker.patch.object(Order, "post_to_db", return_value=None)

        executor = Executor(t212, coinmate)
        executor.place_orders({"VWCEd_EQ": 5000.0}, {"VWCEd_EQ": 1.0}, RUN_ID)

        # 5000 CZK / 25 (fx) / 100 (price) = 2.0 shares
        mock_eq_order.assert_called_once_with("VWCEd_EQ", 2.0)

    def test_t212_quantity_rounded_to_3_decimal_places(
        self,
        mocker: MockerFixture,
        t212: Trading212,
        coinmate: Coinmate,
        portfolio_settings: PortfolioSettings,
        t212_order_place_response: dict,
    ) -> None:
        """Share quantity is rounded to 3 decimal places before being sent to T212."""
        mocker.patch.object(Instruments, "get_fx_rate_to_czk", return_value=25.0)
        mocker.patch.object(Instruments, "get_current_price", return_value=100.3)
        mock_eq_order = mocker.patch.object(
            t212, "equity_order_place_market", return_value=t212_order_place_response
        )
        mocker.patch.object(Order, "post_to_db", return_value=None)

        executor = Executor(t212, coinmate)
        executor.place_orders({"VWCEd_EQ": 5000.0}, {"VWCEd_EQ": 1.0}, RUN_ID)

        # 5000 / 25 / 100.3 = 1.99401..., rounded to 3dp = 1.994
        expected_qty = round(5000.0 / 25.0 / 100.3, 3)
        mock_eq_order.assert_called_once_with("VWCEd_EQ", expected_qty)

    def test_coinmate_called_with_correct_amount_and_pair(
        self,
        mocker: MockerFixture,
        t212: Trading212,
        coinmate: Coinmate,
        portfolio_settings: PortfolioSettings,
        coinmate_buy_response: dict,
    ) -> None:
        """buy_instant receives the exact CZK amount and the BTC_CZK pair string."""
        mocker.patch.object(Instruments, "get_btc_price", return_value=1_500_000.0)
        mock_buy = mocker.patch.object(
            coinmate, "buy_instant", return_value=coinmate_buy_response
        )
        mocker.patch.object(Order, "post_to_db", return_value=None)

        executor = Executor(t212, coinmate)
        executor.place_orders({"BTC": 250.0}, {"BTC": 1.0}, RUN_ID)

        mock_buy.assert_called_once_with(250.0, "BTC_CZK")

    def test_coinmate_amount_rounded_to_2_decimal_places(
        self,
        mocker: MockerFixture,
        t212: Trading212,
        coinmate: Coinmate,
        portfolio_settings: PortfolioSettings,
        coinmate_buy_response: dict,
    ) -> None:
        """CZK amount is rounded to 2 decimal places before being sent to Coinmate."""
        mocker.patch.object(Instruments, "get_btc_price", return_value=1_500_000.0)
        mock_buy = mocker.patch.object(
            coinmate, "buy_instant", return_value=coinmate_buy_response
        )
        mocker.patch.object(Order, "post_to_db", return_value=None)

        executor = Executor(t212, coinmate)
        executor.place_orders({"BTC": 1234.567}, {"BTC": 1.0}, RUN_ID)

        # 1234.567 rounded to 2dp = 1234.57
        mock_buy.assert_called_once_with(1234.57, "BTC_CZK")
