from django.test import TestCase

# Create your tests here.
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.urls import reverse

from .forms import TripQueryForm


class TripQueryFormTests(TestCase):
    def test_valid_with_question(self):
        form = TripQueryForm(data={"question": "Plan a 3 day trip to Munnar"})
        self.assertTrue(form.is_valid())

    def test_invalid_when_question_is_empty(self):
        form = TripQueryForm(data={"question": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("question", form.errors)

    def test_invalid_when_question_missing(self):
        form = TripQueryForm(data={})
        self.assertFalse(form.is_valid())


class HomeViewGetTests(TestCase):
    def test_get_renders_empty_form(self):
        response = self.client.get(reverse("home:home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home/home.html")
        self.assertNotIn("answer", response.context)
        self.assertNotIn("error", response.context)

    def test_get_after_post_shows_result_once_then_clears(self):
        session = self.client.session
        session["display_answer"] = "Day 1: Arrive in Munnar."
        session["display_question"] = "Plan a trip to Munnar"
        session.save()

        first = self.client.get(reverse("home:home"))
        self.assertIn("answer", first.context)
        self.assertIn("Munnar", first.context["answer"])

        second = self.client.get(reverse("home:home"))
        self.assertNotIn("answer", second.context)


class HomeViewPostTests(TestCase):
    """
    GraphBuilder (the LangGraph agent) is mocked in every test here so the
    suite never calls Groq, weather, places, or currency APIs. That keeps CI
    fast, free, and independent of secrets/network access. The agent's own
    tools/graph logic should be tested separately (see AI_Trip_Planner/tests/).
    """

    @patch("home.views.GraphBuilder")
    def test_post_valid_question_stores_answer_and_redirects(self, mock_graph_builder):
        fake_message = MagicMock()
        fake_message.content = "Day 1: Arrive in Munnar and check into your hotel."
        mock_react_app = MagicMock()
        mock_react_app.invoke.return_value = {"messages": [fake_message]}
        mock_react_app.get_graph.return_value.draw_mermaid_png.return_value = b"fake-png-bytes"
        mock_graph_builder.return_value.return_value = mock_react_app

        response = self.client.post(
            reverse("home:home"), data={"question": "Plan a 3 day trip to Munnar"}
        )

        # fetch_redirect_response=False: assertRedirects would otherwise GET the
        # target itself, which pops display_answer from the session before our
        # own follow-up GET below gets to see it.
        self.assertRedirects(response, reverse("home:home"), fetch_redirect_response=False)
        mock_react_app.invoke.assert_called_once()

        follow_up = self.client.get(reverse("home:home"))
        self.assertIn("answer", follow_up.context)
        self.assertIn("Munnar", follow_up.context["answer"])

    @patch("home.views.GraphBuilder")
    def test_post_agent_exception_shows_error_not_500(self, mock_graph_builder):
        mock_graph_builder.side_effect = RuntimeError("Groq API unavailable")

        response = self.client.post(
            reverse("home:home"), data={"question": "Plan a trip to Wayanad"}
        )

        self.assertRedirects(response, reverse("home:home"), fetch_redirect_response=False)

        follow_up = self.client.get(reverse("home:home"))
        self.assertIn("error", follow_up.context)
        self.assertIn("Groq API unavailable", follow_up.context["error"])

    def test_post_empty_question_reshows_form_with_errors(self):
        response = self.client.post(reverse("home:home"), data={"question": ""})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())

    @patch("home.views.GraphBuilder")
    def test_post_does_not_leak_previous_answer_on_new_error(self, mock_graph_builder):
        # First a successful run leaves an answer in the session...
        fake_message = MagicMock()
        fake_message.content = "Old answer"
        mock_react_app = MagicMock()
        mock_react_app.invoke.return_value = {"messages": [fake_message]}
        mock_react_app.get_graph.return_value.draw_mermaid_png.return_value = b""
        mock_graph_builder.return_value.return_value = mock_react_app
        self.client.post(reverse("home:home"), data={"question": "Plan a trip"})

        # ...then a failing run should clear "display_answer", not show stale data.
        mock_graph_builder.side_effect = RuntimeError("boom")
        self.client.post(reverse("home:home"), data={"question": "Plan another trip"})

        follow_up = self.client.get(reverse("home:home"))
        self.assertIn("error", follow_up.context)
        self.assertNotIn("answer", follow_up.context)


class DownloadAnswerViewTests(TestCase):
    def test_download_without_answer_returns_404(self):
        response = self.client.get(reverse("home:download"))
        self.assertEqual(response.status_code, 404)

    def test_download_with_answer_returns_markdown_attachment(self):
        session = self.client.session
        session["download_answer"] = "# Trip Plan\n\nDay 1: Munnar"
        session.save()

        response = self.client.get(reverse("home:download"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/markdown")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("trip_plan_", response["Content-Disposition"])

    def test_download_persists_after_display_answer_is_cleared(self):
        # download_answer is intentionally separate from display_answer so the
        # download link keeps working even after a page refresh clears the
        # on-screen result. This test pins that intended behavior down.
        session = self.client.session
        session["download_answer"] = "# Trip Plan"
        session.save()

        self.client.get(reverse("home:home"))  # a GET would pop display_* keys

        response = self.client.get(reverse("home:download"))
        self.assertEqual(response.status_code, 200)