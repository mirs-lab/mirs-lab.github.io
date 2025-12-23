---
layout: single
title: People
permalink: /people/
---

{% assign leaders = site.members | where: "label", "leader" | sort: "order" %}
{% assign phds = site.members | where: "label", "PhD" | sort: "order" %}
{% assign msc_all = site.members | where: "label", "MSc" %}
{% assign current_msc = msc_all | where: "current_msc", true | sort: "end" | reverse %}
{% assign former_msc = msc_all | where_exp: "m", "m.current_msc != true" | sort: "end" | reverse %}

## Junior Research Group Leader

<div class="leader-card">
  {% for m in leaders %}
    <div class="leader-card__inner">
      {% if m.image %}
        <div class="leader-card__photo">
          <img src="{{ m.image | relative_url }}" alt="{{ m.name }}">
        </div>
      {% endif %}
      <div class="leader-card__body">
        <div class="leader-card__name">
          {% if m.website %}
            <a href="{{ m.website }}" target="_blank" rel="noopener">{{ m.name }}</a>
          {% else %}
            {{ m.name }}
          {% endif %}
        </div>
        <div class="leader-card__meta">{{ m.position }}</div>
        {% if m.former_positions %}
          <div class="leader-card__former">
            Former: {{ m.former_positions | join: "; " }}
          </div>
        {% endif %}
      </div>
    </div>
  {% endfor %}
</div>

## Doctoral Candidates (external)

<div class="phd-list">
  {% for m in phds %}
    <div class="phd-card">
      {% if m.image %}
        <div class="phd-card__photo">
          <img src="{{ m.image | relative_url }}" alt="{{ m.name }}">
        </div>
      {% endif %}
      <div class="phd-card__body">
        <div class="phd-card__name">
          {% if m.website %}
            <a href="{{ m.website }}" target="_blank" rel="noopener">{{ m.name }}</a>
          {% else %}
            {{ m.name }}
          {% endif %}
        </div>
        <div class="phd-card__meta">{{ m.position_long }}</div>
        {% if m.topic or m.phd_topic %}
          <div class="phd-card__topic">{{ m.topic | default: m.phd_topic }}</div>
        {% endif %}
      </div>
    </div>
  {% endfor %}
</div>

## Current MSc Students (Wageningen)

<ul class="member-compact-list">
  {% for m in current_msc %}
    <li class="member-compact__item">
      {% if m.image %}
        <span class="member-compact__photo">
          <img src="{{ m.image | relative_url }}" alt="{{ m.name }}">
        </span>
      {% endif %}
      <span class="member-compact__body">
        <span class="member-compact__name">
          {% if m.website %}
            <a href="{{ m.website }}" target="_blank" rel="noopener">{{ m.name }}</a>
          {% else %}
            {{ m.name }}
          {% endif %}
        </span>
        {% if m.thesis_title %}
          <span class="member-compact__thesis">
            {% if m.thesis_url %}
              <a href="{{ m.thesis_url }}" target="_blank" rel="noopener">{{ m.thesis_title }}</a>
            {% else %}
              {{ m.thesis_title }}
            {% endif %}
          </span>
        {% endif %}
      </span>
    </li>
  {% endfor %}
</ul>

## Former MSc Students

<div class="former-msc-line">
  {% for m in former_msc %}
    <span class="former-msc-name">
      {% if m.website %}
        <a href="{{ m.website }}" target="_blank" rel="noopener">{{ m.name }}</a>
      {% else %}
        {{ m.name }}
      {% endif %}
    </span>
    {% if m.end or m.award or m.thesis_url %}
      <span class="former-msc-meta">
        ({% if m.end %}{{ m.end }}{% endif %}
        {% if m.thesis_url %}{% if m.end %}, {% endif %}<a href="{{ m.thesis_url }}" target="_blank" rel="noopener">MSc Thesis</a>{% endif %}
        {% if m.award %}{% if m.end or m.thesis_url %}, {% endif %}{{ m.award }}{% endif %})
      </span>
    {% endif %}
    {% unless forloop.last %}<span class="former-msc-sep"> — </span>{% endunless %}
  {% endfor %}
</div>
