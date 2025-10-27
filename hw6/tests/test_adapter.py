from src.data_loader import YahooFinanceAdapter, BloombergXMLAdapter

def test_adapter_demo_real_files():
    """
    Demonstrates ingestion of real external data using the Adapter Pattern.
    Reads from:
      - configs/external_data_yahoo.json
      - configs/external_data_bloomberg.xml

    Run with:  pytest -s tests/test_adapter.py
    """
    yahoo_path = "configs/external_data_yahoo.json"
    bloomberg_path = "configs/external_data_bloomberg.xml"

    yahoo = YahooFinanceAdapter(yahoo_path)
    bloomberg = BloombergXMLAdapter(bloomberg_path)

    yahoo_data = list(yahoo.get_data("AAPL"))
    bloomberg_data = list(bloomberg.get_data("MSFT"))

    print("\n=== Adapter Pattern Demonstration ===")
    print("YahooFinanceAdapter output:")
    for row in yahoo_data:
        print(f"  {row}")

    print("\nBloombergXMLAdapter output:")
    for row in bloomberg_data:
        print(f"  {row}")

    # keep pytest happy (simple checks)
    assert len(yahoo_data) >= 1
    assert len(bloomberg_data) >= 1