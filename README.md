# Stickman

Reusable character-motion development, separate from rose-render-test.

**Status: work in progress. Mechanics checks pass; visual quality against the supplied reference video has NOT passed.** No approved 3D model exists yet. Do not treat this checkpoint as a finished animation product.

## Current implementation
- `engine.py`: deterministic timestamp evaluator with fixed-length humanoid IK, authored walk keys, planted support feet, foot roll, weight transfer, stopping, turn and gesture.
- `rig_api.py` and `skeleton.json`: named-joint topology registry. Only humanoids are implemented.
- `characters.json`: blank-base and taller test proportions, palette and artwork paths.
- `render.py`: separate 2.5D white-outline renderer. This is a procedural approximation, not the approved character master and not an arbitrary-image auto-rigger.
- `assets/`: extracted source-sheet hands, shoes and face reference crops. These are character artwork, not default accessories.
- `character-sheets/`: approved blank white base reference and earlier v2 no-accessories sheet. The blank white base replaces the earlier blue-shirt identity. The v2 sheet is retained as earlier reference material, not the current blank model.
- `blender-prep/`: staged build instructions and read-only rig inspection script for the planned editable Blender master.

## Run locally
Requires Python 3, Pillow, NumPy and ffmpeg.

```sh
python -m pip install -r requirements.txt
python test_motion.py
python render.py --video
```

The diagnostic render is nine seconds, 1280x720, 30fps and intentionally silent. Output names retain the earlier v4 label inside the renderer; code/motion here includes the newer v5 motion study. Local render filenames are not version or quality approvals.

## Quality gates
`checks.json` records passing mechanics for both proportion configurations: fixed limb lengths, zero flat-stance ankle drift, negligible turn-support ankle drift and deterministic sampling. Dense 1ms motion checks measure positional jumps, not natural performance. `velocity-diagnostics.json` adds finite-difference knee acceleration diagnostics, not a human-motion standard.

Latest motion study reduced stride/clearance, smoothed pelvis reach constraints to avoid switching velocity corners, and made turn-foot lift start/end with zero vertical velocity. These help mechanics but do not close the visual gap.

Still unresolved: rigid/thin procedural appearance, stiff walk/stop/turn acting, hand inconsistency at rest and a shoe-image facing switch during turns. Source artwork and multi-view silhouettes need a better master. Every release needs actual pixel inspection and comparison with the reference, not only numeric tests.

## Planned Blender master
Actual mesh plus skinned armature, documented named bones and IK controls, face controls and thumbs-up pose. Flat outlined cartoon renders, with front/three-quarter/side previews for appearance approval before full performance animation. Preserve any existing Blender scene and save uniquely named files. The configured ChatGPT Blender connection has not yet returned live Blender data; connection checks currently fail with a remote probe error. No `.blend` or real 3D previews are claimed here.

## Scope
Roadmap: stickman -> stickwoman -> stickanimals (quadruped) -> stickbirds (winged). Only humanoid work is implemented. Future quadruped/winged families need separate topology, gait and renderer implementations; they cannot silently reuse a biped gait.

Vehicles are scene-specific props, not character rigs. A spear or other accessory is scene-specific only, never part of the base character identity. No default accessories.

Keep the existing Michael/Kokoro narration, measured timing and automatic joining pipeline unchanged when producing finished narrated videos. Current tests are silent. Existing rose-render-test files are not modified by this project.
