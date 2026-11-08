# Plan: robot maid v2 (BentoSite)

v1 (`examples/robot-maid`) is a restyled stock body. v2 is **Kevin's own design**, built with the generated route
(`generated-character.md`), and replaces v1 in BentoSite's prologue. It is also lochara's first real test of that
route, so it is built in the open as `examples/robot-maid-v2`.

## What the site needs (fixed)
From BentoSite's prologue (`src/components/Prologue/engine/robot.js`, the script in `prototypes/crt-site/PROLOGUE.md`):
- **Shots:** she wakes in a dark CRT's reflection (face close-up, emissive eyes carry the dark), tidies her
  headdress, wipes the glass, switches the TV on. Face, headdress and right hand get the screen time; legs barely
  show.
- **Contract:** Mixamo bone names for the spine, neck, head, eyes, both arms and every finger bone; a `blink` morph.
  The loader fits shoulder-to-wrist to 0.97 and the head centre to y = 0.59, so proportions are free.
- **Budget:** 1.5 MB GLB in total, 1K textures, meshopt + WebP. A 25k–40k triangle character fits.
- **Hands:** the prologue poses every finger (reach, grip, wipe). They must be mechanical and clean at close range.

## A robot makes the generated route easier
Most of a robot is rigid: plates and shells that each follow one bone. Only cloth and hair bend. So v2 is a
**hybrid**:

| Piece | How it's made | Moves by |
|---|---|---|
| Head shell, face plate, headdress, ear units | generated parts (today's part route), one per bone | rigid, `Head` |
| Hair | generated with the head (head + hair views) | `Head`, springs later |
| Torso, upper arms, forearms, thighs, shins | generated body, then split at the joints | rigid per bone (no weights) |
| Joints (shoulder, elbow, wrist, knee) | generated or scripted rings | rigid |
| Dress, apron, skirt | generated with the body | donor weights (+ springs later) |
| Hands | scripted mechanical hands (v1's sculpted hands, restyled to the design) | finger bones |
| Eyes | emissive decal meshes; `blink` squashes them | morph |

So the hard step of the generated route (weights that bend skin cleanly) is only needed for the cloth, and the robot
body can be cut at the joints into rigid pieces. The skeleton still comes from the donor (AvatarSample E), fitted
to the design's joints, so the contract keeps passing.

## Steps

### 1. Design (Kevin)
What I need, in any form:
- **A full-body front picture**: a drawing, a sketch with colour notes, or a concept we iterate with `lochara
  concept` until it's right. A rough side or back is a bonus.
- **A short brief**: anything the picture can't show. For example: how robotic (visible joints? seams on the face?),
  materials (lacquer, porcelain, brushed metal, fabric), what glows and in what colour, hair style and length, the
  silhouette in the dark, must-keeps from v1 (black, white and orange? mouthless? lace headdress?).

*Output:* `design/front.png`, `design/design.md`. Checkpoint: Kevin signs off the design.

### 2. Views (spike S1)
Head + hair and the T-posed body in 4 views, plus 3 balance views. Kevin reviews them.

### 3. 3D (spike S2)
Head and body candidates. Pixal3D (front + back) is the target engine; install Xcode first. Kevin picks.

### 4. Cut and split (S3)
Hair from head; body cut at the joints into rigid shells; dress, apron and skirt kept as the skinned group.

### 5. Paint (S4), hands, eyes
Project the views onto the pieces. Restyle the scripted hands to the design's colours and plating. Eye decals with a
`blink` morph and emissive irises.

### 6. Rig (S5)
Fit AvatarSample E's skeleton to the design; parent the rigid shells to their bones; transfer the donor's weights to
the cloth only. Contract and budget checks.

### 7. In the prologue
Export to a branch of BentoSite, check every shot on the tuning page (`prototypes/crt-site/index.html`), tune
`ROBOT_HOME` only if needed, re-record the phone video. Kevin signs off; then it replaces `robot-maid.glb`.

### Later
Skirt and hair springs (S6), a VRM export for other apps, more expressions.

## Order and effort
| | Needs | Rough effort |
|---|---|---|
| Design | Kevin | open |
| Xcode install, Pixal3D setup | Kevin (App Store), then ~9 GB | an hour, mostly downloading |
| S1 views | design | a session |
| S2 3D | views, Pixal3D | a session (≈20 min per model) |
| S3–S5 | candidates | a session each |
| S6 rig, prologue check | the above | a session |

Spikes S1 and S2 can start on a stand-in design while Kevin's is in progress, so the route is known to work by the
time the real design lands.
