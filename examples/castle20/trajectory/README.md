# Recorded Key-Stage Sample

This is a sparse export of the accepted Isaac castle20 seed 0 run:
`final-v6-seed0`, documented in the [completion report](../../../reports/demo009-castle20.md)
and [native audit](../../../reports/demo009-seed0-audit.json).

- [keyframes.json](keyframes.json): 242 stage segments from 26,411 control steps;
- [waypoints.csv](waypoints.csv): commanded and measured phase endpoints;
- [events.json](events.json): all 181 motion and per-part events;
- [export-manifest.json](export-manifest.json): selection rule and SHA-256 values.

Positions are meters; quaternions are wxyz. Robot joint arrays contain seven
arm angles in radians and two finger displacements in meters, in the DOF order
recorded in the JSON. Measured values retain the original API batch dimension.

This is real executed data, not a sequence of Blender preview poses. It is not
a direct replay controller or the full lossless rollout. The full physical and
control streams remain at the source path in the export manifest.
See [the output contract](../../../docs/guides/castle-outputs.md).

To export a new run:

```bash
python3 scripts/castle.py export --run outputs/castle20-seed0 \
  --output outputs/castle20-seed0-keyframes
```
