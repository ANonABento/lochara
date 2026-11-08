"""lochara's Blender stages, run headless by the CLI:

    Blender -b --factory-startup -P blender/lochara_blender.py -- <stage> <job.json>

Stages:
  style   base model (VRM / GLB) -> styled GLB: bone names, morphs, material rules
  parts   styled GLB + generated parts -> character GLB: each part attached to one bone
  render  GLB -> a contact sheet (front, three-quarter, back) for review

The job file is written by the CLI: the character's recipe (character.json) with paths made absolute.
"""
import json
import math
import os
import shutil
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
PRESETS = os.path.join(os.path.dirname(HERE), 'presets')


# ------------------------------------------------------------------ io
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_model(path):
    """Import a .glb/.gltf/.vrm. VRM 0.x and 1.0 are glTF binaries, so the glTF importer reads them
    (VRM-only data such as spring bones is dropped; bones, skins, morphs and textures come through)."""
    src = path
    if path.lower().endswith('.vrm'):
        src = path + '.import.glb'
        shutil.copy(path, src)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=src)
    if src != path:
        os.remove(src)
    return [o for o in bpy.data.objects if o not in before]


def export_glb(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', export_skins=True, export_morph=True,
                              export_morph_normal=False, export_animations=False, export_yup=True)
    print('WROTE', path, os.path.getsize(path))


def armature():
    return next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)


def evaluated_verts(o):
    """World positions after modifiers (the armature's skinning), which is what renders. An optimised GLB's
    rest data can sit far from the character (quantisation moves it into the skin's bind space)."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get('co', co)
    ev.to_mesh_clear()
    co = co.reshape(-1, 3)
    M = np.array(o.matrix_world)
    return co @ M[:3, :3].T + M[:3, 3]


def bone_pos(arm, name):
    return arm.matrix_world @ arm.pose.bones[name].head


def world_verts(o):
    me = o.data
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    M = np.array(o.matrix_world)
    return co @ M[:3, :3].T + M[:3, 3]


# ------------------------------------------------------------------ style
def rename_bones(arm, preset):
    if preset in (None, 'keep'):
        return
    with open(os.path.join(PRESETS, 'bones', f'{preset}.json')) as f:
        table = json.load(f)['map']
    n = 0
    for b in arm.data.bones:
        for prefix in table.get('_strip', []):
            key = b.name[len(prefix):] if b.name.startswith(prefix) else None
            if key and key in table:
                b.name = table[key]; n += 1
                break
        else:
            if b.name in table:
                b.name = table[b.name]; n += 1
    print(f'bones: {n} renamed to {preset}')


def vroid_eye_morphs(face):
    """VRoid VRM 0.x morphs come through unnamed (target_N). Find blink / happy / irisOff by what they move:
    blink and happy move both eyelines evenly and not the mouth; irisOff moves only the iris."""
    me = face.data
    if not me.shape_keys:
        return {}
    n = len(me.vertices)

    def co(kb):
        a = np.empty(n * 3); kb.data.foreach_get('co', a); return a.reshape(-1, 3)

    def verts(frag):
        return np.array(sorted({v for p in me.polygons if frag in me.materials[p.material_index].name
                                for v in p.vertices}), dtype=int)
    base = co(me.shape_keys.key_blocks[0])
    line, iris, mouth = verts('FaceEyeline'), verts('EyeIris'), verts('FaceMouth')
    if not len(line):
        return {}
    x = base[:, 0]
    scores = []
    for kb in me.shape_keys.key_blocks[1:]:
        d = np.linalg.norm(co(kb) - base, axis=1)
        L, R = d[line][x[line] > 0].mean(), d[line][x[line] < 0].mean()
        scores.append((kb.name, L, R, d[iris].mean() if len(iris) else 0, d[mouth].mean() if len(mouth) else 0))
    both = sorted([s for s in scores if s[1] > 0.004 and abs(s[1] - s[2]) < 0.1 * s[1] and s[4] < 0.0005],
                  key=lambda s: -s[1])
    iris_only = sorted([s for s in scores if s[3] > 0.01 and s[1] < 0.0005], key=lambda s: -s[3])
    found = {}
    if both: found[both[0][0]] = 'blink'
    if len(both) > 1: found[both[1][0]] = 'happy'
    if iris_only: found[iris_only[0][0]] = 'irisOff'
    print('morphs detected:', found)
    return found


def apply_morphs(spec):
    if not spec:
        return
    detected = {}
    if spec.get('detect') == 'vroid-eyes':
        face = next((o for o in bpy.data.objects if o.type == 'MESH' and o.data.shape_keys
                     and any(m and 'FaceEyeline' in m.name for m in o.data.materials)), None)
        if face:
            detected = vroid_eye_morphs(face)
            for kb in face.data.shape_keys.key_blocks[1:]:
                if kb.name in detected:
                    kb.name = detected[kb.name]
    keep = spec.get('keep')
    if keep is None:
        return
    for o in bpy.data.objects:
        if o.type != 'MESH' or not o.data.shape_keys:
            continue
        for kb in list(o.data.shape_keys.key_blocks)[1:]:
            if kb.name not in keep:
                o.shape_key_remove(kb)


def principled(m):
    return next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None) if m and m.use_nodes else None


_tinted = {}


def tinted(img, tint):
    key = (img.name, tuple(tint))
    if key not in _tinted:
        W, H = img.size
        px = np.empty(W * H * 4, dtype=np.float32); img.pixels.foreach_get(px)
        px = px.reshape(-1, 4)
        px[:, :3] *= np.array(tint, dtype=np.float32)
        out = bpy.data.images.new(f'{img.name}_tint', W, H, alpha=True)
        out.pixels.foreach_set(px.ravel()); out.pack()
        _tinted[key] = out
    return _tinted[key]


def apply_materials(rules):
    """Rules match material names by fragment, first match wins:
    {"match": "FaceBrow", "delete": true} | {"match": "HAIR", "tint": [r, g, b]} |
    {"match": "EyeIris", "emissive": [r, g, b], "strength": 3}"""
    if not rules:
        return
    delete = []
    for o in [o for o in bpy.data.objects if o.type == 'MESH']:
        for i, m in enumerate(o.data.materials):
            if m is None:
                continue
            rule = next((r for r in rules if r['match'] in m.name), None)
            if not rule:
                continue
            if rule.get('delete'):
                delete.append((o, i)); continue
            tex = next((n for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image), None) if m.use_nodes else None
            p = principled(m)
            if 'tint' in rule:
                if tex:   # bake the tint into a copy of the texture: works for lit and unlit (VRoid) materials
                    tex.image = tinted(tex.image, rule['tint'])
                elif p:
                    p.inputs['Base Color'].default_value = (*rule['tint'], 1)
            if 'emissive' in rule and not p:
                print(f"note: {m.name} is unlit, so emissive does nothing (it already shows full colour)")
                continue
            if 'emissive' in rule:
                p.inputs['Emission Color'].default_value = (*rule['emissive'], 1)
                p.inputs['Emission Strength'].default_value = rule.get('strength', 1.0)
    for o, i in delete:
        delete_material_faces(o, i)


def delete_material_faces(o, index):
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index == index], context='FACES')
    bm.to_mesh(o.data); bm.free()


def stage_style(job):
    reset()
    import_model(job['base'])
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and not o.data.materials:
            bpy.data.objects.remove(o)                       # helper meshes some exporters leave behind
    arm = armature()
    style = job.get('style', {})
    if arm:
        rename_bones(arm, style.get('bones'))
    apply_morphs(style.get('morphs'))
    apply_materials(style.get('materials'))
    export_glb(job['out'])


# ------------------------------------------------------------------ parts
def frame(arm):
    """The character's own axes in world space: right, up, forward (from the hands and the feet)."""
    bones = arm.data.bones
    W = lambda n: arm.matrix_world @ bones[n].head_local
    up = Vector((0, 0, 1))
    if 'RightHand' in bones and 'LeftHand' in bones:
        right = (W('RightHand') - W('LeftHand'))
    else:
        right = Vector((-1, 0, 0))
    right.z = 0; right.normalize()
    fwd = up.cross(right)       # right-handed: right x up = -forward, so up x right = forward
    foot = next((n for n in ('LeftFoot', 'RightFoot') if n in bones), None)
    if foot:
        toe = (arm.matrix_world.to_3x3() @ (bones[foot].tail_local - bones[foot].head_local))
        if toe.dot(fwd) < 0:    # the feet point forward; trust them over the cross product
            fwd = -fwd; right = -right
    return right, up, fwd


def mirror_name(bone):
    for a, b in (('Left', 'Right'), ('Right', 'Left'), ('_L', '_R'), ('_R', '_L'), ('.L', '.R'), ('.R', '.L')):
        if a in bone:
            return bone.replace(a, b)
    return bone


def glow_texture(img, hue, strength_name):
    """An emissive map: the pixels whose hue falls in [lo, hi] degrees (and are saturated and bright) keep
    their colour, the rest go black. Generated parts paint their lights on; this makes them glow."""
    W, H = img.size
    px = np.empty(W * H * 4, dtype=np.float32); img.pixels.foreach_get(px)
    px = px.reshape(-1, 4)
    rgb = px[:, :3]
    mx, mn = rgb.max(1), rgb.min(1)
    d = np.where(mx - mn == 0, 1e-6, mx - mn)
    r, g, b = rgb.T
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    s = np.where(mx == 0, 0, (mx - mn) / np.maximum(mx, 1e-6))
    lo, hi = hue
    on = ((h >= lo) & (h <= hi) if lo <= hi else (h >= lo) | (h <= hi)) & (s > 0.35) & (mx > 0.3)
    out = np.zeros_like(px); out[:, 3] = 1
    out[on, :3] = rgb[on]
    em = bpy.data.images.new(strength_name, W, H)
    em.pixels.foreach_set(out.ravel()); em.pack()
    print(f'glow: {on.mean() * 100:.1f}% of the texture lights up')
    return em


def add_glow(obj, glow):
    for m in obj.data.materials:
        p = principled(m)
        tex = next((n for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image), None) if p else None
        if not tex:
            continue
        node = m.node_tree.nodes.new('ShaderNodeTexImage')
        node.image = glow_texture(tex.image, glow.get('hue', [10, 45]), f'{m.name}_glow')
        uv = tex.inputs['Vector'].links[0].from_socket if tex.inputs['Vector'].links else None
        if uv:
            m.node_tree.links.new(uv, node.inputs['Vector'])
        m.node_tree.links.new(node.outputs['Color'], p.inputs['Emission Color'])
        p.inputs['Emission Strength'].default_value = glow.get('strength', 3.0)


def place_part(part, arm, axes, side_bone, mirrored):
    objs = [o for o in import_model(part['model']) if o.type == 'MESH']
    if not objs:
        raise SystemExit(f"part {part['id']}: no mesh in {part['model']}")
    bpy.context.view_layer.update()
    for o in objs:   # bake transforms so the part is plain geometry in world space
        o.data.transform(o.matrix_world); o.parent = None; o.matrix_world = Matrix.Identity(4)
    if len(objs) > 1:
        with bpy.context.temp_override(active_object=objs[0], selected_editable_objects=objs):
            bpy.ops.object.join()
    ob = objs[0]
    ob.name = f"part_{part['id']}" + ('_mirror' if mirrored else '')
    v = world_verts(ob)
    lo, hi = v.min(0), v.max(0)
    centre, longest = (lo + hi) / 2, float((hi - lo).max())
    scale = part.get('size', longest) / longest
    right, up, fwd = axes
    # the part's own frame, as AssetFurnace previews it: front = glTF +Z = Blender -Y, up = +Z
    # columns are where the part's X, Y, Z go: -Y (its front) -> forward, Z -> up, X -> the character's left
    # (the only choice that keeps it a rotation, not a reflection)
    to_char = Matrix(((-right.x, -fwd.x, up.x), (-right.y, -fwd.y, up.y), (-right.z, -fwd.z, up.z)))
    rx, ry, rz = (math.radians(a) for a in part.get('rotation', [0, 0, 0]))
    turn = (Matrix.Rotation(ry, 3, up) @ Matrix.Rotation(rx, 3, right) @ Matrix.Rotation(rz, 3, fwd))
    R = turn @ to_char
    if mirrored:   # reflect across the character's centre plane
        mir = Matrix.Identity(3) - 2 * Matrix([[right.x * right.x, right.x * right.y, right.x * right.z],
                                                  [right.y * right.x, right.y * right.y, right.y * right.z],
                                                  [right.z * right.x, right.z * right.y, right.z * right.z]])
        R = mir @ R
    M = R.to_4x4() @ Matrix.Diagonal((scale, scale, scale, 1)) @ Matrix.Translation(-Vector(centre))
    ob.data.transform(M)
    if mirrored:
        bm = bmesh.new(); bm.from_mesh(ob.data)
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:]); bm.to_mesh(ob.data); bm.free()
    ox, oy, oz = part.get('offset', [0, 0, 0])
    if mirrored:
        ox = -ox
    head = arm.matrix_world @ arm.data.bones[side_bone].head_local
    ob.location = head + right * ox + up * oy + fwd * oz
    if part.get('glow'):
        add_glow(ob, part['glow'])
    bpy.context.view_layer.update()          # matrix_world is stale until the scene updates
    mw = ob.matrix_world.copy()
    ob.parent = arm; ob.parent_type = 'BONE'; ob.parent_bone = side_bone
    bpy.context.view_layer.update()
    ob.matrix_world = mw
    return ob


def stage_parts(job):
    reset()
    import_model(job['styled'])
    arm = armature()
    parts = [p for p in job.get('parts', []) if p.get('enabled', True)]
    if parts and not arm:
        raise SystemExit('parts need a rigged base (no armature found)')
    axes = frame(arm) if arm else None
    for p in parts:
        if p['bone'] not in arm.data.bones:
            raise SystemExit(f"part {p['id']}: no bone {p['bone']!r} (bones: {', '.join(b.name for b in arm.data.bones)[:400]})")
        place_part(p, arm, axes, p['bone'], False)
        if p.get('mirror'):
            place_part(p, arm, axes, mirror_name(p['bone']), True)
        print('part', p['id'], 'on', p['bone'], '(mirrored)' if p.get('mirror') else '')
    export_glb(job['out'])


# ------------------------------------------------------------------ render
def stage_render(job):
    reset()
    import_model(job['model'])
    scn = bpy.context.scene
    try:
        scn.render.engine = 'BLENDER_EEVEE'
    except TypeError:
        scn.render.engine = 'BLENDER_EEVEE_NEXT'
    w, h = job.get('size', [600, 900])
    scn.render.resolution_x, scn.render.resolution_y = w, h
    world = bpy.data.worlds.new('W'); scn.world = world; world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.09, 0.085, 0.08, 1)
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.name != 'Icosphere']
    bpy.context.view_layer.update()
    v = np.concatenate([evaluated_verts(o) for o in meshes])
    lo, hi = v.min(0), v.max(0)
    c = Vector(((lo + hi) / 2).tolist())
    span = float((hi - lo).max())
    arm = armature()
    right, up, fwd = frame(arm) if arm else (Vector((-1, 0, 0)), Vector((0, 0, 1)), Vector((0, -1, 0)))
    if job.get('focus') and arm and job['focus'] in arm.data.bones:
        c = bone_pos(arm, job['focus'])
        span = job.get('span', 0.4)
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); scn.collection.objects.link(cam)
    scn.camera = cam; cam.data.angle = math.radians(30)
    key = bpy.data.objects.new('Key', bpy.data.lights.new('Key', 'AREA'))
    key.data.energy, key.data.size = 60 * span * span + 40, span
    rim = bpy.data.objects.new('Rim', bpy.data.lights.new('Rim', 'AREA'))
    rim.data.energy, rim.data.size, rim.data.color = 40 * span * span + 30, span, (1, .8, .6)
    for o in (key, rim):
        scn.collection.objects.link(o)

    def look(obj, frm):
        obj.location = frm
        obj.rotation_euler = (c - frm).to_track_quat('-Z', 'Y').to_euler()

    dist = span / (2 * math.tan(math.radians(15))) * 1.15
    shots = [('front', fwd), ('three-quarter', (fwd + right * -0.9).normalized()), ('back', -fwd)]
    frames = []
    for name, d in shots:
        look(cam, c + d * dist + up * span * 0.05)
        look(key, c + (fwd + right * 0.8 + up).normalized() * dist)
        look(rim, c + (-fwd - right * 0.6 + up * 0.8).normalized() * dist)
        path = job['out'] + f'.{name}.png'
        scn.render.filepath = path
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(path)
        px = np.empty(w * h * 4, dtype=np.float32); img.pixels.foreach_get(px)
        frames.append(px.reshape(h, w, 4)); os.remove(path)
    sheet = np.concatenate(frames, axis=1)
    out = bpy.data.images.new('sheet', w * len(frames), h)
    out.pixels.foreach_set(sheet.ravel()); out.filepath_raw = job['out']; out.file_format = 'PNG'; out.save()
    print('WROTE', job['out'])


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:]
    stage, job_file = argv[0], argv[1]
    with open(job_file) as f:
        job = json.load(f)
    {'style': stage_style, 'parts': stage_parts, 'render': stage_render}[stage](job)
