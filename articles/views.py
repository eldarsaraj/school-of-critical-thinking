from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render
from .data import ARTICLES


def index(request):
    paginator = Paginator(ARTICLES, 10)  # 10 articles per page
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    return render(request, "articles/index.html", {"page_obj": page_obj})


def detail(request, slug):
    article = next((a for a in ARTICLES if a["slug"] == slug), None)
    if article is None:
        raise Http404("Article not found")

    return render(request, "articles/detail.html", {"article": article})
