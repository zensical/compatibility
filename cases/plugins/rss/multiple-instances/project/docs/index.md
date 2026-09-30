---
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

date: 2024-01-01
updated: 2024-01-02
image: images/overview.svg
tags: [showcase]
description: A small RSS project with several independently configured feeds.
---

# RSS compatibility showcase

This site exercises RSS and JSON Feed generation from ordinary pages and a
Material blog post. Open the generated feeds to inspect their metadata and
item order:

- <a href="feed_rss_created.xml">All pages, creation order</a>
- <a href="feed_rss_updated.xml">All pages, update order</a>
- <a href="feed_json_created.json">All pages, JSON Feed</a>
- <a href="news-created.xml">News, creation order</a>
- <a href="news-updated.xml">News, update order</a>
- <a href="blog-created.xml">Blog author feed</a>

The [release](news/release.md) has the newer creation date. The
[maintenance note](news/maintenance.md) has the newer update date, so the
two news feeds select different items.
