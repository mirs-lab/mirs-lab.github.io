---
title: Marine Litter Monitoring with Remote Sensing and AI Models
period: "2021 - ongoing"
image: /assets/images/research/marinelitter.jpg
topic_tags:
  - Marine Litter
  - Remote Sensing
  - AI Models
order: 2
layout: single
classes: research-topic
description: Detecting and tracking marine debris from multi-sensor imagery to support monitoring and response.
---

Marine plastic pollution is hard to measure at scale: surveys are expensive and sparse, while remote sensing offers repeatable coverage—if we can make detection reliable across conditions, sensors, and geographies ([Rußwurm et al., 2023](https://arxiv.org/abs/2307.02465))

# Snap Snap Track (Open Mind proposal concept, 2025)
{% include video id="9hsTvXxDU2A" provider="youtube" %}

## Research direction: multi-scale monitoring

We work on **end-to-end pipelines** that connect:
1) **in-situ / camera observations** (for ground truth and process understanding),  
2) **controlled field experiments** (to learn detectability limits and calibration), and  
3) **large-scale satellite monitoring** (to map and track litter hotspots over time).

---

## Selected papers and works

### [Large-scale Detection of Marine Debris in Coastal Areas with Sentinel-2](https://www.sciencedirect.com/science/article/pii/S2589004223024793) (iScience, 2023)
Main contributions:
- Introduces a **pixel-wise marine debris detector** (deep segmentation) for **medium-resolution Sentinel-2** imagery. 
- Shows that performance gains come largely from **data-centric design** (many hard negatives + label refinement), not just architecture tweaks. 
- Releases **model weights and training code** to support reproducible large-scale monitoring. 

### [Exploring plastic detectability on riverbanks using remote sensing](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5779542) (SSRN)
Main contributions:
- Runs a controlled **riverbank target experiment** with multiple sensors (field spectrometer, close-range multispectral, Sentinel-2, PlanetScope, EnMAP).
- Proposes a detectability workflow (incl. a new index and a simple classifier) and shows **polyester sheets can be detected** at larger sizes, while **PET bottle targets were not detected** in this setup.  
- Derives practical limits: detectability is constrained by **spatial resolution** and **plastic concentration**. 

### [Exploring Transferability of Plastic-Water Hyacinth Interaction and Detection in Rivers](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5841770) (SSRN, 2025, under review)
Main contributions:
- Studies how floating plastics become **entangled in water hyacinths**, enabling monitoring via a natural “proxy” that concentrates plastics.  
- Evaluates **transferability of object detection models** across rivers (including performance gaps between entangled vs. free-floating plastics).  
- Combines imagery-based detection with **physical sampling**, highlighting differences between what is visible from imagery and what is present in-situ.  
### [MSc thesis: double acquisition across sensors (2025)](https://edepot.wur.nl/695474)
- MSc thesis exploring **double-image / multi-sensor acquisition strategies** for monitoring drifting marine litter.  

---

## What’s next

Current focus areas:
- **Cross-scale validation:** connecting camera/field observations to satellite detections.
- **Robust generalization:** reducing false positives via better negatives, site diversity, and uncertainty-aware outputs.
- **Operational monitoring:** turning detectors into repeatable coastal and river monitoring products (with transparent evaluation and open baselines).