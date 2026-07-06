from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from veridian_quant.v2.analysis.s2_state_reconstruction import (
    compute_deterioration_candidates,
    compute_next_open_exit_feasibility,
    expand_trade_lifecycle_dates,
    first_deterioration_occurrences,
    infer_ohlc_load_window,
    join_daily_states_to_trades,
    load_ohlc_for_reconstruction,
    load_ohlc_from_daily_loader,
    parse_s2_state_label,
    summarize_reconstruction_coverage,
    validate_entry_state_match,
)


def test_parse_state_label_with_expected_components() -> None:
    parsed = parse_s2_state_label(
        "RET_STRONG_DOWN|VOL_HIGH|DD_DEEP|LOW_MID_RANGE"
    )

    assert parsed["raw_state_label"] == "RET_STRONG_DOWN|VOL_HIGH|DD_DEEP|LOW_MID_RANGE"
    assert parsed["return_state"] == "RET_STRONG_DOWN"
    assert parsed["volatility_state"] == "VOL_HIGH"
    assert parsed["drawdown_state_component"] == "DD_DEEP"
    assert parsed["range_state"] == "LOW_MID_RANGE"
    assert parsed["unknown_components"] == []
    assert parsed["parse_status"] == "PARSED"


def test_parse_missing_and_unknown_state_label() -> None:
    missing = parse_s2_state_label("")
    unknown = parse_s2_state_label("RET_UP|VOL_MID|DD_SHALLOW|LOW_NEAR|ODD")

    assert missing["parse_status"] == "MISSING"
    assert unknown["return_state"] == "RET_UP"
    assert unknown["volatility_state"] == "VOL_MID"
    assert unknown["unknown_components"] == ["ODD"]
    assert unknown["parse_status"] == "PARSED_WITH_UNKNOWN_COMPONENTS"


def test_expand_trade_lifecycle_across_symbol_trading_dates() -> None:
    trades = _trades(exit_date="2026-01-06")
    lifecycle = expand_trade_lifecycle_dates(trades, {"AAA": _ohlc()})

    assert lifecycle["holding_date"].dt.date.tolist() == [
        date(2026, 1, 2),
        date(2026, 1, 5),
        date(2026, 1, 6),
    ]
    assert lifecycle["holding_day_index"].tolist() == [0, 1, 2]
    assert lifecycle["actual_exit_on_holding_date"].tolist() == [
        False,
        False,
        True,
    ]
    assert lifecycle["state_actionable_after_close"].tolist() == [
        True,
        True,
        False,
    ]


def test_lifecycle_excludes_dates_outside_entry_exit() -> None:
    lifecycle = expand_trade_lifecycle_dates(_trades(exit_date="2026-01-05"), {"AAA": _ohlc()})

    assert lifecycle["holding_date"].dt.date.tolist() == [
        date(2026, 1, 2),
        date(2026, 1, 5),
    ]


def test_join_daily_state_to_lifecycle_marks_missing_rows() -> None:
    lifecycle = expand_trade_lifecycle_dates(_trades(exit_date="2026-01-06"), {"AAA": _ohlc()})
    joined = join_daily_states_to_trades(lifecycle, _states(["2026-01-02", "2026-01-06"]))

    assert joined["state_join_status"].tolist() == [
        "STATE_JOINED",
        "STATE_MISSING",
        "STATE_JOINED",
    ]
    assert len(joined) == len(lifecycle)


def test_entry_state_match_summary_handles_match_mismatch_and_missing() -> None:
    trades = pd.DataFrame(
        [
            _trade("T1", signal_date="2026-01-01", state="RET_UP|VOL_MID|DD_SHALLOW|LOW_NEAR"),
            _trade("T2", signal_date="2026-01-01", state="RET_DOWN|VOL_MID|DD_SHALLOW|LOW_NEAR"),
            _trade("T3", signal_date="2026-01-01", state=None),
            _trade("T4", signal_date="2026-01-09", state="RET_UP|VOL_MID|DD_SHALLOW|LOW_NEAR"),
        ]
    )
    states = _states(
        ["2026-01-01"],
        labels=["RET_UP|VOL_MID|DD_SHALLOW|LOW_NEAR"],
    )

    summary, details = validate_entry_state_match(trades, states)

    assert summary.iloc[0]["trades_checked"] == 2
    assert summary.iloc[0]["matches"] == 1
    assert summary.iloc[0]["mismatches"] == 1
    assert summary.iloc[0]["missing_stored_state"] == 1
    assert summary.iloc[0]["missing_reconstructed_state"] == 1
    assert summary.iloc[0]["match_rate_pct"] == 50.0
    assert set(details["match_status"]) == {
        "MATCH",
        "MISMATCH",
        "MISSING_STORED_STATE",
        "MISSING_RECONSTRUCTED_STATE",
    }


def test_deterioration_flags_are_diagnostic_only_and_do_not_mutate_input() -> None:
    joined = _joined_with_states(
        [
            "RET_UP|VOL_MID|DD_SHALLOW|LOW_NEAR",
            "RET_DOWN|VOL_HIGH|DD_SHALLOW|LOW_NEAR",
            "RET_STRONG_DOWN|VOL_MID|DD_DEEP|LOW_NEAR",
        ]
    )
    original_columns = list(joined.columns)

    candidates = compute_deterioration_candidates(joined)

    assert list(joined.columns) == original_columns
    assert candidates["contains_ret_down"].tolist() == [False, True, True]
    assert candidates["entered_ret_down_after_entry"].tolist() == [False, True, True]
    assert candidates["entered_vol_high_after_entry"].tolist() == [False, True, False]
    assert candidates["state_changed_from_entry"].tolist() == [False, True, True]
    assert candidates["return_state_worse_than_entry"].tolist() == [False, True, True]
    assert candidates["diagnostic_only"].all()


def test_first_occurrence_chooses_first_actionable_date_only() -> None:
    candidates = compute_deterioration_candidates(
        _joined_with_states(
            [
                "RET_UP|VOL_MID|DD_SHALLOW|LOW_NEAR",
                "RET_FLAT|VOL_HIGH|DD_SHALLOW|LOW_NEAR",
                "RET_DOWN|VOL_MID|DD_SHALLOW|LOW_NEAR",
            ],
            exit_date="2026-01-06",
        )
    )

    first = first_deterioration_occurrences(
        candidates,
        candidate_flags=["entered_vol_high_after_entry", "contains_ret_down"],
    )

    vol = first[first["candidate_flag_name"] == "entered_vol_high_after_entry"].iloc[0]
    ret_down = first[first["candidate_flag_name"] == "contains_ret_down"].iloc[0]
    assert vol["first_occurrence_date"].date() == date(2026, 1, 5)
    assert bool(vol["actionable"]) is True
    assert pd.isna(ret_down["first_occurrence_date"])
    assert ret_down["no_occurrence_reason"] == "NO_ACTIONABLE_OCCURRENCE"


def test_next_open_feasibility_computes_pnl_and_r_when_possible() -> None:
    first = pd.DataFrame(
        [
            {
                "trade_id": "T1",
                "symbol": "AAA",
                "candidate_flag_name": "contains_ret_down",
                "first_occurrence_date": pd.Timestamp("2026-01-02"),
                "actionable": True,
            }
        ]
    )
    trades = _trades(exit_date="2026-01-06")

    feasibility = compute_next_open_exit_feasibility(first, trades, {"AAA": _ohlc()})

    row = feasibility.iloc[0]
    assert row["next_session_date"].date() == date(2026, 1, 5)
    assert bool(row["hypothetical_exit_feasible"]) is True
    assert row["hypothetical_exit_price"] == 105.0
    assert row["hypothetical_exit_pnl"] == 50.0
    assert row["hypothetical_exit_r"] == 0.5
    assert row["delta_pnl"] == -50.0
    assert row["delta_r"] == -0.5


def test_next_open_feasibility_marks_too_late_and_missing_open() -> None:
    first = pd.DataFrame(
        [
            {
                "trade_id": "T1",
                "symbol": "AAA",
                "candidate_flag_name": "contains_ret_down",
                "first_occurrence_date": pd.Timestamp("2026-01-02"),
                "actionable": True,
            },
            {
                "trade_id": "T2",
                "symbol": "BBB",
                "candidate_flag_name": "contains_ret_down",
                "first_occurrence_date": pd.Timestamp("2026-01-06"),
                "actionable": True,
            },
        ]
    )
    trades = pd.concat(
        [
            _trades(trade_id="T1", exit_date="2026-01-05"),
            _trades(trade_id="T2", symbol="BBB", exit_date="2026-01-09"),
        ],
        ignore_index=True,
    )

    feasibility = compute_next_open_exit_feasibility(first, trades, {"AAA": _ohlc(), "BBB": _ohlc("BBB")})

    reasons = feasibility.set_index("trade_id")["infeasible_reason"].to_dict()
    assert reasons["T1"] == "ACTUAL_EXIT_BEFORE_OR_ON_NEXT_OPEN"
    assert reasons["T2"] == "NEXT_OPEN_MISSING"


def test_hypothetical_pnl_r_only_when_required_fields_exist() -> None:
    first = pd.DataFrame(
        [
            {
                "trade_id": "T1",
                "symbol": "AAA",
                "candidate_flag_name": "contains_ret_down",
                "first_occurrence_date": pd.Timestamp("2026-01-02"),
                "actionable": True,
            }
        ]
    )
    trades = _trades(exit_date="2026-01-06").drop(columns=["quantity"])

    feasibility = compute_next_open_exit_feasibility(first, trades, {"AAA": _ohlc()})

    assert pd.isna(feasibility.iloc[0]["hypothetical_exit_pnl"])
    assert pd.isna(feasibility.iloc[0]["hypothetical_exit_r"])


def test_coverage_summary_counts_rows_and_trades() -> None:
    trades = _trades(exit_date="2026-01-06")
    lifecycle = expand_trade_lifecycle_dates(trades, {"AAA": _ohlc()})
    joined = join_daily_states_to_trades(lifecycle, _states(["2026-01-02", "2026-01-06"]))
    validation = pd.DataFrame([{"trades_checked": 1, "match_rate_pct": 100.0}])
    first = pd.DataFrame(
        [
            {
                "candidate_flag_name": "contains_ret_down",
                "actionable": True,
            }
        ]
    )
    feasibility = pd.DataFrame(
        [
            {
                "candidate_flag_name": "contains_ret_down",
                "hypothetical_exit_feasible": True,
                "infeasible_reason": "",
            },
            {
                "candidate_flag_name": "entered_vol_high_after_entry",
                "hypothetical_exit_feasible": False,
                "infeasible_reason": "NEXT_OPEN_MISSING",
            },
        ]
    )

    summary = summarize_reconstruction_coverage(
        trades,
        lifecycle,
        joined,
        validation,
        first,
        feasibility,
    )

    row = summary.iloc[0]
    assert row["total_trades_loaded"] == 1
    assert row["trades_with_lifecycle_expanded"] == 1
    assert row["lifecycle_rows"] == 3
    assert row["rows_with_state_joined"] == 2
    assert row["rows_missing_state"] == 1
    assert row["state_join_coverage_pct"] == 66.666667
    assert row["entry_state_trades_checked"] == 1
    assert row["entry_state_match_rate_pct"] == 100.0
    assert row["missing_next_open_count"] == 1
    assert row["same_day_exit_blocked_count"] == 1


def test_ohlc_source_layer_uses_csv_dir(tmp_path) -> None:
    csv_path = tmp_path / "AAA.csv"
    _ohlc().to_csv(csv_path, index=False)

    loaded = load_ohlc_for_reconstruction(
        _trades(),
        ohlc_source="csv",
        ohlc_csv_dir=tmp_path,
    )

    assert list(loaded) == ["AAA"]
    assert list(loaded["AAA"].columns) == [
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]
    assert loaded["AAA"]["date"].is_monotonic_increasing


def test_ohlc_source_layer_uses_mocked_db_loader() -> None:
    loader = FakeDailyLoader({"AAA": _ohlc_unsorted_with_duplicate()})

    loaded = load_ohlc_for_reconstruction(
        _trades(),
        ohlc_source="db",
        ohlc_loader=loader,
        lookback_buffer_days=10,
    )

    assert loader.calls == [
        (["AAA"], date(2025, 12, 22), date(2026, 1, 6))
    ]
    assert loaded["AAA"]["date"].dt.date.tolist() == [
        date(2026, 1, 2),
        date(2026, 1, 5),
        date(2026, 1, 6),
    ]
    assert loaded["AAA"].iloc[-1]["close"] == 110.0


def test_missing_ohlc_source_gives_clear_error() -> None:
    try:
        load_ohlc_for_reconstruction(_trades(), ohlc_source="csv")
    except ValueError as error:
        assert "ohlc_csv_dir is required" in str(error)
    else:  # pragma: no cover - assertion guard
        raise AssertionError("expected missing CSV source error")

    try:
        load_ohlc_for_reconstruction(_trades(), ohlc_source="db")
    except ValueError as error:
        assert "ohlc_loader is required" in str(error)
    else:  # pragma: no cover - assertion guard
        raise AssertionError("expected missing DB loader error")


def test_loader_missing_symbol_fails_clearly() -> None:
    loader = FakeDailyLoader({})

    try:
        load_ohlc_from_daily_loader(
            loader,
            ["AAA"],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 6),
        )
    except FileNotFoundError as error:
        assert "missing OHLC data from loader for symbols: AAA" in str(error)
    else:  # pragma: no cover - assertion guard
        raise AssertionError("expected missing loader symbol error")


def test_infer_ohlc_load_window_uses_signal_or_entry_start_with_buffer() -> None:
    trades = pd.DataFrame(
        [
            _trade(signal_date="2026-01-02", entry_date="2026-01-05"),
            _trade("T2", signal_date=None, entry_date="2026-01-04"),
        ]
    )

    assert infer_ohlc_load_window(trades, lookback_buffer_days=7) == (
        date(2025, 12, 26),
        date(2026, 1, 6),
    )


def test_cli_wires_db_source_without_strategy_backtest(monkeypatch, tmp_path, capsys) -> None:
    from veridian_quant.v2 import run_s2_state_reconstruction_prototype as cli

    observed: dict[str, object] = {}

    class FakeResult:
        output_dir = tmp_path / "out"
        outputs = {"metadata": tmp_path / "out" / "metadata.json"}
        metadata = {"caveat": "Read-only diagnostics only"}

    class FakeLoader:
        pass

    def fake_build_ohlc_loader(ohlc_source: str, lookback_buffer_days: int) -> FakeLoader:
        observed["build_source"] = ohlc_source
        observed["build_buffer"] = lookback_buffer_days
        return FakeLoader()

    def fake_run(**kwargs: object) -> FakeResult:
        observed.update(kwargs)
        return FakeResult()

    monkeypatch.setattr(cli, "_build_ohlc_loader", fake_build_ohlc_loader)
    monkeypatch.setattr(cli, "run_s2_state_reconstruction_prototype", fake_run)

    exit_code = cli.main(
        [
            "--ohlc-source",
            "db",
            "--lookback-buffer-days",
            "42",
            "--report-dir",
            "reports/s2",
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )

    assert exit_code == 0
    assert observed["build_source"] == "db"
    assert observed["build_buffer"] == 42
    assert observed["ohlc_source"] == "db"
    assert observed["ohlc_csv_dir"] is None
    assert observed["report_dir"] == Path("reports/s2")
    assert observed["output_dir"] == tmp_path / "out"
    assert observed["lookback_buffer_days"] == 42
    assert "Read-only diagnostics only" in capsys.readouterr().out


def _trade(
    trade_id: str = "T1",
    symbol: str = "AAA",
    signal_date: str = "2026-01-01",
    entry_date: str = "2026-01-02",
    exit_date: str = "2026-01-06",
    state: str | None = "RET_UP|VOL_MID|DD_SHALLOW|LOW_NEAR",
) -> dict[str, object]:
    return {
        "trade_id": trade_id,
        "symbol": symbol,
        "signal_date": pd.Timestamp(signal_date),
        "entry_date": pd.Timestamp(entry_date),
        "exit_date": pd.Timestamp(exit_date),
        "exit_reason": "target_hit",
        "entry_price": 100.0,
        "exit_price": 110.0,
        "quantity": 10.0,
        "initial_risk_amount": 100.0,
        "net_pnl": 100.0,
        "r_multiple": 1.0,
        "stored_entry_state_label": state,
    }


def _trades(
    trade_id: str = "T1",
    symbol: str = "AAA",
    exit_date: str = "2026-01-06",
) -> pd.DataFrame:
    return pd.DataFrame([_trade(trade_id=trade_id, symbol=symbol, exit_date=exit_date)])


def _ohlc(symbol: str = "AAA") -> pd.DataFrame:
    dates = ["2026-01-02", "2026-01-05", "2026-01-06"]
    if symbol == "BBB":
        dates = ["2026-01-02", "2026-01-05", "2026-01-06"]
    return pd.DataFrame(
        {
            "date": pd.to_datetime(dates),
            "open": [100.0, 105.0, 111.0],
            "high": [102.0, 108.0, 112.0],
            "low": [99.0, 104.0, 109.0],
            "close": [101.0, 107.0, 110.0],
            "volume": [1000, 1000, 1000],
        }
    )


def _ohlc_unsorted_with_duplicate() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2026-01-06", "2026-01-02", "2026-01-05", "2026-01-06"]
            ),
            "open": [110.0, 100.0, 105.0, 111.0],
            "high": [111.0, 102.0, 108.0, 112.0],
            "low": [108.0, 99.0, 104.0, 109.0],
            "close": [109.0, 101.0, 107.0, 110.0],
            "volume": [900, 1000, 1000, 1000],
        }
    )


def _states(
    dates: list[str],
    labels: list[str] | None = None,
) -> pd.DataFrame:
    labels = labels or ["RET_UP|VOL_MID|DD_SHALLOW|LOW_NEAR" for _ in dates]
    rows = []
    for state_date, label in zip(dates, labels, strict=True):
        parsed = parse_s2_state_label(label)
        rows.append(
            {
                "symbol": "AAA",
                "date": pd.Timestamp(state_date),
                "state_label": label,
                **parsed,
                "state_available": True,
                "state_unavailable_reason": "",
            }
        )
    return pd.DataFrame(rows)


def _joined_with_states(
    labels: list[str],
    exit_date: str = "2026-01-06",
) -> pd.DataFrame:
    lifecycle = expand_trade_lifecycle_dates(_trades(exit_date=exit_date), {"AAA": _ohlc()})
    states = _states(
        [value.strftime("%Y-%m-%d") for value in lifecycle["holding_date"]],
        labels=labels,
    )
    return join_daily_states_to_trades(lifecycle, states)


class FakeDailyLoader:
    def __init__(self, frames: dict[str, pd.DataFrame]) -> None:
        self.frames = frames
        self.calls: list[tuple[list[str], date, date]] = []

    def load_symbols(
        self,
        symbols: list[str],
        start_date: date,
        end_date: date,
    ) -> dict[str, pd.DataFrame]:
        self.calls.append((symbols, start_date, end_date))
        return {symbol: self.frames[symbol] for symbol in symbols if symbol in self.frames}
