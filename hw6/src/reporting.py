from __future__ import annotations
from typing import List, Protocol, Dict, Any, Optional, Iterable
from dataclasses import dataclass, field

from src.models import Signal, Action  # your existing types


class Observer(Protocol):
    def update(self, signal: Dict[str, Any]) -> None:  # spec: dict payload
        ㅊ



@dataclass
class SignalPublisher:
    observers: List[Observer] = field(default_factory=list)

    def attach(self, observer: Observer) -> None:
        if observer not in self.observers:
            self.observers.append(observer)

    def detach(self, observer: Observer) -> None:
        if observer in self.observers:
            self.observers.remove(observer)

    def notify(self, signal: Signal | Dict[str, Any]) -> None:
        """
        Accepts your Signal NamedTuple or a plain dict; notifies all observers.
        """
        payload = self._to_dict(signal)
        for ob in list(self.observers):  # copy in case observers modify registration
            ob.update(payload)

    @staticmethod
    def _to_dict(sig: Signal | Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(sig, dict):
            return sig
        return {
            "action": sig.action.value if isinstance(sig.action, Action) else sig.action,
            "symbol": sig.symbol,
            "qty": sig.qty,
            "price": sig.price,
        }

@dataclass
class LoggerObserver:
    """
    Stores every signal received in-memory. 
    """
    logs: List[Dict[str, Any]] = field(default_factory=list)

    def update(self, signal: Dict[str, Any]) -> None:
        self.logs.append(dict(signal))  # shallow copy


@dataclass
class AlertObserver:
    """
    Triggers an alert when a signal exceeds thresholds.
    - If threshold_notional is set: alert when |qty * price| >= threshold_notional
    - If threshold_qty is set: alert when |qty| >= threshold_qty
    """
    threshold_notional: Optional[float] = None
    threshold_qty: Optional[int] = None
    alerts: List[Dict[str, Any]] = field(default_factory=list)

    def update(self, signal: Dict[str, Any]) -> None:
        qty = int(signal.get("qty", 0))
        px = float(signal.get("price", 0.0))
        notional_ok = (self.threshold_notional is not None) and (abs(qty * px) >= float(self.threshold_notional))
        qty_ok = (self.threshold_qty is not None) and (abs(qty) >= int(self.threshold_qty))
        if notional_ok or qty_ok:
            self.alerts.append(dict(signal))