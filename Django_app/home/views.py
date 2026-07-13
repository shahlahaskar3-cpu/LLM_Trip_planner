import os
import datetime

import markdown as md_lib
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render, redirect

from AI_Trip_Planner.Agent.agentic_workflow import GraphBuilder
from AI_Trip_Planner.utils.save_to_document import save_document

from .forms import TripQueryForm

def home(request):
    if request.method == "POST":
        form = TripQueryForm(request.POST)

        if form.is_valid():
            question = form.cleaned_data["question"]
            original_cwd = os.getcwd()

            try:
                os.chdir(settings.TRIP_PLANNER_DIR)

                graph = GraphBuilder(model_provider="groq")
                react_app = graph()

                try:
                    png_graph = react_app.get_graph().draw_mermaid_png()
                    graph_path = os.path.join(settings.BASE_DIR, "my_graph.png")
                    with open(graph_path, "wb") as f:
                        f.write(png_graph)
                except Exception:
                    pass

                messages = {"messages": [question]}
                output = react_app.invoke(messages)

                if isinstance(output, dict) and "messages" in output:
                    final_output = output["messages"][-1].content
                else:
                    final_output = str(output)

                # "display_*" keys are shown once, then cleared on the next GET.
                # "download_answer" persists so the download link keeps working
                # even after the on-screen result has been cleared by a refresh.
                request.session["display_answer"] = final_output
                request.session["display_question"] = question
                request.session.pop("display_error", None)
                request.session["download_answer"] = final_output

            except Exception as e:
                request.session["display_error"] = str(e)
                request.session["display_question"] = question
                request.session.pop("display_answer", None)
            finally:
                os.chdir(original_cwd)

            return redirect("home:home")

        context = {"form": form}
        return render(request, "home/home.html", context)

    # GET request: show the form, plus the just-generated answer/error (if any),
    # then clear it so a subsequent refresh shows a blank form again.
    form = TripQueryForm()
    context = {"form": form}

    display_answer = request.session.pop("display_answer", None)
    display_error = request.session.pop("display_error", None)
    display_question = request.session.pop("display_question", None)

    if display_answer:
        context["answer"] = display_answer
        context["answer_html"] = md_lib.markdown(
            display_answer, extensions=["fenced_code", "tables", "nl2br"]
        )
        context["question"] = display_question
    elif display_error:
        context["error"] = display_error
        context["question"] = display_question

    return render(request, "home/home.html", context)


def download_answer(request):
    answer = request.session.get("download_answer")

    if not answer:
        return HttpResponse("No trip plan available to download yet.", status=404)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"trip_plan_{timestamp}.md"

    response = HttpResponse(answer, content_type="text/markdown")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response