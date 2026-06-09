"""Lightweight progress reporting for Veridian Quant v2 backtests."""

from dataclasses import dataclass
from typing import TextIO
import sys


@dataclass(slots=True)
class ProgressReporter:
    """Small stdout-style reporter with quiet, normal, and verbose modes."""

    verbosity: str = "normal"
    stream: TextIO | None = None

    def __post_init__(self) -> None:
        if self.verbosity not in {"quiet", "normal", "verbose"}:
            raise ValueError("verbosity must be one of: quiet, normal, verbose")

    def info(self, message: str) -> None:
        """Print normal progress messages unless quiet."""

        if self.verbosity in {"normal", "verbose"}:
            self._write(message)

    def complete(self, message: str) -> None:
        """Print final completion messages for all verbosity levels."""

        self._write(message)

    def signal(self, signal: object) -> None:
        """Print a verbose signal event."""

        if self.verbosity != "verbose":
            return
        z_score = getattr(signal, "metadata", {}).get("z_score", "")
        self._write(
            f"[SIGNAL] {signal.generated_on} {signal.symbol} {z_score}"
        )

    def trade(self, position_plan: object) -> None:
        """Print a verbose accepted trade event."""

        if self.verbosity != "verbose":
            return
        self._write(
            "[TRADE] "
            f"{position_plan.entry_date} "
            f"{position_plan.symbol} "
            f"{position_plan.quantity} "
            f"{position_plan.entry_price} "
            f"{position_plan.stop_loss} "
            f"{position_plan.target_price}"
        )

    def exit(
        self,
        trade: object,
        trade_pnl: object,
        equity: object,
    ) -> None:
        """Print a verbose closed trade event."""

        if self.verbosity != "verbose":
            return
        self._write(
            "[EXIT] "
            f"{trade.exit_date} "
            f"{trade.symbol} "
            f"{_enum_value(trade.exit_reason)} "
            f"{trade_pnl.net_pnl} "
            f"{equity}"
        )

    def rejected(self, rejected_signal: object) -> None:
        """Print a verbose rejected signal event."""

        if self.verbosity != "verbose":
            return
        signal_date = getattr(rejected_signal, "signal_date", None) or "N/A"
        self._write(
            "[REJECTED] "
            f"{signal_date} "
            f"{rejected_signal.symbol} "
            f"{rejected_signal.reason}"
        )

    def _write(self, message: str) -> None:
        """Write one progress line."""

        print(message, file=self.stream or sys.stdout)


class NullProgressReporter:
    """No-op reporter used when callers do not request progress output."""

    def info(self, message: str) -> None:
        """Ignore info messages."""

    def complete(self, message: str) -> None:
        """Ignore completion messages."""

    def signal(self, signal: object) -> None:
        """Ignore signal events."""

    def trade(self, position_plan: object) -> None:
        """Ignore trade events."""

    def exit(
        self,
        trade: object,
        trade_pnl: object,
        equity: object,
    ) -> None:
        """Ignore exit events."""

    def rejected(self, rejected_signal: object) -> None:
        """Ignore rejection events."""


def _enum_value(value: object) -> object:
    """Return enum value when present, otherwise the original value."""

    return getattr(value, "value", value)
