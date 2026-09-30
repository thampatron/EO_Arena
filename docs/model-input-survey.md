# How geospatial foundation models declare their inputs

Survey date: 30 September 2026. Step 1 of the EOArena interface spec: before writing templates or a model-side contract, record how existing GeoFMs and harnesses already describe inputs and outputs, and adopt their conventions where they work.

Everything here is taken from model repositories, Hugging Face model cards and framework code (PANGAEA, TorchGeo, TerraTorch). Links are given per model. Anything the sources do not settle is marked **UNVERIFIED**. The machine-readable version is [`data/model_inputs.json`](../data/model_inputs.json).

## Summary

- **Two families.** Five models take a fixed band list (Prithvi, TerraMind, AnySat, Galileo, SatlasPretrain). Four take any bands, identified by wavelength (DOFA, Panopticon, Copernicus-FM, Clay). A shared interface must serve both.
- **No two models agree on band names, units, tensor layout, time encoding or mask polarity.** Most of these differences are silent: a wrong choice produces a result, not an error.
- **Normalisation is almost always left to the caller**, and several models ship no statistics at all.
- **Harnesses diverge from the model authors.** PANGAEA's TerraMind config uses B10 where TerraTorch uses B9; PANGAEA's SatlasPretrain wrapper differs from Satlas in band order and normalisation and mixes bands with time steps for multi-image input; PANGAEA pads missing bands without warning.

## Per-model inputs

| Model | Band identity | Bands | Normalisation | Patch / size | Time | Location / GSD | Layout |
|---|---|---|---|---|---|---|---|
| Prithvi-EO-2.0 | fixed names | 6 HLS bands | caller; mean/std shipped | 16 (300M), 14 (600M); 224, interpolated | native; TL: [year, day of year] | TL: 2 values, order disputed; no GSD | B,C,T,H,W |
| TerraMind 1.0 | fixed names per modality | S2 L1C/L2A/RGB, S1 GRD/RTC, DEM, coords | caller; stats in TerraTorch | 16; 224, interpolated | single frame | optional coords as text; no GSD | dict of B,C,H,W |
| DOFA | wavelength (µm), per batch | any | caller; none shipped | 16; fixed 224 | none | none | B,C,H,W + wavelengths |
| Panopticon | wavelength (nm), per sample; SAR ids | any | caller; none shipped | 14; 224 | none | none | dict imgs + chn_ids |
| Copernicus-FM | wavelength + bandwidth (nm), per batch | any | caller; bench configs | 16, kernel adjustable | days since 1970 | lon, lat; patch area | B,C,H,W + meta (B,4) |
| AnySat | fixed per modality | 11 modalities | caller; none shipped | metres; square | native; day of year | none; GSD fixed per modality | dict of B,T,C,H,W + dates + masks |
| Galileo | fixed band slots | S1, S2, climate, DEM, landcover… | caller or helper | pixels; flexible | native ≤24; month 0–11 | lat/lon as xyz; GSD input | B,H,W,T,C per group + masks |
| SatlasPretrain | fixed order | S2, S1, Landsat, aerial | caller; divisors documented | Swin; flexible | MI: max-pool ≤8 | none | B, T·C, H, W |
| Clay v1.5 | wavelength (µm), per batch; SAR placeholders | any in metadata.yaml | caller; stats per sensor | 8; square | week/hour sin-cos | lat/lon sin-cos; GSD input | dict pixels, time, latlon, gsd, waves |
| OSM embedding (SatOSM?) | fixed RGB | 3 | ImageNet mean/std | 16; 224 | none | none | B,C,H,W |

Details and caveats per model are in `data/model_inputs.json`.

## Per-model outputs

| Model | What comes out | Dim | Intermediate layers |
|---|---|---|---|
| Prithvi-EO-2.0 | tokens with CLS | 1024 / 1280 | all blocks |
| TerraMind | tokens, no CLS; modalities merged by mean, max, concat or dict | up to 1024 | all blocks |
| DOFA | pooled vector | 768 / 1024 | via wrappers |
| Panopticon | CLS | 768 | yes |
| Copernicus-FM | pooled or CLS | 768 | yes |
| AnySat | tile, patch or dense; patch output channels-last in code (README says channels-first) | 768 (dense 1536) | no |
| Galileo | tokens per group and time step | 128–768 | no canonical pooled output |
| SatlasPretrain | feature pyramid, strides 4–32 | 128–1024 | pyramid |
| Clay | CLS + patch tokens | 1024 | final layer only |

## Problems a common interface must solve

1. **Band names.** The same Sentinel-2 blue band is `B02`, `B2`, `BLUE` or an index depending on the model.
2. **Wavelength units.** DOFA and Clay use µm; Panopticon and Copernicus-FM use nm. Nothing checks the unit.
3. **SAR has no wavelength convention.** Wavelength-conditioned models use placeholders: DOFA 3.75 (TorchGeo, PANGAEA), 5.405 (README demo) or 5.6 (other harnesses); Clay 3.5 for VV and 4.0 for VH; Copernicus-FM a fixed large value. DOFA and Copernicus-FM cannot tell VV from VH; Clay can only through its two placeholders; Panopticon encodes polarisation and orbit direction.
4. **Scale and units of pixel values.** Reflectance ×10⁴, 0–1, DN, dB or linear backscatter, rarely declared. Clay changed S1 from linear (v1) to dB (v1.5).
5. **Normalisation owner.** PANGAEA normalises with dataset statistics; model authors expect their pretraining statistics. The two give different inputs to the same weights.
6. **Silent band handling.** PANGAEA drops extra bands and pads missing ones with zeros after normalisation (so each missing band is set to its dataset mean), with no warning. A model can be scored on input it never saw.
7. **Harness drift.** PANGAEA's TerraMind config lists B10 for S2 L2A, which has no B10; TerraTorch uses B9. SatlasPretrain band order and normalisation differ between Satlas and PANGAEA, and PANGAEA's multi-image wrapper folds (B,C,T,H,W) to (B,C·T,H,W) without a permute, while Satlas expects time-major input, so bands and time steps are mixed whenever T>1.
8. **Tensor layout.** B,C,T,H,W; B,T,C,H,W; B,H,W,T,C; and time folded into channels.
9. **Time encoding.** [year, day of year]; day of year only; month 0–11; days since 1970; week and hour on a circle. Day of year is 0-based in some documents and 1-based in others.
10. **Location encoding.** (lat, lon) vs (lon, lat) disagree even within one model's own files (Prithvi: the code docstring says lat, lon; its inference script passes lon, lat). TerraMind and Copernicus-FM use (lon, lat).
11. **Masks.** AnySat uses 1 = valid; Galileo uses 1 = missing.
12. **Batch vs sample metadata.** DOFA, Copernicus-FM and Clay take one wavelength list per batch, so a batch cannot mix sensors. Panopticon takes it per sample.
13. **Resolution.** Only Galileo and Clay take GSD directly; Copernicus-FM takes the caller-supplied area of each patch; the rest assume the pretraining resolution.
14. **Outputs.** CLS vs pooled vs tokens vs pyramid; some expose no intermediate layers, so a single decoder design cannot fit all.
15. **Licences.** Panopticon weights are listed as CC-BY-4.0 in the README and MIT on Hugging Face.

## Conventions worth adopting

- **Modality-keyed dictionaries** for inputs (TerraMind, AnySat, Clay). They carry multi-sensor tasks without folding everything into channels.
- **A canonical band registry based on STAC.** Each band carries `name`, `eo:common_name`, `eo:center_wavelength` and `eo:full_width_half_max` in µm (STAC `eo` extension); SAR bands carry `sar:polarizations` and `sar:frequency_band` (STAC `sar` extension). Models map from the registry; task cards already use it.
- **Per-sample band metadata** (Panopticon), which lets one batch mix sensors.
- **Normalisation statistics shipped with the weights** (Prithvi, Clay, TorchGeo weight metadata), applied by the model adapter, not the task.
- **Missing metadata as NaN or explicit masks with one polarity** (Copernicus-FM uses NaN for unknown location and time).
- **TorchGeo weight metadata** (`model`, `publication`, `repo`, and where present `in_chans`, `bands`, `license`) as a starting point for model cards. The keys are not uniform: DOFA's entry has none of the last three.
- **Outputs as a pooled vector plus a list of intermediate feature maps with declared strides**, as PANGAEA's `output_layers` and TerraTorch necks already do.

## Next

Use this to write the task templates and the model-side contract: task data in physical units with STAC band metadata, and each model adapter declaring what it needs and converting from that.

## Sources

- Prithvi-EO-2.0: [code repo](https://github.com/NASA-IMPACT/Prithvi-EO-2.0), [model card](https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-300M-TL), [prithvi_mae.py](https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-300M-TL/blob/main/prithvi_mae.py), [TerraTorch backbone](https://github.com/IBM/terratorch/blob/main/terratorch/models/backbones/prithvi_vit.py)
- TerraMind: [TerraTorch registry](https://github.com/IBM/terratorch/blob/main/terratorch/models/backbones/terramind/model/terramind_register.py), [PANGAEA config](https://github.com/VMarsocci/pangaea-bench/blob/main/configs/encoder/terramind_large.yaml)
- DOFA: [repo](https://github.com/zhu-xlab/DOFA), [TorchGeo](https://github.com/microsoft/torchgeo/blob/main/torchgeo/models/dofa.py), [PANGAEA config](https://github.com/VMarsocci/pangaea-bench/blob/main/configs/encoder/dofa.yaml), [GeoBreeze wrapper](https://github.com/geobreeze/geobreeze/blob/main/geobreeze/models/dofa.py)
- Panopticon: [repo](https://github.com/Panopticon-FM/panopticon), [TorchGeo](https://github.com/microsoft/torchgeo/blob/main/torchgeo/models/panopticon.py)
- Copernicus-FM: [model code](https://github.com/zhu-xlab/Copernicus-FM/blob/main/Copernicus-FM/src/model_vit.py), [TorchGeo](https://github.com/microsoft/torchgeo/blob/main/torchgeo/models/copernicusfm.py)
- AnySat: [repo](https://github.com/gastruc/AnySat), [hubconf.py](https://github.com/gastruc/AnySat/blob/main/hubconf.py)
- Galileo: [repo](https://github.com/nasaharvest/galileo), [single_file_galileo.py](https://github.com/nasaharvest/galileo/blob/main/single_file_galileo.py)
- SatlasPretrain: [Normalization.md](https://github.com/allenai/satlas/blob/main/Normalization.md), [satlaspretrain_models](https://github.com/allenai/satlaspretrain_models), [PANGAEA wrapper](https://github.com/VMarsocci/pangaea-bench/blob/main/pangaea/encoders/satlasnet_encoder.py)
- Clay: [metadata.yaml](https://github.com/Clay-foundation/model/blob/main/configs/metadata.yaml), [model.py](https://github.com/Clay-foundation/model/blob/main/claymodel/model.py)
- PANGAEA: [repo](https://github.com/VMarsocci/pangaea-bench); STAC [eo](https://github.com/stac-extensions/eo) and [sar](https://github.com/stac-extensions/sar) extensions
- OSM embedding: repository `Ruizhe0723/osm` (ViT-L/16 config; an HRNet-W64 config also exists); whether this is the SatOSM model is **UNVERIFIED**.
