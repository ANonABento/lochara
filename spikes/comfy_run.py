"""Run a ComfyUI editor workflow (a template's .json) through the API, with some nodes' values replaced.

    python3 spikes/comfy_run.py <workflow.json> [--set ID.input=value ...] [--load ID=picture.png ...] [--dry]

- Editor workflows keep widget values as a list; the API wants named inputs. The names come from the server's
  /object_info, in its order (a seed's "control after generate" value is skipped).
- Notes, preview and muted nodes are dropped; bypassed ones run (templates bypass optional inputs, like the side
  views); Reroutes are followed through.
- `--load ID=file` makes node ID a LoadImage of that file (copied into ComfyUI's input folder), whatever it was.
- Waits for the run and prints the files it wrote.
Spike S2 (docs/plans/generated-character.md).
"""

import argparse
import json
import shutil
import time
import urllib.request
from pathlib import Path

SERVER = "http://127.0.0.1:8188"
COMFY = Path(__file__).resolve().parents[1] / "vendor" / "comfyui"
SKIP = {"Note", "MarkdownNote", "PreviewImage", "Preview3DAdvanced", "Preview3D", "GetMeshInfo", "SaveImageAdvanced"}
WIDGET_TYPES = {"INT", "FLOAT", "STRING", "BOOLEAN", "COMBO", "COLOR", "BOUNDING_BOX", "LOAD_3D", "COMFY_DYNAMICCOMBO_V3"}


def get(path: str):
    return json.load(urllib.request.urlopen(SERVER + path))


def is_widget(spec) -> bool:
    t, opts = spec[0], spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {}
    return isinstance(t, list) or t in WIDGET_TYPES or "default" in opts or opts.get("socketless", False)


def convert(wf: dict, info: dict) -> dict:
    nodes = {n["id"]: n for n in wf["nodes"]}
    links = {l[0]: l for l in wf["links"]}  # id, src, src_slot, dst, dst_slot, type

    def source(link_id):
        _, src, slot, *_ = links[link_id]
        # Reroutes, and previews that pass their picture on, are followed back to what feeds them.
        while nodes[src]["type"] == "Reroute" or nodes[src]["type"] in SKIP and nodes[src].get("inputs"):
            src, slot = links[nodes[src]["inputs"][0]["link"]][1:3]
        return [str(src), slot]

    out = {}
    for nid, n in nodes.items():
        t = n["type"]
        if t in SKIP or t == "Reroute" or n.get("mode") == 2:  # bypassed (4) nodes run: templates bypass optional views
            continue
        if t not in info:
            raise SystemExit(f"node {nid}: {t} isn't on this server")
        spec = {**info[t]["input"].get("required", {}), **info[t]["input"].get("optional", {})}
        linked = {i["name"]: i["link"] for i in n.get("inputs", []) if i.get("link") is not None}
        values = list(n.get("widgets_values") or [])
        if isinstance(n.get("widgets_values"), dict):
            values = []
        inputs = {}
        for name, s in spec.items():
            if is_widget(s):
                if values:
                    inputs[name] = values.pop(0)
                    opts = s[1] if len(s) > 1 and isinstance(s[1], dict) else {}
                    if opts.get("control_after_generate") and values:
                        values.pop(0)
                    # A dynamic combo's chosen option brings its own inputs, next in the list, as `name.sub`.
                    if s[0] == "COMFY_DYNAMICCOMBO_V3":
                        chosen = next((o for o in opts.get("options", []) if o["key"] == inputs[name]), {})
                        for sub in {**chosen.get("inputs", {}).get("required", {}),
                                    **chosen.get("inputs", {}).get("optional", {})}:
                            if values:
                                inputs[f"{name}.{sub}"] = values.pop(0)
            if name in linked:
                inputs[name] = source(linked[name])
        out[str(nid)] = {"class_type": t, "inputs": inputs}
    # Outputs feeding only dropped nodes are fine; inputs pointing at dropped nodes are not.
    for nid, n in out.items():
        for k, v in list(n["inputs"].items()):
            if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str) and v[0] not in out:
                raise SystemExit(f"node {nid}.{k} needs dropped node {v[0]}")
    return out


def coerce(v: str):
    for f in (int, float):
        try:
            return f(v)
        except ValueError:
            pass
    return {"true": True, "false": False}.get(v, v)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("workflow")
    ap.add_argument("--set", nargs="*", default=[])
    ap.add_argument("--load", nargs="*", default=[])
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    prompt = convert(json.load(open(a.workflow)), get("/object_info"))
    for item in a.load:
        nid, path = item.split("=", 1)
        name = f"lochara-{Path(path).parent.name}-{Path(path).name}"
        shutil.copy(path, COMFY / "input" / name)
        prompt[nid] = {"class_type": "LoadImage", "inputs": {"image": name}}
    for item in a.set:
        key, v = item.split("=", 1)
        nid, inp = key.split(".", 1)
        prompt[nid]["inputs"][inp] = coerce(v)
    if a.dry:
        print(json.dumps(prompt, indent=1))
        return
    req = urllib.request.Request(SERVER + "/prompt", json.dumps({"prompt": prompt}).encode(),
                                 {"Content-Type": "application/json"})
    try:
        pid = json.load(urllib.request.urlopen(req))["prompt_id"]
    except urllib.error.HTTPError as e:
        raise SystemExit(e.read().decode()[:3000])
    t0 = time.time()
    while True:
        h = get(f"/history/{pid}").get(pid)
        if h and h.get("status", {}).get("completed") is not None or h and h["status"].get("status_str") == "error":
            break
        time.sleep(5)
    print(f"{h['status'].get('status_str')} in {time.time() - t0:.0f}s")
    for msg in h["status"].get("messages", []):
        if msg[0] == "execution_error":
            print(json.dumps(msg[1])[:2000])
    for nid, o in h.get("outputs", {}).items():
        for kind, items in o.items():
            for it in items if isinstance(items, list) else []:
                if isinstance(it, dict) and "filename" in it:
                    print(f"{nid} {kind}: {COMFY / 'output' / it.get('subfolder', '') / it['filename']}")


if __name__ == "__main__":
    main()
