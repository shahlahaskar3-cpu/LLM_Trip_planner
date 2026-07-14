from unittest.mock import patch, MagicMock

import pytest
from Django_app.AI_Trip_Planner.utils.place_info_search import (
    GooglePlaceSearchTool,
    TavilyPlaceSearchTool,
)


class TestGooglePlaceSearchTool:
    @patch("Django_app.AI_Trip_Planner.utils.place_info_search.GooglePlacesTool")
    @patch("Django_app.AI_Trip_Planner.utils.place_info_search.GooglePlacesAPIWrapper")
    def test_google_search_attractions_returns_run_result(self, mock_wrapper_cls, mock_tool_cls):
        mock_tool_instance = MagicMock()
        mock_tool_instance.run.return_value = "Fort Kochi, Marine Drive, Chinese Fishing Nets"
        mock_tool_cls.return_value = mock_tool_instance

        google_search = GooglePlaceSearchTool(api_key="dummy-key")
        result = google_search.google_search_attractions("Kochi")

        assert result == "Fort Kochi, Marine Drive, Chinese Fishing Nets"
        mock_tool_instance.run.assert_called_once()
        call_arg = mock_tool_instance.run.call_args[0][0]
        assert "Kochi" in call_arg

    @patch("Django_app.AI_Trip_Planner.utils.place_info_search.GooglePlacesTool")
    @patch("Django_app.AI_Trip_Planner.utils.place_info_search.GooglePlacesAPIWrapper")
    def test_google_search_restaurants_returns_run_result(self, mock_wrapper_cls, mock_tool_cls):
        mock_tool_instance = MagicMock()
        mock_tool_instance.run.return_value = "Dal Roti, Ginger House"
        mock_tool_cls.return_value = mock_tool_instance

        google_search = GooglePlaceSearchTool(api_key="dummy-key")
        result = google_search.google_search_restaurants("Kochi")

        assert result == "Dal Roti, Ginger House"

    @patch("Django_app.AI_Trip_Planner.utils.place_info_search.GooglePlacesTool")
    @patch("Django_app.AI_Trip_Planner.utils.place_info_search.GooglePlacesAPIWrapper")
    def test_google_search_raises_when_places_tool_errors(self, mock_wrapper_cls, mock_tool_cls):
        mock_tool_instance = MagicMock()
        mock_tool_instance.run.side_effect = Exception("Google Places API quota exceeded")
        mock_tool_cls.return_value = mock_tool_instance

        google_search = GooglePlaceSearchTool(api_key="dummy-key")

        with pytest.raises(Exception, match="quota exceeded"):
            google_search.google_search_attractions("Kochi")


class TestTavilyPlaceSearchTool:
    @patch("Django_app.AI_Trip_Planner.utils.place_info_search.TavilySearch")
    def test_tavily_search_attractions_prefers_answer_field(self, mock_tavily_cls):
        mock_tavily_instance = MagicMock()
        mock_tavily_instance.invoke.return_value = {
            "answer": "Top attractions include Fort Kochi and Marine Drive.",
            "results": [{"content": "raw search result"}],
        }
        mock_tavily_cls.return_value = mock_tavily_instance

        tavily_search = TavilyPlaceSearchTool()
        result = tavily_search.tavily_search_attractions("Kochi")

        assert result == "Top attractions include Fort Kochi and Marine Drive."

    @patch("Django_app.AI_Trip_Planner.utils.place_info_search.TavilySearch")
    def test_tavily_search_falls_back_to_raw_result_without_answer(self, mock_tavily_cls):
        # If Tavily's response has no "answer" key, the raw dict is returned as-is.
        mock_tavily_instance = MagicMock()
        mock_tavily_instance.invoke.return_value = {"results": [{"content": "raw search result"}]}
        mock_tavily_cls.return_value = mock_tavily_instance

        tavily_search = TavilyPlaceSearchTool()
        result = tavily_search.tavily_search_restaurants("Kochi")

        assert result == {"results": [{"content": "raw search result"}]}


class TestPlaceSearchToolWiring:
    def test_place_search_tool_list_has_four_tools(self):
        from Django_app.AI_Trip_Planner.Tools.place_info_tool import PlaceSearchTool

        with patch(
            "Django_app.AI_Trip_Planner.Tools.place_info_tool.GooglePlaceSearchTool"
        ), patch("Django_app.AI_Trip_Planner.Tools.place_info_tool.TavilyPlaceSearchTool"):
            tool = PlaceSearchTool()
            tool_names = {t.name for t in tool.place_search_tool_list}

        assert tool_names == {
            "search_attractions",
            "search_restaurants",
            "search_activities",
            "search_transportation",
        }

    def test_search_attractions_falls_back_to_tavily_on_google_exception(self):
        from Django_app.AI_Trip_Planner.Tools.place_info_tool import PlaceSearchTool

        with patch(
            "Django_app.AI_Trip_Planner.Tools.place_info_tool.GooglePlaceSearchTool"
        ) as mock_google_cls, patch(
            "Django_app.AI_Trip_Planner.Tools.place_info_tool.TavilyPlaceSearchTool"
        ) as mock_tavily_cls:
            mock_google_instance = MagicMock()
            mock_google_instance.google_search_attractions.side_effect = Exception("API quota exceeded")
            mock_google_cls.return_value = mock_google_instance

            mock_tavily_instance = MagicMock()
            mock_tavily_instance.tavily_search_attractions.return_value = "Fort Kochi, Marine Drive"
            mock_tavily_cls.return_value = mock_tavily_instance

            tool = PlaceSearchTool()
            search_attractions_tool = next(
                t for t in tool.place_search_tool_list if t.name == "search_attractions"
            )
            result = search_attractions_tool.invoke({"place": "Kochi"})

        assert "Google cannot find the details" in result
        assert "Fort Kochi, Marine Drive" in result

    def test_search_restaurants_returns_google_result_when_available(self):
        from Django_app.AI_Trip_Planner.Tools.place_info_tool import PlaceSearchTool

        with patch(
            "Django_app.AI_Trip_Planner.Tools.place_info_tool.GooglePlaceSearchTool"
        ) as mock_google_cls, patch(
            "Django_app.AI_Trip_Planner.Tools.place_info_tool.TavilyPlaceSearchTool"
        ):
            mock_google_instance = MagicMock()
            mock_google_instance.google_search_restaurants.return_value = "Dal Roti, Ginger House"
            mock_google_cls.return_value = mock_google_instance

            tool = PlaceSearchTool()
            search_restaurants_tool = next(
                t for t in tool.place_search_tool_list if t.name == "search_restaurants"
            )
            result = search_restaurants_tool.invoke({"place": "Kochi"})

        assert "Dal Roti, Ginger House" in result
        assert "as suggested by google" in result

    def test_search_activities_returns_none_when_google_result_is_falsy(self):
        """
        KNOWN BUG, not a bug in this test: if google_search_activity returns a
        falsy value (empty string, empty list, etc.) without raising an
        exception, `search_activities` falls through both the `if` branch and
        the `except` block, implicitly returning None instead of falling back
        to Tavily. This test documents the current behavior - if the fallback
        is later fixed to also trigger on a falsy (non-exception) result, this
        test should be updated to assert the Tavily fallback message instead.
        """
        from Django_app.AI_Trip_Planner.Tools.place_info_tool import PlaceSearchTool

        with patch(
            "Django_app.AI_Trip_Planner.Tools.place_info_tool.GooglePlaceSearchTool"
        ) as mock_google_cls, patch(
            "Django_app.AI_Trip_Planner.Tools.place_info_tool.TavilyPlaceSearchTool"
        ) as mock_tavily_cls:
            mock_google_instance = MagicMock()
            mock_google_instance.google_search_activity.return_value = ""
            mock_google_cls.return_value = mock_google_instance

            tool = PlaceSearchTool()
            search_activities_tool = next(
                t for t in tool.place_search_tool_list if t.name == "search_activities"
            )
            result = search_activities_tool.invoke({"place": "Kochi"})

        assert result is None
        mock_tavily_cls.return_value.tavily_search_activity.assert_not_called()