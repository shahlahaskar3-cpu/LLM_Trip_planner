from unittest.mock import patch, MagicMock

import pytest
from Django_app.AI_Trip_Planner.utils.corrency_converter import CurrencyConverter


@pytest.fixture
def converter():
    return CurrencyConverter(api_key="dummy-key")


class TestCurrencyConverter:
    @patch("Django_app.AI_Trip_Planner.utils.corrency_converter.requests.get")
    def test_convert_success(self, mock_get, converter):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"conversion_rates": {"INR": 83.0, "EUR": 0.92}}
        mock_get.return_value = mock_response

        result = converter.convert(10, "USD", "INR")

        assert result == 830.0
        mock_get.assert_called_once()

    @patch("Django_app.AI_Trip_Planner.utils.corrency_converter.requests.get")
    def test_convert_unknown_target_currency_raises(self, mock_get, converter):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"conversion_rates": {"INR": 83.0}}
        mock_get.return_value = mock_response

        with pytest.raises(ValueError, match="XXX not found"):
            converter.convert(10, "USD", "XXX")

    @patch("Django_app.AI_Trip_Planner.utils.corrency_converter.requests.get")
    def test_convert_api_failure_raises(self, mock_get, converter):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"error": "invalid-key"}
        mock_get.return_value = mock_response

        with pytest.raises(Exception):
            converter.convert(10, "USD", "INR")