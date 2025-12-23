---
title: Earth Embeddings and Geospatial Representation Learning
period: "2023 - ongoing"
image: /assets/images/research/satclip.gif
topic_tags:
  - Representation Learning
  - Embeddings
  - Geospatial AI
order: 1
layout: single
classes: research-topic
description: Learning general-purpose representations that capture spatial, temporal, and contextual signals across Earth observation data.
---


Learning general-purpose representations that capture **spatial**, **temporal**, and **contextual** signals across Earth.

{% include video id="Mnjrh-uc2Os" provider="youtube" %}

## Embeddings, explained simply

An **embedding** is a short list of numbers that acts like a *fingerprint* for something complex (an image, text, or a place). Similar fingerprints mean similar content—enabling fast **search**, **grouping**, and **prediction**.

---

## Key papers and main takeaways

### [Earth Embeddings: Towards AI-centric Representations of our Planet](https://eartharxiv.org/repository/view/11083/)
- Introduces **Earth embeddings** as an AI-native representation layer for geospatial data (a reusable “location representation” across tasks).
- Frames embeddings as a bridge between **databases (retrieval/indexing)** and **models (generalization/interpolation)** across **modalities** and **scales**.
- Outlines a community roadmap: standardized embedding products, evaluation, and tooling to make geospatial ML more reusable and comparable.

### [SatCLIP: Global, General-Purpose Location Embeddings with Satellite Imagery](https://arxiv.org/abs/2311.17179)
- Proposes **contrastive pretraining** that matches satellite image features with their **geographic coordinates** to learn a **location encoder**.
- Produces **general-purpose location embeddings** that transfer across many downstream tasks and improve **geographic generalization**.
- Shows that geolocalized EO imagery can act as scalable supervision for learning “place representations” without dense labels.

### [Geographic Location Encoding with Spherical Harmonics and Sinusoidal Representation Networks](https://arxiv.org/abs/2310.06743)
- Highlights why global location encoding is tricky: naïve coordinate embeddings can create **spherical artifacts** (notably near the poles).
- Introduces a principled global encoder combining **spherical harmonics** (sphere-native basis) with **sinusoidal representation networks (SIREN)**.
- Demonstrates strong performance across benchmarks, motivating INRs/location encoders as a foundation for global Earth representations.

### [Measuring the Intrinsic Dimension of Earth Representations](https://arxiv.org/abs/2511.02101)
- Studies **intrinsic dimension** as a label-free lens on “how much information” Earth representations actually use (vs. their ambient vector size).
- Finds intrinsic dimension is often **much smaller** than the embedding size and varies with **resolution** and **training modality**.
- Shows intrinsic dimension can correlate with downstream performance and reveal **spatial artifacts**, supporting diagnostics and model selection.

---

## Where we are heading

We build Earth embeddings to enable:
- **global retrieval** (“find places like this”),
- **robust transfer** across regions and sensors,
- **multimodal fusion** (EO, climate, maps, text),
- and **interpretable representations** with diagnostics that help scientific trust and use.