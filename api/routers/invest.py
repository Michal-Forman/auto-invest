# Standard library
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import math
from typing import Dict, List, Optional, Tuple

# Third-party
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

# Local
from api.dependencies import (
    get_coinmate_for_user,
    get_current_user_id,
    get_mailer_for_user,
    get_t212_for_user,
    get_user_settings_for_user,
)
from api.routers.instruments import build_ratio_data, distribute_for_amount
from api.schemas import (
    ExchangeFundingItem,
    FundingCheckResponse,
    InvestOrPendingResponse,
    InvestResponse,
    PendingInvestmentResponse,
)
from core.coinmate import Coinmate
from core.db.orders import Order
from core.db.runs import Run, RunUpdate
from core.executor import Executor
from core.funding import OneTimeFundingCheck, one_time_funding_status
from core.log import log
from core.mailer import Mailer
from core.pending_investments import PENDING_EXPIRY_DAYS
from core.precision import quantize_czk, to_decimal
from core.qr import qr_data_uri
from core.settings import UserSettings
from core.trading212 import Trading212

router = APIRouter()

# A double-submitted POST /invest lands two runs of real orders; the client-side
# disabled button is not enough. Reject a second one-time invest inside this window.
_RECENT_INVEST_WINDOW = timedelta(minutes=2)


def _safe_send_confirmation(
    mailer: Mailer,
    run: Run,
    orders: List[Order],
    cash_distribution: Dict[str, Decimal],
    multipliers: Dict[str, Decimal],
) -> None:
    """Send the investment confirmation, swallowing any SMTP/DB failure so a mail
    problem never surfaces on the request that already placed the orders."""
    try:
        mailer.send_investment_confirmation(run, orders, cash_distribution, multipliers)
    except Exception as e:  # noqa: BLE001 - best-effort notification
        log.warning(f"Failed to send investment confirmation for run {run.id}: {e}")


def _resolve_distribution(
    user_id: str,
    user_settings: UserSettings,
    t212: Trading212,
    coinmate: Coinmate,
    invest_amount: float,
) -> Tuple[Dict[str, Decimal], Dict[str, Decimal], Dict[str, Decimal]]:
    """Return the one-time cash distribution, its order multipliers, and the
    reserve distribution for the next regular DCA run at the current ratios."""
    data = build_ratio_data(user_id, user_settings, t212, coinmate)
    adj_weights: Dict[str, float] = data["adj_weights"]
    multipliers_map: Dict[str, float] = data["multipliers"]

    cash_distribution = distribute_for_amount(invest_amount, adj_weights)
    multipliers: Dict[str, Decimal] = {
        ticker: to_decimal(multipliers_map[ticker]) for ticker in cash_distribution
    }
    dca_reserve: Dict[str, Decimal] = {
        ticker: to_decimal(czk) for ticker, czk in data["next_czk"].items() if czk > 0
    }

    return cash_distribution, multipliers, dca_reserve


def _funding_check_response(
    user_settings: UserSettings,
    t212: Trading212,
    coinmate: Coinmate,
    cash_distribution: Dict[str, Decimal],
    dca_reserve: Dict[str, Decimal],
) -> FundingCheckResponse:
    """Compare live balances against the one-time invest plus the DCA reserve,
    attaching top-up account/VS/QR details for any short exchange."""
    statuses: List[OneTimeFundingCheck] = one_time_funding_status(
        cash_distribution, dca_reserve, t212, coinmate
    )
    deposit_config: Dict[str, Tuple[Optional[str], Optional[str]]] = {
        "T212": (user_settings.t212_deposit_account, user_settings.t212_deposit_vs),
        "COINMATE": (
            user_settings.coinmate_deposit_account,
            user_settings.coinmate_deposit_vs,
        ),
    }

    items: List[ExchangeFundingItem] = []
    for status in statuses:
        account, vs = deposit_config.get(status.exchange, (None, None))
        suggested_topup: Optional[float] = None
        qr: Optional[str] = None
        if status.is_short:
            suggested_topup = float(math.ceil(status.shortfall_czk / 100) * 100)
            if account and vs:
                qr = qr_data_uri(account, vs, suggested_topup)

        items.append(
            ExchangeFundingItem(
                exchange=status.exchange,
                available_czk=float(quantize_czk(status.available_czk)),
                one_time_czk=float(status.one_time_czk),
                dca_reserve_czk=float(status.dca_reserve_czk),
                needed_czk=float(status.needed_czk),
                shortfall_czk=float(status.shortfall_czk),
                is_short=status.is_short,
                account=account,
                vs=vs,
                suggested_topup_czk=suggested_topup,
                qr_data_uri=qr,
            )
        )

    return FundingCheckResponse(
        sufficient=not any(item.is_short for item in items), exchanges=items
    )


def _place_immediately(
    user_id: str,
    t212: Trading212,
    coinmate: Coinmate,
    cash_distribution: Dict[str, Decimal],
    multipliers: Dict[str, Decimal],
    run: Optional[Run] = None,
    background_tasks: Optional[BackgroundTasks] = None,
) -> InvestResponse:
    """Create (unless `run` is already a pending one) and fill a run right now."""
    if run is None:
        run = Run.create_run(
            datetime.now(timezone.utc),
            get_user_settings_for_user(user_id).portfolio,
            user_id=user_id,
            investment_type="one_time",
        )
    assert run.id is not None

    executor = Executor(t212, coinmate, user_id=user_id)
    orders: List[Order] = executor.place_orders(
        cash_distribution, multipliers, run_id=run.id, investment_type="one_time"
    )

    run_update: RunUpdate = Run.process_new_run_data(orders)
    run.update_in_db(run_update)

    # Send the completion email off the request path — SMTP can block for seconds.
    if background_tasks is not None:
        mailer: Optional[Mailer] = get_mailer_for_user(user_id)
        if mailer is not None:
            background_tasks.add_task(
                _safe_send_confirmation,
                mailer,
                run,
                orders,
                cash_distribution,
                multipliers,
            )

    return InvestResponse(
        run_id=str(run.id), total_czk=float(sum(o.total_czk for o in orders))
    )


def _pending_response(
    run: Run, funding: FundingCheckResponse
) -> PendingInvestmentResponse:
    assert run.id is not None
    expires_at = run.started_at + timedelta(days=PENDING_EXPIRY_DAYS)
    return PendingInvestmentResponse(
        run_id=str(run.id),
        amount_czk=float(run.planned_total_czk or 0),
        created_at=run.started_at.isoformat(),
        expires_at=expires_at.isoformat(),
        funding=funding,
    )


@router.get("/invest/funding-check", response_model=FundingCheckResponse)
def check_funding(
    amount: float = 0,
    user_id: str = Depends(get_current_user_id),
) -> FundingCheckResponse:
    """Check live exchange balances against a one-time invest of `amount` plus a
    reserve for the next regular DCA run, returning top-up details when short."""
    user_settings = get_user_settings_for_user(user_id)
    invest_amount = amount if amount > 0 else user_settings.portfolio.invest_amount

    t212 = get_t212_for_user(user_id)
    coinmate = get_coinmate_for_user(user_id)
    cash_distribution, _, dca_reserve = _resolve_distribution(
        user_id, user_settings, t212, coinmate, invest_amount
    )

    return _funding_check_response(
        user_settings, t212, coinmate, cash_distribution, dca_reserve
    )


@router.post("/invest", response_model=InvestResponse)
def place_investment(
    background_tasks: BackgroundTasks,
    amount: float = 0,
    user_id: str = Depends(get_current_user_id),
) -> InvestResponse:
    """Place a one-time manual investment using ATH-adjusted distribution.

    Blocked with a 402 (no run/orders created) if either exchange can't cover
    this investment plus a reserve for the next regular DCA run. Blocked with a
    409 if a one-time invest was just placed or is pending.
    """
    if Run.get_pending_runs(user_id=user_id) or Run.recent_one_time_run_exists(
        user_id, _RECENT_INVEST_WINDOW
    ):
        raise HTTPException(
            status_code=409,
            detail="A one-time investment was just placed or is pending. "
            "Check the Runs page.",
        )

    user_settings = get_user_settings_for_user(user_id)
    invest_amount = amount if amount > 0 else user_settings.portfolio.invest_amount

    t212 = get_t212_for_user(user_id)
    coinmate = get_coinmate_for_user(user_id)
    cash_distribution, multipliers, dca_reserve = _resolve_distribution(
        user_id, user_settings, t212, coinmate, invest_amount
    )

    funding = _funding_check_response(
        user_settings, t212, coinmate, cash_distribution, dca_reserve
    )
    if not funding.sufficient:
        raise HTTPException(status_code=402, detail=funding.model_dump())

    return _place_immediately(
        user_id,
        t212,
        coinmate,
        cash_distribution,
        multipliers,
        background_tasks=background_tasks,
    )


@router.post("/invest/pending", response_model=InvestOrPendingResponse)
def register_pending_investment(
    background_tasks: BackgroundTasks,
    amount: float = 0,
    user_id: str = Depends(get_current_user_id),
) -> InvestOrPendingResponse:
    """The "I've sent the money" flow: place the investment now if funds have
    already arrived, otherwise register it to be retried automatically as funds
    arrive.

    409s if the user already has a pending one-time investment.
    """
    if Run.get_pending_runs(user_id=user_id):
        raise HTTPException(
            status_code=409, detail="A one-time investment is already pending."
        )

    user_settings = get_user_settings_for_user(user_id)
    invest_amount = amount if amount > 0 else user_settings.portfolio.invest_amount

    t212 = get_t212_for_user(user_id)
    coinmate = get_coinmate_for_user(user_id)
    cash_distribution, multipliers, dca_reserve = _resolve_distribution(
        user_id, user_settings, t212, coinmate, invest_amount
    )

    funding = _funding_check_response(
        user_settings, t212, coinmate, cash_distribution, dca_reserve
    )
    if funding.sufficient:
        invest = _place_immediately(
            user_id,
            t212,
            coinmate,
            cash_distribution,
            multipliers,
            background_tasks=background_tasks,
        )
        return InvestOrPendingResponse(placed=True, invest=invest)

    run = Run.create_run(
        datetime.now(timezone.utc),
        user_settings.portfolio,
        user_id=user_id,
        investment_type="one_time",
    )
    run.update_in_db(
        RunUpdate(
            status="PENDING",
            distribution=dict(cash_distribution),
            multipliers=dict(multipliers),
            planned_total_czk=sum(cash_distribution.values(), Decimal("0")),
        )
    )

    return InvestOrPendingResponse(
        placed=False, pending=_pending_response(run, funding)
    )


@router.get("/invest/pending", response_model=Optional[PendingInvestmentResponse])
def get_pending_investment(
    user_id: str = Depends(get_current_user_id),
) -> Optional[PendingInvestmentResponse]:
    """Return the user's current pending one-time investment, or null if none."""
    pending = Run.get_pending_runs(user_id=user_id)
    if not pending:
        return None
    run = pending[0]

    user_settings = get_user_settings_for_user(user_id)
    t212 = get_t212_for_user(user_id)
    coinmate = get_coinmate_for_user(user_id)

    cash_distribution: Dict[str, Decimal] = {
        ticker: to_decimal(czk) for ticker, czk in (run.distribution or {}).items()
    }
    data = build_ratio_data(user_id, user_settings, t212, coinmate)
    dca_reserve: Dict[str, Decimal] = {
        ticker: to_decimal(czk) for ticker, czk in data["next_czk"].items() if czk > 0
    }
    funding = _funding_check_response(
        user_settings, t212, coinmate, cash_distribution, dca_reserve
    )

    return _pending_response(run, funding)


@router.post("/invest/pending/cancel", response_model=PendingInvestmentResponse)
def cancel_pending_investment(
    user_id: str = Depends(get_current_user_id),
) -> PendingInvestmentResponse:
    """Cancel the user's pending one-time investment."""
    pending = Run.get_pending_runs(user_id=user_id)
    if not pending:
        raise HTTPException(status_code=404, detail="No pending investment.")
    run = pending[0]

    run.update_in_db(
        RunUpdate(status="CANCELLED", finished_at=datetime.now(timezone.utc))
    )

    empty_funding = FundingCheckResponse(sufficient=True, exchanges=[])
    return _pending_response(run, empty_funding)
