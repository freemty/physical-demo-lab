# Getting Started: Blender to Robot Trajectories

Build a twenty-piece block castle in Blender, import its physics blueprint into
Isaac Sim, and record a Franka assembling it from loose blocks.

[中文入门](docs/guides/getting-started.zh-CN.md) ·
[Verified result](reports/demo009-castle20.md) ·
[Output format](docs/guides/castle-outputs.md)

## Choose Your Starting Point

| What you want | Start here | What it proves |
| --- | --- | --- |
| Open the finished design | [Bundled Blender example](examples/castle20/README.md) | Three design views, not robot motion |
| Generate the scene yourself | Step 2 | Blender geometry matches the shared blueprint |
| Generate a complete expert trajectory | Steps 1–5 | Actual contact-driven robot assembly and audited evidence |
| Inspect recorded key stages | [Recorded sample](examples/castle20/trajectory/README.md) | Sparse endpoints derived from one verified run |

The minimum example is fixed to the accepted twenty-piece design. It is not an
arbitrary `.blend` importer, a Lego snap-fit model, or a general task generator.
The controller reads privileged simulator state. No language-model API key or
policy training is required.

## What “Blender to Isaac” Means

One [blueprint](assets/block_castle/scene_spec.json) specifies each independent
piece, dimensions, mass, loose pose, target pose, and support dependency.
The Blender builder emits an editable `castle.blend` and a byte-identical
`scene_spec.json`. Isaac compiles that JSON into USD and PhysX bodies.

Blender bevels, lights and design layouts are visual only. Blender animation is
not used as the robot trajectory. The robot must grasp, transport, release, and
support every block through native physics. Manual Blender edits are not
automatically exported back to the blueprint.

## 1. Get the Repository and Runtime

Clone the repository. If it is private, your GitHub account needs access.

```bash
git clone https://github.com/freemty/physical-demo-lab.git
cd physical-demo-lab
export PHYSICAL_DEMO_RUNTIME="$PWD/.runtime"
```

For a remote machine, clone and run there. Copy the generated Blender file and
videos to your viewing machine as needed.

### Requirements

The full launcher supports Linux x86_64. The verified host used Ubuntu 22.04,
Python 3.12.13, Isaac Sim 6.0.1.0, PyTorch 2.11.0+cu128, an RTX 5880 Ada, and
driver 595.71.05. This is a tested configuration, not a minimum-hardware claim.

Install these prerequisites:

- [uv](https://docs.astral.sh/uv/getting-started/installation/) for the dedicated Python runtime;
- [Blender 4.5 LTS](https://www.blender.org/download/lts/4-5/) for scene generation;
- `ffmpeg` and `ffprobe` on PATH for video validation;
- a supported NVIDIA RTX GPU and driver.

NVIDIA specifies Python 3.12 and GLIBC 2.35+ for this pip installation.
Check its [installation guide](https://docs.isaacsim.omniverse.nvidia.com/6.0.1/installation/install_python.html)
and [hardware requirements](https://docs.isaacsim.omniverse.nvidia.com/6.0.1/installation/requirements.html)
before downloading. RTX cores are required; a headless run is not CPU-only.
The current launcher is not supported on macOS or Windows. Blender-only use
does not require Isaac Sim.

Reserve at least 60 GB for the runtime and cache as a practical starting budget,
plus about 2 GB per full recorded run. The retained seed 0 directory is about
1.5 GB; actual disk use varies. First startup also needs HTTPS access to
NVIDIA robot assets. The repository does not bundle those assets.

Read the [NVIDIA EULA](https://docs.omniverse.nvidia.com/platform/latest/common/NVIDIA_Omniverse_License_Agreement.html).
If you accept it:

```bash
export OMNI_KIT_ACCEPT_EULA=YES
bash scripts/setup_castle.sh
export BLENDER_BIN=blender
python3 scripts/castle.py doctor --gpu 0
```

Set `BLENDER_BIN` to the absolute executable path if Blender is not on PATH.
Likewise, `UV_BIN` can select an installed uv executable. The setup script uses
a dedicated runtime, not your training environment. If `venv/` already exists,
it does not change packages; use `doctor` to check it. A failed or incomplete
installation should be preserved and retried with a new runtime path.

`doctor` is a read-only preflight. A passing result does not prove that GPU 0 is
free, asset downloads work, or a simulation can complete. Check `nvidia-smi`
and choose an idle GPU for the following commands.

### Blender-Only Use

Skip the Isaac installation and continue with Step 2. Python 3.10+ and Blender
4.5 are enough for the scene-generation entry point. On macOS, for example:

```bash
export BLENDER_BIN=/Applications/Blender.app/Contents/MacOS/Blender
```

The Blender-only path is structurally portable; this release's actual build
and re-open checks were run on Linux.

## 2. Generate the Blender Scene

```bash
python3 scripts/castle.py build --output outputs/castle20-design --render
```

Expected files:

- `castle.blend`: twenty independently named parts in three Blender scenes;
- `scene_spec.json`: the shared physics blueprint;
- `castle-goal.png`, `castle-loose.png`, `castle-exploded.png`: design renders;
- `blender-audit.json`: checks performed after reopening the saved Blender file.

Open `castle.blend`. Select **Goal**, **Loose**, or **Exploded** in Blender's
Scene selector. No auto-run script or add-on is needed. Omit `--render` for a
faster build that still saves and reopens the Blender file.

Every build/run/export path must be new. Use a new name when retrying; do not
delete an earlier attempt merely to reuse its path.

## 3. Check the Imported Scene

Use a six-second loose-state smoke test before a full assembly:

```bash
python3 scripts/castle.py run --design outputs/castle20-design \
  --output outputs/castle20-loose-0 --mode loose --gpu 0
```

This compiles the generated JSON into native USD/PhysX bodies. It should exit
0 after checking that the unsolved scattered scene remains stable. Inspect
`scene.usda`, `result.json`, and `video.mp4`.

A successful `loose` or `goal` run is not a successful robot assembly.
The strict audit command in Step 5 intentionally rejects those modes.

## 4. Generate an Expert Trajectory

```bash
python3 scripts/castle.py run --design outputs/castle20-design \
  --output outputs/castle20-seed0 --seed 0 --gpu 0
```

The controller uses the accepted PGS solver configuration, four native physics
steps per control step, a 50,000-control-step budget and a 5,400-second wall
limit. The earlier six-seed acceptance runs took roughly 29–32 minutes each
on the recorded host, with about 440 seconds of simulated motion. Your timing
will depend on rendering, storage and other workloads.

The launcher refuses a GPU with existing compute users and monitors its own
process group. It never stops unrelated jobs. A failed or interrupted attempt
keeps its artifacts and returns nonzero.

## 5. Audit and Export Key Stages

```bash
python3 scripts/castle.py audit --run outputs/castle20-seed0 \
  --receipt outputs/castle20-seed0-audit.json
python3 scripts/castle.py export --run outputs/castle20-seed0 \
  --output outputs/castle20-seed0-keyframes
```

The strict audit requires complete twenty-part assembly, consistent native
evidence, the recorded process result, and a full video decode. It writes both
a physics receipt and an aggregate receipt. View the video as well: decoding
does not establish visual quality.

The export contains:

- `keyframes.json`: first and last recorded state of each control phase;
- `waypoints.csv`: commanded and measured endpoints for those phases;
- `events.json`: recorded motion and per-part events;
- `export-manifest.json`: source hashes, selection rule and scope.

“Expert trajectory” means the full executed controller record.
“Keyframes” are a sparse view of that record, not generated motion, an
executable replay controller, or a replacement for the full trajectory.
See [field definitions and units](docs/guides/castle-outputs.md).

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| No matching Isaac package | Python 3.12, Linux x86_64, GLIBC 2.35+, NVIDIA index access |
| No uv or Blender executable | Set `UV_BIN` / `BLENDER_BIN` to actual installed paths |
| Missing ffmpeg or ffprobe | Install the system video tools and add them to PATH |
| Asset loading stalls | Outbound HTTPS to NVIDIA asset storage and available disk space |
| Selected GPU already has compute users | Choose another idle GPU; do not terminate someone else's job |
| Output already exists | Choose a new attempt/build/export path |
| Unsupported blueprint | The quickstart deliberately accepts only the verified twenty-piece design |
| Robot stops or process exits 2 | Inspect `result.json`, `exception.json`, events, and the adjacent process/console records |
| Audit fails on a successful loose scene | Loose/goal tests are not robot assemblies |
| Missing or truncated video | Keep the run; inspect the process receipt and rerun in a new directory |

For the exact prior results, failed control candidates, and physical limits,
read the [castle completion report](reports/demo009-castle20.md).
The [quickstart validation report](reports/castle-quickstart.md) distinguishes
tested entry points from untested cold installation or second-host claims.
