class FixParser:
    def __init__(self, delimiter="|"):
        self.delimiter = delimiter

    def parse(self, raw):
        if raw is None:
            raise ValueError("empty FIX message")
        s = raw.strip()
        if not s:
            raise ValueError("empty FIX message")

        s = s.replace("\x01", self.delimiter)
        fields = s.split(self.delimiter)
        msg = {}

        for f in fields:
            f = f.strip()
            if not f:
                continue
            if "=" not in f:
                raise ValueError(f"invalid field: {f!r}")
            tag, value = f.split("=", 1)
            tag = tag.strip()
            value = value.strip()
            if not tag:
                raise ValueError(f"empty tag in field {f!r}")
            if tag in msg:
                raise ValueError(f"duplicate tag {tag!r}")
            msg[tag] = value

        self._validate(msg)
        return msg

    def _validate(self, msg):
        required = ["35", "55", "54", "38"]
        missing = [t for t in required if t not in msg]
        if missing:
            raise ValueError(
                "missing required tag(s): " + ",".join(sorted(missing))
            )

        if msg.get("40") == "2" and "44" not in msg:
            raise ValueError("missing required tag 44 (Price) for limit order")

if __name__ == "__main__":
    msg = "8=FIX.4.2|35=D|55=AAPL|54=1|38=100|40=2|44=150.25|10=128"
    print(FixParser().parse(msg))