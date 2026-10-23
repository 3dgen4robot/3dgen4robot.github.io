# 3dgen4robot.github.io

Project page for *3D Generation for Embodied AI and Robotic Simulation: A Survey* ([arXiv 2604.26509](https://arxiv.org/abs/2604.26509)).

## Updating the paper lists

The Collections and Datasets sections are rendered from `static/js/collections-data.js` and `static/js/datasets-data.js`. Both are generated from the paper database `data/papers.yaml` in the list repo [hitcslj/3DGen4Robot](https://github.com/hitcslj/3DGen4Robot), which also generates that repo's README tables.

1. Edit `data/papers.yaml` in a checkout of `3DGen4Robot` placed next to this repo.
2. Run `python scripts/build_all.py` here (needs `pip install pyyaml`; pass `--db PATH` if the list repo is elsewhere). It rewrites both data files and bumps the cache-busting version in `index.html`.
