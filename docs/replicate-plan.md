# Replicate plan: where measured seed noise is missing

Generated 2026-10-27 by `scripts/build_evidence.py`. Datasets with published comparisons but no measured seed noise (score provisional), ordered by evidence mass = models x comparisons. Suggested models are the ones that appear in most of the dataset's comparisons; re-evaluating them with >= 5 seeds under the listed protocol families would convert the dataset's score from provisional to measured.

The score of every dataset below is **provisional**: its noise σ² is plugged in from similar comparisons. Re-running the suggested models with ≥ 5 seeds (same protocol family, same metric) measures σ² directly and moves the dataset to the measured tier. Evidence mass = models × comparisons; the first rows carry the most published evidence per unit of work.

| # | Dataset | Domain | Models | Papers | Comparisons | Evidence mass | Provisional score | Protocols | Suggested models (comparisons they appear in) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | MADOS | Oceans and coasts | 51 | 4 | 14 | 714 | 0.99 | fine-tuned, frozen | croma_vitl (14), dofa_vitb (12), remoteclip (8), scalemae_vitl (8), spectralgpt (8), prithvi_v1_100m (8) |
| 2 | RESISC45 *(not in inventory)* | Terrestrial ecosystems | 27 | 4 | 9 | 243 | 0.93 | fine-tuned, frozen, zero_shot | convmae_convvitl (5), scalemae_vitl (5), satmae_vitl (5), vanilla_mae (4), dofa_vitb (3), clip_vit (3) |
| 3 | GEOID-Flood *(not in inventory)* | Inland water | 15 | 1 | 14 | 210 | 0.63 | fine-tuned, frozen | dofa_vitb (14), olmoearth_v1_base (14), dofa_vitl (14), terramind_v1b (14), terramind_v1l (14), satlas_swinb (14) |
| 4 | CropTypeMapping Ghana / South Sudan | Agriculture | 12 | 1 | 15 | 180 | 0.99 | frozen | croma_vitl (15), dofa_vitb (15), gfm_swinb (15), prithvi_v1_100m (15), remoteclip (15), satlas_s2_swinb_mi_ms (15) |
| 5 | Nandi *(not in inventory)* | Agriculture | 29 | 1 | 5 | 145 | 0.98 | fine-tuned, frozen | anysat (5), olmoearth_v12_tiny (5), olmoearth_v12_small (5), olmoearth_v12_nano (5), olmoearth_v12_base (5), olmoearth_v1_tiny (5) |
| 6 | AWF *(not in inventory)* | Terrestrial ecosystems | 29 | 1 | 5 | 145 | 0.99 | fine-tuned, frozen | anysat (5), olmoearth_v12_tiny (5), olmoearth_v12_small (5), olmoearth_v12_nano (5), olmoearth_v12_base (5), olmoearth_v1_tiny (5) |
| 7 | AI4SmallFarms | Agriculture | 12 | 1 | 9 | 108 | 0.65 | frozen | croma_vitl (9), dofa_vitb (9), gfm_swinb (9), prithvi_v1_100m (9), remoteclip (9), satlas_s2_swinb_si_ms (9) |
| 8 | Five Billion Pixels | Terrestrial ecosystems | 12 | 1 | 8 | 96 | 0.99 | frozen | croma_vitl (8), dofa_vitb (8), gfm_swinb (8), prithvi_v1_100m (8), remoteclip (8), satlas_s2_swinb_si_ms (8) |
| 9 | Borneo Canopy Height *(not in inventory)* | Terrestrial ecosystems | 14 | 1 | 6 | 84 | – | fine-tuned, frozen | croma_vitl (6), dofa_vitb (6), prithvi_v1_100m (6), galileo (6), satlas_swinb (6), remoteclip (6) |
| 10 | xBD / xView2 | Disasters | 12 | 1 | 5 | 60 | 0.79 | frozen | croma_vitl (5), dofa_vitb (5), gfm_swinb (5), prithvi_v1_100m (5), remoteclip (5), satlas_s2_swinb_si_ms (5) |
| 11 | BreizhCrops | Agriculture | 29 | 2 | 2 | 58 | 0.99 | frozen | anysat (2), galileo_nano (2), galileo_base (2), presto (2), galileo_tiny (2), croma_vitl (1) |
| 12 | SustainBench DHS tasks | Human systems | 10 | 1 | 5 | 50 | – | frozen | croma_vitl (5), dofa_vitb (5), gfm_swin_swint (5), prithvi_v1_100m (5), remoteclip (5), satlas_swint (5) |
| 13 | Canadian Cropland *(not in inventory)* | Agriculture | 9 | 1 | 5 | 45 | 0.98 | fine-tuned, frozen, kmeans_clustering | croma_vitb (5), croma_vitl (5), resnet50_baseline (5), satmae_vitb (5), satmae_vitl (5), ssl4eo_vits_dino (5) |
| 14 | GeoNRW *(not in inventory)* | Terrestrial ecosystems | 11 | 1 | 4 | 44 | 0.99 | fine-tuned, frozen | decur_bl_barlow_twins_geonrw (4), decur_bl_barlow_twins_rgb_geonrw (4), decur_bl_clip_cross_geonrw (4), decur_bl_simclr_cross_geonrw (4), decur_bl_supervised_geonrw (4), decur_bl_vicreg_geonrw (4) |
| 15 | AI4Arctic / AutoICE | Cryosphere | 14 | 1 | 3 | 42 | 0.97 | fine-tuned, frozen | croma_vitl (3), dofa_vitb (3), gfm_swinb (3), prithvi_v1_100m (3), ramen (3), remoteclip (3) |
| 16 | GLD *(not in inventory)* | Cryosphere | 14 | 1 | 3 | 42 | 0.98 | fine-tuned, frozen | croma_vitl (3), dofa_vitb (3), gfm_swinb (3), prithvi_v1_100m (3), ramen (3), remoteclip (3) |
| 17 | GLID *(not in inventory)* | Cryosphere | 14 | 1 | 3 | 42 | 0.99 | fine-tuned, frozen | croma_vitl (3), dofa_vitb (3), gfm_swinb (3), prithvi_v1_100m (3), ramen (3), remoteclip (3) |
| 18 | GSDD *(not in inventory)* | Cryosphere | 14 | 1 | 3 | 42 | 0.91 | fine-tuned, frozen | croma_vitl (3), dofa_vitb (3), gfm_swinb (3), prithvi_v1_100m (3), ramen (3), remoteclip (3) |
| 19 | Landslide4Sense | Solid Earth | 4 | 1 | 10 | 40 | 0.32 | fine-tuned | prithvi_v2_300m (10), prithvi_v2_600m (10), unet_supervised (10), unetpp_supervised (10) |
| 20 | OlmoEarth Mangrove *(not in inventory)* | Oceans and coasts | 20 | 1 | 2 | 40 | 0.55 | fine-tuned | anysat (2), copernicusfm (2), croma_vitb (2), croma_vitl (2), terramind_v1l (2), galileo_base (2) |
| 21 | Live Fuel Moisture Content *(not in inventory)* | Terrestrial ecosystems | 19 | 1 | 2 | 38 | – | fine-tuned | anysat (2), copernicusfm (2), croma_vitb (2), panopticon (2), croma_vitl (2), galileo_base (2) |
| 22 | AID *(not in inventory)* | Terrestrial ecosystems | 12 | 1 | 3 | 36 | 0.99 | frozen, zero_shot | clip_rn50 (3), clip_vit (3), remoteclip_vitb32 (3), remoteclip_rn50 (3), vitae_vitb (2), barlowtwins_resnet50 (2) |
| 23 | MLRSNet *(not in inventory)* | Terrestrial ecosystems | 12 | 1 | 3 | 36 | 0.98 | frozen, zero_shot | clip_rn50 (3), clip_vit (3), remoteclip_vitb32 (3), remoteclip_rn50 (3), vitae_vitb (2), barlowtwins_resnet50 (2) |
| 24 | OPTIMAL-31 *(not in inventory)* | Terrestrial ecosystems | 12 | 1 | 3 | 36 | 0.98 | frozen, zero_shot | clip_rn50 (3), clip_vit (3), remoteclip_vitb32 (3), remoteclip_rn50 (3), vitae_vitb (2), barlowtwins_resnet50 (2) |
| 25 | RSC11 *(not in inventory)* | Terrestrial ecosystems | 12 | 1 | 3 | 36 | 0.99 | frozen, zero_shot | clip_rn50 (3), clip_vit (3), remoteclip_vitb32 (3), remoteclip_rn50 (3), vitae_vitb (2), barlowtwins_resnet50 (2) |
| 26 | RSI-CB128 *(not in inventory)* | Terrestrial ecosystems | 12 | 1 | 3 | 36 | 0.89 | frozen, zero_shot | clip_rn50 (3), clip_vit (3), remoteclip_vitb32 (3), remoteclip_rn50 (3), vitae_vitb (2), barlowtwins_resnet50 (2) |
| 27 | RSI-CB256 *(not in inventory)* | Terrestrial ecosystems | 12 | 1 | 3 | 36 | 0.54 | frozen, zero_shot | clip_rn50 (3), clip_vit (3), remoteclip_vitb32 (3), remoteclip_rn50 (3), vitae_vitb (2), barlowtwins_resnet50 (2) |
| 28 | RSSCN7 *(not in inventory)* | Terrestrial ecosystems | 12 | 1 | 3 | 36 | 0.99 | frozen, zero_shot | clip_rn50 (3), clip_vit (3), remoteclip_vitb32 (3), remoteclip_rn50 (3), vitae_vitb (2), barlowtwins_resnet50 (2) |
| 29 | WHU-RS19 *(not in inventory)* | Terrestrial ecosystems | 12 | 1 | 3 | 36 | 0.96 | frozen, zero_shot | clip_rn50 (3), clip_vit (3), remoteclip_vitb32 (3), remoteclip_rn50 (3), vitae_vitb (2), barlowtwins_resnet50 (2) |
| 30 | WHU-earth *(not in inventory)* | Terrestrial ecosystems | 12 | 1 | 3 | 36 | 0.89 | frozen, zero_shot | clip_rn50 (3), clip_vit (3), remoteclip_vitb32 (3), remoteclip_rn50 (3), vitae_vitb (2), barlowtwins_resnet50 (2) |
| 31 | CHC canopy height change *(not in inventory)* | Terrestrial ecosystems | 9 | 1 | 4 | 36 | – | frozen | croma_vitl (4), dinov3_unspecified (4), dofa_vitb (4), prithvi_v2_600m (4), remoteclip (4), satlas_s2_swinb_mi_ms (4) |
| 32 | PatternNet *(not in inventory)* | Human systems | 12 | 1 | 3 | 36 | 0.81 | frozen, zero_shot | clip_rn50 (3), clip_vit (3), remoteclip_vitb32 (3), remoteclip_rn50 (3), vitae_vitb (2), barlowtwins_resnet50 (2) |
| 33 | NeuCo-Bench Landcover *(not in inventory)* | Agriculture | 14 | 1 | 2 | 28 | – | frozen | clay_vitb (2), dofa_vitl (2), factorized_prior_l0025 (2), factorized_prior_l01 (2), factorized_prior_l05 (2), neuco_avg_baseline (2) |
| 34 | NeuCo-Bench Biomass *(not in inventory)* | Terrestrial ecosystems | 14 | 1 | 2 | 28 | – | frozen | clay_vitb (2), dofa_vitl (2), factorized_prior_l0025 (2), factorized_prior_l01 (2), factorized_prior_l05 (2), neuco_avg_baseline (2) |
| 35 | UrbanSARFloods *(not in inventory)* | Inland water | 7 | 1 | 4 | 28 | 0.99 | fine-tuned, frozen | climax (4), convnext (4), dofa_vitb (4), prithvi_v1_100m (4), prithvi_v2_300m_tl (4), satmae_stack (4) |
| 36 | NeuCo-Bench Heatisland *(not in inventory)* | Human systems | 14 | 1 | 2 | 28 | – | frozen | clay_vitb (2), dofa_vitl (2), factorized_prior_l0025 (2), factorized_prior_l01 (2), factorized_prior_l05 (2), neuco_avg_baseline (2) |
| 37 | AGBD | Terrestrial ecosystems | 13 | 1 | 2 | 26 | – | frozen | alphaearth (2), croma_vitb (2), satlas_s2_swinb_mi_ms (2), resnet50_ssl4eo_moco (2), prithvi_v2_100m (2), terramind_v1t (2) |
| 38 | OlmoEarth Vessel Detection *(not in inventory)* | Human systems | 13 | 1 | 2 | 26 | 0.89 | fine-tuned | clay (2), olmoearth_v12_nano (2), olmoearth_v12_base (2), olmoearth_v12_tiny (2), olmoearth_v12_small (2), olmoearth_v1_tiny (2) |
| 39 | METER-ML *(not in inventory)* | Atmosphere | 6 | 1 | 4 | 24 | 0.96 | frozen | clip_vit (4), decur (4), prithvi_v1_100m (4), prithvi_v2_300m (4), terramind_v1b (4), terramind_v1l (4) |
| 40 | SpaceNet 1 *(not in inventory)* | Human systems | 12 | 2 | 2 | 24 | 0.51 | fine-tuned, frozen | anysat (1), convmae_convvitl (1), croma_vitb (1), dinov2_vitb (1), dofa_vitb (1), gassl (1) |
| 41 | DSIFN *(not in inventory)* | Human systems | 7 | 1 | 3 | 21 | 0.37 | fine-tuned | gfm_swinb_random_init (3), resnet50_imagenet (3), satmae_vitl (3), swinb_imagenet_baseline (3), seco_resnet50 (3), vitl_imagenet (3) |
| 42 | Forest Loss Driver *(not in inventory)* | Terrestrial ecosystems | 20 | 1 | 1 | 20 | 0.99 | fine-tuned | anysat (1), clay (1), copernicusfm (1), croma_vitb (1), croma_vitl (1), dinov3_sat_vitl (1) |
| 43 | GEA North Africa *(not in inventory)* | Terrestrial ecosystems | 20 | 1 | 1 | 20 | 0.98 | fine-tuned | anysat (1), clay (1), copernicusfm (1), croma_vitb (1), croma_vitl (1), dinov3_sat_vitl (1) |
| 44 | OMBRIA *(not in inventory)* | Inland water | 10 | 1 | 2 | 20 | 0.42 | fine-tuned, frozen | croma_vitl (2), dofa_vitb (2), gfm_swin_swint (2), prithvi_v1_100m (2), remoteclip (2), satlas_swint (2) |
| 45 | OlmoEarth Solar Farm *(not in inventory)* | Human systems | 20 | 1 | 1 | 20 | 0.96 | fine-tuned | anysat (1), clay (1), copernicusfm (1), croma_vitb (1), croma_vitl (1), dinov3_sat_vitl (1) |
| 46 | OlmoEarth Vessel Length *(not in inventory)* | Human systems | 17 | 1 | 1 | 17 | – | fine-tuned | anysat (1), clay (1), copernicusfm (1), croma_vitb (1), dinov3_sat_vitl (1), galileo_base (1) |
| 47 | MMEarth-Bench species *(not in inventory)* | Terrestrial ecosystems | 8 | 1 | 2 | 16 | 0.98 | fine-tuned | copernicusfm (2), dinov3_sat_vitl (2), dinov3_vitl (2), galileo_base (2), mmearth_cnn_atto (2), satlas_swinb (2) |
| 48 | OlmoEarth Vessel Type *(not in inventory)* | Human systems | 16 | 1 | 1 | 16 | 0.99 | fine-tuned | anysat (1), clay (1), copernicusfm (1), croma_vitb (1), dinov3_sat_vitl (1), galileo_base (1) |
| 49 | DIOR *(not in inventory)* | Human systems | 15 | 1 | 1 | 15 | 0.98 | fine-tuned | caco (1), cmid (1), dofa_plus_vitl (1), dofa_vitl (1), gassl (1), gfm_swinb (1) |
| 50 | NeuCo-Bench Crops *(not in inventory)* | Agriculture | 14 | 1 | 1 | 14 | – | frozen | clay_vitb (1), dofa_vitl (1), factorized_prior_l0025 (1), factorized_prior_l01 (1), factorized_prior_l05 (1), neuco_avg_baseline (1) |
| 51 | Hyperview *(not in inventory)* | Agriculture | 7 | 1 | 2 | 14 | – | frozen | anysat (2), croma_vitb (2), dinov2_vitb (2), dofa_vitb (2), panopticon (2), senpamae (2) |
| 52 | CORINE (Panopticon) *(not in inventory)* | Terrestrial ecosystems | 7 | 1 | 2 | 14 | 0.99 | frozen | anysat (2), croma_vitb (2), dinov2_vitb (2), dofa_vitb (2), panopticon (2), senpamae (2) |
| 53 | NeuCo-Bench Clouds *(not in inventory)* | Atmosphere | 14 | 1 | 1 | 14 | – | frozen | clay_vitb (1), dofa_vitl (1), factorized_prior_l0025 (1), factorized_prior_l01 (1), factorized_prior_l05 (1), neuco_avg_baseline (1) |
| 54 | CLCD *(not in inventory)* | Agriculture | 10 | 1 | 1 | 10 | 0.97 | frozen | croma_vitl (1), dofa_vitb (1), gfm_swin_swint (1), prithvi_v1_100m (1), remoteclip (1), satlas_swint (1) |
| 55 | SegMunich *(not in inventory)* | Terrestrial ecosystems | 5 | 1 | 2 | 10 | 0.74 | fine-tuned | resnet50_imagenet (2), satmae_vitl (2), seco_resnet50 (2), spectralgpt (2), vitb_imagenet22k (2) |
| 56 | RSBD *(not in inventory)* | Inland water | 10 | 1 | 1 | 10 | 0.97 | frozen | croma_vitl (1), dofa_vitb (1), gfm_swin_swint (1), prithvi_v1_100m (1), remoteclip (1), satlas_swint (1) |
| 57 | SmokePlume *(not in inventory)* | Atmosphere | 10 | 1 | 1 | 10 | 0.77 | frozen | croma_vitl (1), dofa_vitb (1), gfm_swin_swint (1), prithvi_v1_100m (1), remoteclip (1), satlas_swint (1) |
| 58 | DSE *(not in inventory)* | Human systems | 10 | 1 | 1 | 10 | 0.95 | frozen | croma_vitl (1), dofa_vitb (1), gfm_swin_swint (1), prithvi_v1_100m (1), remoteclip (1), satlas_swint (1) |
| 59 | GloSoFarID *(not in inventory)* | Human systems | 10 | 1 | 1 | 10 | 0.54 | frozen | croma_vitl (1), dofa_vitb (1), gfm_swin_swint (1), prithvi_v1_100m (1), remoteclip (1), satlas_swint (1) |
| 60 | LEVIR-CD *(not in inventory)* | Human systems | 10 | 1 | 1 | 10 | 0.83 | frozen | croma_vitl (1), dofa_vitb (1), gfm_swin_swint (1), prithvi_v1_100m (1), remoteclip (1), satlas_swint (1) |
| 61 | MineNetCD *(not in inventory)* | Human systems | 10 | 1 | 1 | 10 | 0.98 | frozen | croma_vitl (1), dofa_vitb (1), gfm_swin_swint (1), prithvi_v1_100m (1), remoteclip (1), satlas_swint (1) |
| 62 | GAZADeepDAV *(not in inventory)* | Disasters | 10 | 1 | 1 | 10 | 0.91 | frozen | croma_vitl (1), dofa_vitb (1), gfm_swin_swint (1), prithvi_v1_100m (1), remoteclip (1), satlas_swint (1) |
| 63 | Multi-Temporal Crop Classification (HLS) *(not in inventory)* | Agriculture | 4 | 1 | 2 | 8 | 0.97 | fine-tuned | prithvi_v1_100m (2), prithvi_v2_300m (2), prithvi_v2_600m (2), unet_supervised (2) |
| 64 | Dynamic World training set | Terrestrial ecosystems | 7 | 1 | 1 | 7 | 0.98 | frozen | croma_vitb (1), croma_vitl (1), satmae_vitb (1), satmae_vitl (1), ssl4eo_vits_dino (1), ssl4eo_vits_mae (1) |
| 65 | MARIDA | Oceans and coasts | 7 | 1 | 1 | 7 | 0.99 | frozen | croma_vitb (1), croma_vitl (1), satmae_vitb (1), satmae_vitl (1), ssl4eo_vits_dino (1), ssl4eo_vits_mae (1) |
| 66 | ISPRS Vaihingen *(not in inventory)* | Terrestrial ecosystems | 7 | 1 | 1 | 7 | 0.95 | fine-tuned | gfm_swinb (1), gfm_swinb_random_init (1), resnet50_imagenet (1), satmae_vitl (1), seco_resnet50 (1), swinb_imagenet_baseline (1) |
| 67 | UC Merced (classification) *(not in inventory)* | Terrestrial ecosystems | 7 | 1 | 1 | 7 | 1.00 | fine-tuned | gfm_swinb (1), gfm_swinb_random_init (1), resnet50_imagenet (1), satmae_vitl (1), seco_resnet50 (1), swinb_imagenet_baseline (1) |
| 68 | WHU Aerial Building *(not in inventory)* | Human systems | 7 | 1 | 1 | 7 | 0.96 | fine-tuned | gfm_swinb (1), gfm_swinb_random_init (1), resnet50_imagenet (1), satmae_vitl (1), seco_resnet50 (1), swinb_imagenet_baseline (1) |
| 69 | Digital Typhoon *(not in inventory)* | Atmosphere | 6 | 1 | 1 | 6 | – | frozen | anysat (1), croma_vitb (1), dinov2_vitb (1), dofa_vitb (1), panopticon (1), softcon (1) |
| 70 | TropicalCyclone *(not in inventory)* | Atmosphere | 6 | 1 | 1 | 6 | – | frozen | anysat (1), croma_vitb (1), dinov2_vitb (1), dofa_vitb (1), panopticon (1), softcon (1) |
| 71 | FLUXNET2015 | Terrestrial ecosystems | 4 | 1 | 1 | 4 | – | frozen | prithvi_v2_300m (1), prithvi_v2_300m_tl (1), prithvi_v2_600m (1), prithvi_v2_600m_tl (1) |
| 72 | HLS Burn Intensity *(not in inventory)* | Terrestrial ecosystems | 4 | 1 | 1 | 4 | 0.91 | fine-tuned | prithvi_v2_300m (1), prithvi_v2_600m (1), unet_resnet50_supervised (1), unet_supervised (1) |

## A first batch

The top 12 rows cover 2093 of 3450 evidence-mass units. Models that recur across them:

- dofa_vitb: in 9 of the 12 datasets' suggestions
- croma_vitl: in 8 of the 12 datasets' suggestions
- remoteclip: in 7 of the 12 datasets' suggestions
- prithvi_v1_100m: in 7 of the 12 datasets' suggestions
- gfm_swinb: in 4 of the 12 datasets' suggestions
- anysat: in 3 of the 12 datasets' suggestions
- satlas_s2_swinb_si_ms: in 3 of the 12 datasets' suggestions
- scalemae_vitl: in 2 of the 12 datasets' suggestions
- satlas_swinb: in 2 of the 12 datasets' suggestions
- olmoearth_v12_tiny: in 2 of the 12 datasets' suggestions

Running these models on these datasets at 5 seeds each, under the protocol family listed, is the smallest job that converts most of the provisional mass to measured. Pangaea-style frozen-decoder evaluation is the common denominator for the segmentation sets; GEO-Bench-style fine-tuning for the classification sets.
