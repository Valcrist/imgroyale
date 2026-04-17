<h1 align="center">ImgRoyale</h1>

<p align="center">
  <strong>The battle royale for images</strong>
</p>

<p align="center">
  Deduplicate perceptually identical images and keep the best version based on resolution and/or PSNR.
</p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/github/v/tag/Valcrist/imgroyale?style=flat&label=version&color=green" alt="Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-polyform--nc-orange?style=flat" alt="License"></a>
  <a href="#"><img src="https://img.shields.io/github/languages/top/Valcrist/imgroyale?style=flat" alt="Top Language"></a>
  <a href="https://peps.python.org/pep-0008/"><img src="https://img.shields.io/badge/code%20style-pep8-73e?style=flat" alt="Code Style"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/req:python-3.10%2B-c47?style=flat" alt="Python Version"></a>
  <a href="https://github.com/Valcrist/imgroyale/activity"><img src="https://img.shields.io/badge/status-active-brightgreen?style=flat" alt="Status"></a>
</p>

---

## Overview

ImgRoyale converts images to WebP, groups perceptually identical ones using a perceptual hash, and keeps only the best copy - preferring higher resolution, falling back to PSNR when sizes match.

## Install

```bash
pip install git+https://github.com/Valcrist/imgroyale.git
```

## Usage

### Deduplicate an image

```python
from imgroyale import dedupe_image

dst = dedupe_image("photo.jpg", out_dir="out", scratch_dir="scratch")
# Converts to WebP, stores at out/<hash-path>.webp, returns destination path
```

### Individual utilities

```python
from imgroyale import to_webp, perceptual_hash, get_image_size, compute_psnr, pick_best

# Convert to WebP
webp_path = to_webp("photo.jpg", out_dir="out", quality=75)

# Perceptual hash (hex string)
h = perceptual_hash("photo.webp")

# Image dimensions
w, h = get_image_size("photo.webp")

# PSNR in both directions
psnr1, psnr2 = compute_psnr("a.webp", "b.webp")

# Return the better of two images (higher res, then PSNR)
best = pick_best("a.webp", "b.webp")
```

## How it works

1. **Convert** - input image is converted to WebP in a scratch directory
2. **Hash** - a perceptual hash (`phash`) is computed; identical or near-identical images produce the same hash
3. **Store** - the hash is split into a nested directory path (e.g. `ab/cd/ef/12/rest.webp`) inside `out_dir`
4. **Compare** - if a file already exists at that path, the better image wins: higher pixel count first, PSNR as a tiebreaker
5. **Cleanup** - the scratch WebP is removed after the operation

## Functions

| Function | Description |
|---|---|
| `dedupe_image(in_file, out_dir, scratch_dir, del_scratch_dir=False)` | Full pipeline: convert to WebP, hash, store best. Removes the scratch WebP after processing; deletes `scratch_dir` if empty and `del_scratch_dir` is `True`. Returns destination path |
| `to_webp(src, out_dir=None, quality=75)` | Convert image to WebP. `out_dir` defaults to the source directory. `quality=100` produces lossless output. Returns output path |
| `perceptual_hash(img)` | Compute `phash` of an image. Normalizes to RGB before hashing for consistent results across modes. Returns hex string |
| `get_image_size(img)` | Return `(width, height)`. Accepts a file path or an open `Image` handle |
| `compute_psnr(img1, img2)` | Return `(psnr1, psnr2)` measured in both directions. Returns `(100.0, 100.0)` for identical images, `(0.0, 0.0)` on error. Accepts paths or open handles |
| `pick_best(img1, img2)` | Return the path of the better image. Prefers higher total pixel count; uses PSNR as a tiebreaker when sizes match |

## Requirements

- Python 3.10+
- `numpy`, `pillow`, `imagehash`, `scikit-image`
- [`imgroyale`](https://github.com/Valcrist/imgroyale)

