# Copyright (c) 2026 Zensical and contributors

# SPDX-License-Identifier: MIT
# All contributions are certified under the DCO

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

"""Observe blog routes, views, excerpts and navigation in generated HTML.

Adapted from Zensical scripts/blog_compatibility.py at 969d9f6a8ddafb2bf854fdfb0d8683fe1a32857c.
The comparator owns this copy; no candidate implementation is imported.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag


def _url(base: str, value: str | None) -> str | None:
    """Normalize an internal link while retaining external URLs."""
    if value is None:
        return None
    absolute = urljoin(base, value)
    parsed = urlparse(absolute)
    if parsed.netloc == "example.test":
        result = parsed.path
        if parsed.query:
            result += f"?{parsed.query}"
        if parsed.fragment:
            result += f"#{parsed.fragment}"
        return result
    return absolute


def _text(element: Tag | None) -> str | None:
    """Normalize the visible text of an element."""
    if element is None:
        return None
    return " ".join(element.stripped_strings)


def _attribute(element: Tag, name: str) -> str | None:
    """Return a scalar HTML attribute."""
    value = element.get(name)
    return value if isinstance(value, str) else None


def _has_class(element: Tag, name: str) -> bool:
    """Check whether an element has a class name."""
    value = element.get("class")
    if isinstance(value, str):
        return name in value.split()
    return value is not None and name in value


def _fragment(element: Tag | None, base: str, *, normalize_urls: bool) -> str | None:
    """Normalize a selected HTML fragment for semantic comparisons."""
    if element is None:
        return None
    clone = BeautifulSoup(str(element), "lxml").find(element.name)
    if clone is None:
        raise ValueError("selected HTML fragment could not be cloned")
    for value in clone.find_all(string=True):
        value.replace_with(re.sub(r"\s+", " ", str(value)))
    if normalize_urls:
        for node in clone.select("a[href], img[src]"):
            attribute = "href" if node.name == "a" else "src"
            value = node.get(attribute)
            if isinstance(value, str):
                node[attribute] = _url(base, value) or value
    return re.sub(r">\s+<", "><", str(clone)).strip()


def _link(element: Tag, base: str) -> dict[str, Any]:
    """Describe one rendered link."""
    return {
        "title": _text(element),
        "url": _url(base, _attribute(element, "href")),
    }


def _nav_items(container: Tag, base: str) -> list[dict[str, Any]]:
    """Extract one navigation level without depending on page objects."""
    root = container.find("ul", recursive=False)
    if root is None:
        return []
    items: list[dict[str, Any]] = []
    for entry in root.find_all("li", recursive=False):
        link = entry.find("a", recursive=False)
        wrapper = entry.find("div", recursive=False)
        if link is None and wrapper is not None:
            link = wrapper.find("a", recursive=False)
        label = entry.find("label", recursive=False)
        title = _text(link or label)
        if not title:
            continue
        item: dict[str, Any] = {"title": title, "children": []}
        if link is not None:
            item["url"] = _url(base, _attribute(link, "href"))
        child = entry.find("nav", recursive=False)
        if child is not None:
            children = _nav_items(child, base)
            if children:
                item["children"] = children
        items.append(item)
    return items


def _active_ancestors(nav: Tag | None) -> list[str]:
    """Extract visible active navigation ancestors in tree order."""
    if nav is None:
        return []
    ancestors: list[str] = []
    for entry in nav.select("li.md-nav__item--active"):
        label = entry.find(["a", "label"], recursive=False)
        title = _text(label)
        if title and title not in ancestors:
            ancestors.append(title)
    return ancestors


def _posts(soup: BeautifulSoup, base: str) -> list[dict[str, Any]]:
    """Extract ordered blog-view memberships and excerpt behavior."""
    posts: list[dict[str, Any]] = []
    for article in soup.select("article.md-post--excerpt"):
        content = article.select_one(".md-post__content")
        heading = content.find(["h1", "h2"]) if content else None
        heading_link = heading.find("a") if heading else None
        time = article.find("time")
        categories = [
            _link(link, base)
            for link in article.select(".md-post__meta a.md-meta__link")
        ]
        authors = [
            image.get("alt") for image in article.select(".md-post__authors img[alt]")
        ]
        action = article.select_one(".md-post__action a[href]")
        posts.append(
            {
                "title": _text(heading),
                "url": _url(
                    base,
                    _attribute(heading_link, "href") if heading_link else None,
                ),
                "date": time.get("datetime") if time else None,
                "authors": authors,
                "categories": categories,
                "pinned": article.select_one(".md-pin") is not None,
                "continue": (
                    _url(base, _attribute(action, "href")) if action else None
                ),
                "content": _fragment(
                    content,
                    base,
                    normalize_urls=True,
                ),
            }
        )
    return posts


def _pagination(soup: BeautifulSoup, base: str) -> dict[str, Any] | None:
    """Extract page number and pager links."""
    pagination = soup.select_one(".md-pagination")
    if pagination is None:
        return None
    current = pagination.select_one(".md-pagination__current")
    return {
        "current": int(_text(current) or "1"),
        "links": [
            _link(link, base) for link in pagination.select("a.md-pagination__link")
        ],
    }


def _page(path: Path) -> dict[str, Any]:
    """Extract the stable, user-visible facts from one generated page."""
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "lxml")
    canonical = soup.select_one('link[rel="canonical"]')
    canonical_url = _attribute(canonical, "href") if canonical else None
    base = str(canonical_url or "https://example.test/")
    primary_nav = soup.select_one("nav.md-nav--primary")
    main = soup.select_one("article.md-content__inner")
    relations = {}
    for name in ("prev", "next"):
        relation = soup.select_one(f'head link[rel="{name}"]')
        relations[name] = _url(base, _attribute(relation, "href")) if relation else None
    headings = (
        [
            {
                "level": int(heading.name[1]),
                "id": None if heading.get("id") == "__skip" else heading.get("id"),
                "title": (_visible_text(heading)),
            }
            for heading in main.select("h1, h2, h3, h4, h5, h6")
        ]
        if main
        else []
    )
    links = (
        [
            _link(link, base)
            for link in main.select("a[href]")
            if not _has_class(link, "headerlink")
        ]
        if main
        else []
    )
    return {
        "document_title": _text(soup.title),
        "text": _visible_text(main) if main else None,
        "canonical": _url(base, canonical_url) if canonical_url else None,
        "relations": {} if soup.select("article.md-post--excerpt") else relations,
        "active_ancestors": _active_ancestors(primary_nav),
        "navigation": _nav_items(primary_nav, base) if primary_nav else [],
        "headings": headings,
        "links": links,
        "images": [
            {"src": _url(base, _attribute(image, "src")), "alt": image.get("alt", "")}
            for image in main.select("img[src]")
        ]
        if main
        else [],
        "posts": _posts(soup, base),
        "pagination": _pagination(soup, base),
    }


def _visible_text(heading: Tag) -> str | None:
    """Return visible content text without permalink controls or page tag badges."""
    clone = BeautifulSoup(str(heading), "lxml").find(heading.name)
    if clone is None:
        return None
    for permalink in clone.select(".headerlink, nav.md-tags"):
        permalink.decompose()
    return _text(clone)


def extract(site: Path) -> dict[str, Any]:
    """Create a deterministic manifest for a built fixture."""
    pages = {
        path.relative_to(site).as_posix(): _page(path)
        for path in sorted(site.rglob("*.html"))
        if path.name != "404.html"
    }
    root = pages.get("index.html") or next(iter(pages.values()), {})
    navigation = root.get("navigation", [])
    for page in pages.values():
        page.pop("navigation")
    outputs = [
        path.relative_to(site).as_posix()
        for path in sorted(site.rglob("*"))
        if path.is_file()
        and (
            path.suffix == ".html"
            or not path.relative_to(site).as_posix().startswith("assets/")
        )
        and path.name not in {"sitemap.xml", "sitemap.xml.gz"}
        and not (
            path.name
            in {
                "__init__.py",
                "mkdocs_theme.yml",
                "objects.inv",
                "search.json",
                "search_index.json",
            }
            or "__pycache__" in path.parts
        )
    ]
    return {
        "outputs": {name: True for name in outputs},
        "navigation": navigation,
        "pages": pages,
    }
