---
title: Large-scale Crop Type Mapping with Deep Time Series Classifiers
period: "2018 - 2021"
image: /assets/images/research/croptypemapping.png
topic_tags:
  - Crop Mapping
  - Time Series
  - Deep Learning
order: 4
layout: single
classes: research-topic
description: Scalable crop-type mapping from Sentinel time series, with models that generalize across regions and can deliver reliable in-season predictions.
---

Crop types are best recognized from **how fields change over time** (phenology), not from a single image. Our work focuses on **parcel-level crop mapping** in Europe using **Sentinel-2 time series**, with models that (1) learn directly from raw observations, (2) scale to large areas, and (3) can make **early** predictions while the season is still unfolding.

---

## Key ideas

- **Time series modeling**: use the full seasonal trajectory, not just a snapshot.
- **Scalability & benchmarking**: compare methods fairly on large, public datasets.
- **In-season decision making**: predict as early as possible, while staying accurate.

---

## Selected works and main takeaways

### AI time-series models (Transformers / Self-Attention)
**[Self-attention for raw optical satellite time series classification](https://www.sciencedirect.com/science/article/abs/pii/S0924271620301647)** (ISPRS JPRS, 2020)
- Introduces a **self-attention / transformer-style** model for crop-type mapping from **raw Sentinel-2 time series**.
- Shows that **self-attention and recurrent models** are particularly strong on raw sequences, and provides analyses of *which observations* matter most for classification.
- Establishes a practical recipe for end-to-end learning that reduces reliance on hand-crafted preprocessing.

### Recurrent Neural Networks (RNNs / LSTMs)
**[Multi-Temporal Land Cover Classification with Sequential Recurrent Encoders](https://www.mdpi.com/2220-9964/7/4/129)** (ISPRS IJGI, 2018)
- Proposes **sequential encoders** using convolutional recurrent layers (e.g., LSTM/GRU variants) to summarize an entire Sentinel-2 sequence into a single representation.
- Treats clouds/atmospheric effects as *temporal noise* and learns robustness by integrating evidence over time.
- Demonstrates how RNN-style models naturally fit crop phenology and multi-temporal land-cover mapping.

### Large-scale benchmark dataset for Europe
**[BreizhCrops: A Time Series Dataset for Crop Type Mapping](https://arxiv.org/abs/1905.11893)** (arXiv / ISPRS Archives, 2019–2020)
- Introduces **BreizhCrops**, a public **parcel-based Sentinel-2 time series benchmark** for crop-type mapping (Brittany, France).
- Provides both **TOA and BOA** time series and establishes strong baselines across several deep architectures plus Random Forest.
- Enables reproducible method comparison and supports the community with dataset + model implementations.

### Early time-series classification (predict early, not only accurately)
**[End-to-end learned early classification of time series for in-season crop type mapping](https://www.sciencedirect.com/science/article/pii/S092427162200332X)** (ISPRS JPRS, 2023)
- Introduces **ELECTS**, a generic mechanism that augments any time-series classifier with a learned **“stop / enough information”** probability.
- Optimizes a balanced objective of **accuracy + earliness**, enabling reliable crop maps **earlier in the season**.
- Reduces the amount of data that must be downloaded/processed by stopping once the model is confident—important for operational, large-scale monitoring.
