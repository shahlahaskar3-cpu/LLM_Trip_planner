from unittest.mock import patch, MagicMock

import pytest
from Django_app.AI_Trip_Planner.utils.weather_info import WeatherForecastTool


@pytest.fixture
def weather_service():
    return WeatherForecastTool(api_key="dummy-key")


class TestWeatherForecastToolCurrentWeather:
    @patch("Django_app.AI_Trip_Planner.utils.weather_info.requests.get")
    def test_get_current_weather_success(self, mock_get, weather_service):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "main": {"temp": 28.5},
            "weather": [{"description": "clear sky"}],
        }
        mock_get.return_value = mock_response

        result = weather_service.get_current_weather("Kochi")

        assert result["main"]["temp"] == 28.5
        assert result["weather"][0]["description"] == "clear sky"
        mock_get.assert_called_once()

    @patch("Django_app.AI_Trip_Planner.utils.weather_info.requests.get")
    def test_get_current_weather_non_200_returns_empty_dict(self, mock_get, weather_service):
        # City not found, invalid API key, etc. - API returns non-200
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = weather_service.get_current_weather("NotARealCity123")

        assert result == {}

    @patch("Django_app.AI_Trip_Planner.utils.weather_info.requests.get")
    def test_get_current_weather_request_exception_propagates(self, mock_get, weather_service):
        mock_get.side_effect = ConnectionError("network unreachable")

        with pytest.raises(ConnectionError):
            weather_service.get_current_weather("Kochi")


class TestWeatherForecastToolForecast:
    @patch("Django_app.AI_Trip_Planner.utils.weather_info.requests.get")
    def test_get_forecast_weather_success(self, mock_get, weather_service):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "list": [
                {
                    "dt_txt": "2026-07-15 12:00:00",
                    "main": {"temp": 30.0},
                    "weather": [{"description": "light rain"}],
                },
                {
                    "dt_txt": "2026-07-16 12:00:00",
                    "main": {"temp": 29.2},
                    "weather": [{"description": "overcast clouds"}],
                },
            ]
        }
        mock_get.return_value = mock_response

        result = weather_service.get_forecast_weather("Kochi")

        assert "list" in result
        assert len(result["list"]) == 2
        assert result["list"][0]["main"]["temp"] == 30.0

    @patch("Django_app.AI_Trip_Planner.utils.weather_info.requests.get")
    def test_get_forecast_weather_non_200_returns_empty_dict(self, mock_get, weather_service):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        result = weather_service.get_forecast_weather("Kochi")

        assert result == {}

    @patch("Django_app.AI_Trip_Planner.utils.weather_info.requests.get")
    def test_get_forecast_weather_request_exception_propagates(self, mock_get, weather_service):
        mock_get.side_effect = TimeoutError("request timed out")

        with pytest.raises(TimeoutError):
            weather_service.get_forecast_weather("Kochi")


class TestWeatherInfoToolWiring:
    def test_weather_tool_list_has_two_tools(self):
        # WeatherInfoTool needs no live API call to instantiate - safe for CI.
        from Django_app.AI_Trip_Planner.Tools.weather_search_tool import WeatherInfoTool

        tool = WeatherInfoTool()
        tool_names = {t.name for t in tool.weather_tool_list}

        assert tool_names == {"get_current_weather", "get_weather_forecast"}

    @patch("Django_app.AI_Trip_Planner.utils.weather_info.requests.get")
    def test_get_current_weather_tool_formats_message(self, mock_get):
        from Django_app.AI_Trip_Planner.Tools.weather_search_tool import WeatherInfoTool

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "main": {"temp": 25.0},
            "weather": [{"description": "sunny"}],
        }
        mock_get.return_value = mock_response

        tool = WeatherInfoTool()
        current_weather_tool = next(
            t for t in tool.weather_tool_list if t.name == "get_current_weather"
        )
        result = current_weather_tool.invoke({"city": "Kochi"})

        assert "Kochi" in result
        assert "25.0" in result
        assert "sunny" in result

    @patch("Django_app.AI_Trip_Planner.utils.weather_info.requests.get")
    def test_get_current_weather_tool_handles_empty_response(self, mock_get):
        from Django_app.AI_Trip_Planner.Tools.weather_search_tool import WeatherInfoTool

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        tool = WeatherInfoTool()
        current_weather_tool = next(
            t for t in tool.weather_tool_list if t.name == "get_current_weather"
        )
        result = current_weather_tool.invoke({"city": "NotARealCity123"})

        assert "Could not fetch weather" in result