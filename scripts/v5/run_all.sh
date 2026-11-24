#!/bin/bash
# Full v5 pipeline from a clean build: every reported number comes from one run of this script.
# Required env: EOARENA_WORKBOOK_DIR (workbook xlsx dir), WB5CSV (workbook CSV dir: results_long.csv, sources.csv),
#               V4SOURCES (v4 sources.csv, for the v4-vs-new paper split), OUT (output dir; local only, never committed).
# Two lanes run in parallel (the machine has 2 cores); each step logs to $OUT/logs/<step>.log.
set -u
HERE=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$HERE/../.." && pwd)
: "${EOARENA_WORKBOOK_DIR:?}" "${WB5CSV:?}" "${V4SOURCES:?}" "${OUT:?}"
mkdir -p "$OUT/logs" "$OUT/robustness" "$OUT/prov"
export EOARENA_OUT="$OUT/robustness" V5DIR="$OUT"
run(){ local n=$1; shift; echo "=== $n start $(date +%T)"; ( cd "$HERE" && timeout 14400 "$@" ) > "$OUT/logs/$n.log" 2>&1; echo "=== $n exit $? $(date +%T)"; }
P="python3 -I"

# 0. data layer and task-level Stage-1 outputs (both lanes depend on these)
run long        $P v5_long.py "$OUT/long.pkl"
run task_out    $P task_outputs.py "$OUT/long.pkl" "$OUT/task_outputs_local.json" "$OUT/task_outputs_public.json"

lane_a(){
  VC_UNIT=dataset run vc_dataset $P variance_components.py "$OUT/long.pkl" "$OUT/vc_dataset.json"
  VC_UNIT=task    run vc_task    $P variance_components.py "$OUT/long.pkl" "$OUT/vc_task.json"
  run varcomp_decompose $P varcomp_decompose.py "$OUT/long.pkl" "$V4SOURCES" "$OUT/varcomp_decompose.json"
  run varcomp_deeper    $P varcomp_deeper.py "$OUT/long.pkl" "$V4SOURCES" "$OUT/varcomp_deeper.json"
  run lab_effects  $P lab_effects.py "$OUT/long.pkl" "$OUT/lab_effects.json" "$OUT/w_lab.pkl"
  run heldout_lab  $P heldout_lab.py "$OUT/long.pkl" "$OUT/w_lab.pkl" "$OUT/vc_dataset.json" "$OUT/heldout_lab.json"
  run provenance   bash -c "cd '$ROOT' && $P scripts/v5/provenance.py '$ROOT' '$WB5CSV/results_long.csv' '$WB5CSV/sources.csv' '$OUT/prov/provenance_v5.json'"
  run protocol_md  $P protocol_metadata.py "$ROOT" "$WB5CSV" "$OUT/protocol_metadata.json"
}
lane_b(){
  ML_CHAINS=2 run ml_task_score $P ml_task_score.py "$OUT/long.pkl" "$OUT/task_outputs_local.json" "$OUT/ml_local.json" "$OUT/ml_public.json"
  ML_CHAINS=2 ML_WARM=600 run ml_sim $P ml_task_score.py "$OUT/long.pkl" "$OUT/task_outputs_local.json" x "$OUT/ml_public.json" --sim-only
  run latent_tau      $P latent_tau.py "$OUT/long.pkl" "$OUT/ml_local.json" "$OUT/latent_tau.json" 4
  run heldout_selfrep $P heldout_selfrep.py "$OUT/heldout_selfrep.json"
  run heldout_lopo    $P heldout_lopo_lab.py "$V4SOURCES" "$OUT/heldout_lopo_lab.json" 2
  run note_job        bash -c "cd '$ROOT' && $P scripts/build_note_analysis.py '$EOARENA_WORKBOOK_DIR' --merge-families --out '$OUT/note_analysis_families.json'"
  for s in note_stage2_partial cross_paper pretrain_strata held_fixed_tests ablation_per_input_type ablation_sensor_strata ablation_coverage_bias eq11_fit; do
    run rob_$s bash -c "cd '$ROOT/scripts/robustness' && $P $s.py"
  done
}
lane_a > "$OUT/logs/lane_a.txt" 2>&1 &
lane_b > "$OUT/logs/lane_b.txt" 2>&1 &
wait
echo ALLDONE
