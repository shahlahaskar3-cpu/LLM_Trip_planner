import os
from typing import List
import requests
from langchain.tools import tool


class CurrencyConverter:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("EXCHANGE_RATE_API_KEY")
        if not self.api_key:
            raise ValueError("EXCHANGE_RATE_API_KEY not set")
        self.base_url = f"https://v6.exchangerate-api.com/v6/{self.api_key}/latest"
        self.currency_converter_tool_list = self._setup_tools()

    def convert(self, amount: float, from_currency: str, to_currency: str) -> float:
        """Convert the amount from one currency to another"""
        url = f"{self.base_url}/{from_currency}"
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception("API call failed:", response.json())
        rates = response.json()["conversion_rates"]
        if to_currency not in rates:
            raise ValueError(f"{to_currency} not found in exchange rates.")
        return amount * rates[to_currency]

    def _setup_tools(self) -> List:
        @tool
        def convert_currency(amount: float, from_currency: str, to_currency: str) -> float:
            """Convert an amount from one currency to another using live exchange rates"""
            return self.convert(amount, from_currency, to_currency)

        return [convert_currency]