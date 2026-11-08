# Plan: targets (web, VTuber, VRChat)

One character, several places to use it. A **target** in `character.json` (`"targets": ["web", "vtuber"]`) selects
what the build must contain, what it may cost, and which files come out. `lochara check` runs every selected target's
contract; `lochara export` writes each target's files.

| | web | vtuber | vrchat-pc | vrchat-quest |
|---|---|---|---|---|
| **For** | three.js / three-vrm pages (BentoSite) | VSeeFace, Warudo, VNyan, VTube apps, three-vrm | VRChat on PC | VRChat on Quest and phones |
| **Files** | GLB (meshopt, WebP), optionally VRM | VRM 1.0 and VRM 0.x (some apps, VSeeFace among them, still read only 0.x) | FBX + textures + a setup note | FBX + textures + a setup note |
| **Shader** | toon, done by the app (or MToon via three-vrm) | MToon (in the VRM) | lilToon or Poiyomi, set in Unity | VRChat's mobile toon shader |
| **Budget** | set per site (BentoSite: 1.5 MB) | no hard limit; ~70k triangles is a sane ceiling | rank Good ≈ 70k triangles (check VRChat's current table) | Excellent 7.5k, Good 10k, Medium 15k triangles; few materials and physics colliders |
| **Expressions** | what the app drives (BentoSite: `blink`) | VRM presets: blink (+ left, right), happy, angry, sad, relaxed, surprised, aa, ih, ou, ee, oh, look up/down/left/right; optionally the 52 ARKit shapes ("perfect sync" for iPhone tracking) | the 15 visemes (`vrc.v_sil`, `pp`, `ff`, `th`, `dd`, `kk`, `ch`, `ss`, `nn`, `rr`, `aa`, `e`, `ih`, `oh`, `ou`), blink | same as PC |
| **Bones** | what the app drives (contract) | VRM humanoid, eye bones (or look shape keys) | Unity humanoid, eye bones | same, fewer physics chains |
| **Physics** | the app's (or three-vrm springs) | VRM spring bones and colliders | PhysBones, added in Unity from the exported chain list | PhysBones within mobile limits |
| **Meta** | none | name, author, licence, permissions (VRM meta) | none in the file | none in the file |
| **First person** | none | head hidden in first person | view position | view position |

## Where each comes from
- **Expressions:** the template face (VRoid) already has blink, emotions and vowel shapes. lochara maps them to each
  target's names: VRM presets, VRChat visemes (built from the five vowels, as VRChat's own auto-viseme does), and
  later the ARKit 52 (transferred from a template that has them; not in VRoid's samples).
- **Eye tracking:** eye bones from the template.
- **Springs:** one chain list in `character.json`, written as VRM spring bones (VRM Add-on for Blender) or exported as
  a JSON list for Unity/PhysBones.
- **VRChat upload:** happens in Unity with VRChat's SDK (Creator Companion on Windows, ALCOM on a Mac). lochara stops
  at the FBX and a short setup note (shader, visemes, PhysBones, view position); the VRM can also go through the
  community "VRM Converter for VRChat".

## Order
1. **web** (BentoSite) and **vtuber** (VRM 1.0 and 0.x): the VRM Add-on for Blender does both. First.
2. **vrchat-pc**: FBX export, the viseme map, a chain list.
3. **vrchat-quest**: the same at 7.5k–10k triangles (a second Finish budget, fewer materials, a merged atlas).
4. ARKit 52 shapes.
