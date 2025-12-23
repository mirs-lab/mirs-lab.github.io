---
layout: single
title: Research
permalink: /research/
---

{% assign topics = site.research_topics | sort: "order" %}

## Research Topics

<div class="research-topic-list">
  {% for topic in topics %}
    {% include research-topic-card.html topic=topic %}
  {% endfor %}
</div>

## Publications

{% assign papers = site.publications | sort: "year" | reverse %}

<ul class="papers-list">
  {% for p in papers %}
    <li class="papers-list__item">
      <span class="papers-list__authors">
        {{ p.authors | markdownify | remove: '<p>' | remove: '</p>' }}
      </span>
      <span class="papers-list__title">
        <a href="{{ p.link }}" target="_blank" rel="noopener">{{ p.title }}</a>
      </span>
      <span class="papers-list__venue">
        — {{ p.venue }}{% if p.year %} ({{ p.year }}){% endif %}
      </span>
    </li>
  {% endfor %}
</ul>
