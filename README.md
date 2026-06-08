# lst_models

Compact Colab-first V2 research route for intraday stock direction modeling.

Start with `AGENTS.md`. Before producing code, every agent must read
`docs/lst_models_code_style_and_route_guide.md` once that guide is copied or
created in this project.

Raw data and Drive conventions are documented in `configs/lst_models_data.yaml` and `docs/lst_models_google_drive_raw_data_guide.md`.

GPU/CUDA conventions are enforced by `AGENTS.md`: use GPU when available, fail loudly when `require_gpu=true`, and record device resolution in run manifests.
