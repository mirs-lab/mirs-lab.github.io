---
title: Few-Shot Meta-Learning and Transfer Learning
period: "2020 - 2023"
image: /assets/images/research/few-shot-learning.gif
topic_tags:
  - Few-Shot Learning
  - Meta-Learning
  - Transfer Learning
order: 3
layout: single
classes: research-topic
description: Designing models that adapt quickly to new regions, sensors, and tasks with minimal labeled data.
---


Remote sensing models often fail when moved to a **new region**, **new sensor**, or **new task**—even if the label name stays the same (“urban”, “forest”, “water”).  
**Meta-learning** tackles this by training models to **adapt quickly**: instead of requiring thousands of new labels, the model can learn a new situation from *just a few* examples (“few-shot”).

![METEOR concept diagram (EPFL, CC BY-SA)](https://actu.epfl.ch/public/upload/fckeditorimage/6e/48/b1ac79b0.jpg)
*Image credit: EPFL / Cécilia Carron (CC BY-SA 4.0).*

---

## Why few-shot meta-learning for land cover?

Land cover looks different across the planet (architecture, vegetation seasonality, soil/backgrounds, haze, viewing geometry). Few-shot meta-learning treats this as an **adaptation problem**: learn *how to learn*, so the model can update itself rapidly for a new region or dataset.

---

## Key papers & main contributions

### [Meta-learning to address diverse Earth observation problems across resolutions](https://www.nature.com/articles/s43247-023-01146-0) (Communications Earth & Environment, 2024)
- Introduces **METEOR**, a meta-learning framework designed to **adapt across diverse Earth observation tasks**, including changes in **resolution**, **spectral bands**, and **label spaces**.
- Demonstrates strong **few-shot adaptation**: the system can be retrained for new applications using only a **handful of high-quality examples**.
- Shows a practical path toward **one foundation “meta-model”** that can be quickly specialized to new EO problems instead of training separate models from scratch.

### “Chameleon AI” explainer + visuals (EPFL news)
**EPFL news article:** [Chameleon AI program classifies objects in satellite images faster](https://actu.epfl.ch/news/chameleon-ai-program-classifies-objects-in-satelli/)
- Provides an accessible overview of the **METEOR idea** and why it matters for EO settings where labeled data is scarce.
- Highlights example downstream tasks spanning very different domains (e.g., **ocean debris**, **deforestation**, **urban structure**, change after disasters) to motivate *task-to-task transfer*.

### [Meta-Learning for Few-Shot Land Cover Classification](https://arxiv.org/abs/2004.13390) (EarthVision @ CVPRW, 2020 — Best Paper Award)
- Formulates geographic diversity as a **few-shot transfer problem**: adapt a land-cover model to a new region with only a few labeled samples.
- Evaluates **MAML-style optimization-based meta-learning** for both **classification and segmentation** and shows benefits especially when **source and target domains differ**.
- Provides early evidence that **learning-to-adapt** can outperform standard “pretrain + finetune” pipelines under real-world distribution shift.

Also available via the CVF open-access workshop proceedings:  
- [CVPRW paper (PDF/HTML)](https://openaccess.thecvf.com/content_CVPRW_2020/html/w11/Russwurm_Meta-Learning_for_Few-Shot_Land_Cover_Classification_CVPRW_2020_paper.html)


