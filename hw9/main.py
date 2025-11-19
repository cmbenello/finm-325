from fix_parser import FixParser
from order import Order, OrderState
from risk_engine import RiskEngine
from logger import Logger

def process_message(raw, fix, risk, log):
    msg = fix.parse(raw)
    order = Order(msg["55"], int(msg["38"]), msg["54"])
    log.log("OrderCreated", msg)

    try:
        risk.check(order)
        order.transition(OrderState.ACKED)

        risk.update_position(order)
        order.transition(OrderState.FILLED)
        log.log("OrderFilled", {"symbol": order.symbol, "qty": order.qty})

    except ValueError as e:
        order.transition(OrderState.REJECTED)
        log.log("OrderRejected", {"reason": str(e)})

if __name__ == "__main__":
    fix = FixParser()
    risk = RiskEngine()
    log = Logger()

    msgs = [
        "8=FIX.4.2|35=D|55=AAPL|54=1|38=500|40=2|44=150|10=128",
        "8=FIX.4.2|35=D|55=MSFT|54=2|38=3000|40=1|10=128",
    ]

    for m in msgs:
        process_message(m, fix, risk, log)

    log.save()
