# Footprint extraction brief (for each worker)

Goal: for every dataset in your work list, find WHERE its samples actually are, as lon/lat points, and write
data/footprints/<id>.json via `write_footprint` in scripts/footprints/common.py. The map will draw these points.

Work list: scripts/footprints/_worklist_N.json (id, name, sources, geography, size, licence, footprint as the paper states it).
Repo root: /home/claude/eo_arena. Run scripts from there: `python3 scripts/footprints/<id>.py`.

For each dataset, in this order, stop at the first that works:
1. A public index of sample locations that is small: metadata CSV/JSON/GeoJSON/parquet in the dataset's GitHub repo,
   Hugging Face repo tree (https://huggingface.co/datasets/<org>/<name>/tree/main, raw files at
   https://huggingface.co/datasets/<org>/<name>/resolve/main/<path>), Zenodo record files (https://zenodo.org/api/records/<id>),
   source.coop, a STAC catalog (Planetary Computer, Radiant MLHub archives on source.coop/radiantearth), TorchGeo's dataset
   module (it often lists tile names or URLs), or the paper's supplement. Coordinates encoded in filenames or tile ids
   (MGRS/UTM tile, lat/lon in the name) count: decode them.
2. Reading only the headers of a subsample of GeoTIFFs with rasterio over HTTP (`rasterio.open("/vsicurl/https://...")` or a
   signed URL), taking each raster's centre; cap at 300 files and 150 MB of transfer per dataset.
3. If the data is behind registration, a login, Google Drive, Kaggle, or a one-file multi-GB archive with no index: do NOT
   download it. Write status "unavailable" with a precise note (what exists, where, and why it was not used), and if the
   paper gives a bounding box or named sites, write kind="bbox" or kind="sites" with those few points, status "partial".

Rules
- Never download imagery just to get coordinates when a metadata file exists. Keep total transfer under ~150 MB per dataset.
- Points are sample locations (chip/tile/field/site centroids). Up to 3,000 are stored; the helper subsamples. Record n_total
  = the full number of samples when known. kind: samples (one point per sample), tiles (one per tile/scene), sites (a few
  named sites), bbox (corners only).
- Every footprint needs source.url (the exact file or page the points came from) and source.method (one sentence).
- Write one script per dataset: scripts/footprints/<id>.py, idempotent, no secrets, no absolute paths outside the repo,
  importing write_footprint from common.py (sys.path.insert the scripts/footprints directory). Keep any temp downloads in
  /tmp/claude-0/fp/<id>/ and delete them when done.
- Time box: about 10 minutes of effort per dataset, then write what you have (partial/unavailable) and move on.
- Do not touch git. Do not edit any other repo file. Do not modify common.py or the work lists.
- Quality checks before writing: coordinates in degrees (not metres), lon/lat not swapped (the points must fall in the
  geography the work list states), no (0,0) artifacts. If the points fall outside the stated geography, investigate before writing.

When finished, reply with a table: id | status | kind | n_points | n_total | source.method (short) | note (short). Nothing else.
