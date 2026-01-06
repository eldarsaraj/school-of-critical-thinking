from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from bs4 import BeautifulSoup
from django.utils.text import slugify
import markdown

from .models import Article


def index(request):
    qs = Article.objects.filter(status=Article.Status.PUBLISHED).order_by(
        "-published_at", "-created_at"
    )
    paginator = Paginator(qs, 6)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    return render(request, "articles/index.html", {"page_obj": page_obj})


def detail(request, slug):
    article = get_object_or_404(
        Article,
        slug=slug,
        status=Article.Status.PUBLISHED,
    )

    # Render Markdown to HTML
    html = markdown.markdown(article.content_markdown or "", extensions=["extra"])

    # Custom pullquote block:
    # :::pull
    # ...
    # :::
    # becomes: <aside class="pullquote">...</aside>
    html = html.replace("<p>:::pull</p>", '<aside class="pullquote">')
    html = html.replace("<p>:::</p>", "</aside>")

    soup = BeautifulSoup(html, "html.parser")

    toc_items = []

    # Extract h1 and h2 headings and add ids
    for heading in soup.find_all(["h1", "h2"]):
        text = heading.get_text(strip=True)

        # Avoid duplicating the page title if author used "# Title" in markdown
        if heading.name == "h1" and text == article.title.strip():
            continue

        slug_id = slugify(text)
        if not slug_id:
            continue

        heading["id"] = slug_id
        toc_items.append(
            {
                "id": slug_id,
                "text": text,
                "level": heading.name,  # "h1" or "h2"
            }
        )

    # ---- End mark injection (robust) ----

    # 1) Remove any existing end marks (prevents duplicates)
    for old in soup.select("span.end-mark"):
        old.decompose()

    # 2) Choose the last meaningful text block NOT inside a blockquote
    candidates = soup.find_all(["p", "li"])
    end_target = None
    for el in reversed(candidates):
        if el.get_text(strip=True) and el.find_parent("blockquote") is None:
            end_target = el
            break

    # If everything is inside a blockquote (rare), fall back to last candidate
    if end_target is None:
        for el in reversed(candidates):
            if el.get_text(strip=True):
                end_target = el
                break

    # 3) Inject the mark
    if end_target is not None:
        end_target.append(soup.new_string(" "))
        end_target.append(
            soup.new_tag("span", **{"class": "end-mark", "aria-hidden": "true"})
        )

    return render(
        request,
        "articles/detail.html",
        {
            "article": article,
            "article_html": str(soup),
            "toc_items": toc_items,
        },
    )
