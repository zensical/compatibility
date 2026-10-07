---
title: Hello {{ customer.name }}
---
# Hello {{ customer.name }}

<p data-compat-probe="CONTEXT">{{ site_name }} / {{ site_author }} / {{ customer.name }} / {{ extra.customer.name }}</p>
<p data-compat-probe="MISSING">{{ missing }}</p>
<p data-compat-probe="LOOP">{% for item in items %}{{ item | upper }}{% if not loop.last %}|{% endif %}{% endfor %}</p>

```text
{{ customer.name }}
```
