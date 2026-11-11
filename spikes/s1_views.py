"""Spike S1: views of a character from one design picture, with Qwen-Image-Edit 2511 in mflux.

Run with mflux's own Python (it imports mflux's internals):

    ~/.local/share/uv/tools/mflux/bin/python spikes/s1_views.py characters/bastet-smol/concepts/c-d1.png \
        --model vendor/hf/qwen-edit-2511-views-q4 --out characters/bastet-smol/views [--only body-right] [--seed 1]

The model is a saved copy with the Lightning (8-step) and angles LoRAs baked in (`mflux-save --bake-lora`, see
docs/plans/generated-character.md, "S1 so far").

Two changes from `mflux-generate-qwen-edit`, both for memory and time on a 24 GB Mac:
- Every view's prompt is encoded first, then the 14 GB text encoder is dropped, so drawing only holds the image
  model (about 19 GB instead of 33).
- At guidance 1 (what Lightning wants) the negative pass changes nothing (`compute_guided_noise` returns the
  positive noise), so each step runs the image model once instead of twice.
"""

import argparse
import gc
import time
from pathlib import Path

import mlx.core as mx
from mflux.models.common.config.config import Config
from mflux.models.common.vae.vae_util import VAEUtil
from mflux.models.qwen.latent_creator.qwen_latent_creator import QwenLatentCreator
from mflux.models.qwen.variants.edit.qwen_edit_util import QwenEditUtil
from mflux.models.qwen.variants.edit.qwen_image_edit import QwenImageEdit
from mflux.utils.image_util import ImageUtil

# The angles LoRA's prompt: <sks> <azimuth> <elevation> <distance>.
VIEWS = {
    "body-front": "front view eye-level shot wide shot",
    "body-right": "right side view eye-level shot wide shot",
    "body-back": "back view eye-level shot wide shot",
    "body-left": "left side view eye-level shot wide shot",
    "head-front": "front view eye-level shot close-up",
    "head-right": "right side view eye-level shot close-up",
    "head-back": "back view eye-level shot close-up",
    "head-left": "left side view eye-level shot close-up",
}

GB = 1024**3


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("design")
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", nargs="*", choices=list(VIEWS))
    ap.add_argument("--prompt", nargs="*", default=[], metavar="NAME=TEXT",
                    help="free edits instead of views, e.g. tpose='put her in a T-pose' (no angle tag)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--steps", type=int, default=8)
    ap.add_argument("--width", type=int, default=768)
    ap.add_argument("--height", type=int, default=1152)
    a = ap.parse_args()
    views = ({k: v for k, v in (x.split("=", 1) for x in a.prompt)} if a.prompt
             else {k: f"<sks> {VIEWS[k]}" for k in (a.only or VIEWS)})
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    images = [a.design]

    t0 = time.time()
    model = QwenImageEdit(model_path=a.model)
    _, vl_w, vl_h, vae_w, vae_h = model._compute_dimensions(
        image_paths=images, num_inference_steps=a.steps, height=a.height, width=a.width,
        guidance=1.0, image_path=None, scheduler="linear")
    print(f"loaded in {time.time() - t0:.0f}s, peak {mx.get_peak_memory() / GB:.1f} GB", flush=True)

    # 1. Encode every prompt, and the design for the image model, while the text encoder is here.
    tok = model.tokenizers["qwen_vl"]
    embeds = {}
    for name, angle in views.items():
        ids, mask, pixels, grid = tok.tokenize_with_image(angle, images, vl_width=vl_w, vl_height=vl_h)
        h = model.qwen_vl_encoder(input_ids=ids, attention_mask=mask, pixel_values=pixels, image_grid_thw=grid)
        embeds[name] = (h[0].astype(mx.float16), h[1].astype(mx.float16))
        mx.eval(embeds[name])
    cond, cond_ids, cond_h, cond_w, n_images = QwenEditUtil.create_image_conditioning_latents(
        vae=model.vae, width=vae_w, height=vae_h, image_paths=images, tiling_config=model.tiling_config)
    mx.eval(cond)
    grid = (1, cond_h, cond_w) if n_images == 1 else [(1, cond_h, cond_w)] * n_images
    print(f"encoded {len(embeds)} prompts in {time.time() - t0:.0f}s, peak {mx.get_peak_memory() / GB:.1f} GB",
          flush=True)

    # 2. Drop the text encoder.
    model.text_encoder = None
    model.qwen_vl_encoder = None
    gc.collect()
    mx.clear_cache()
    mx.reset_peak_memory()
    print(f"text encoder dropped: {mx.get_active_memory() / GB:.1f} GB held", flush=True)

    # 3. Draw each view: one image-model pass per step.
    for name, (emb, emb_mask) in embeds.items():
        t1 = time.time()
        config = Config(width=vae_w, height=vae_h, guidance=1.0, scheduler="linear", image_path=None,
                        model_config=model.model_config, num_inference_steps=a.steps)
        latents = QwenLatentCreator.create_noise(seed=a.seed, width=config.width, height=config.height)
        for t in range(len(config.scheduler.timesteps)):
            noise = model.transformer(
                t=t, config=config, hidden_states=mx.concatenate([latents, cond], axis=1),
                encoder_hidden_states=emb, encoder_hidden_states_mask=emb_mask,
                qwen_image_ids=cond_ids, cond_image_grid=grid)[:, : latents.shape[1]]
            latents = config.scheduler.step(noise=noise, timestep=t, latents=latents)
            mx.eval(latents)
        decoded = VAEUtil.decode(vae=model.vae, latent=QwenLatentCreator.unpack_latents(
            latents=latents, height=config.height, width=config.width), tiling_config=model.tiling_config)
        took = time.time() - t1
        ImageUtil.to_image(decoded_latents=decoded, config=config, seed=a.seed, prompt=views[name],
                           quantization=model.bits, lora_paths=None, lora_scales=None, image_path=None,
                           image_paths=images, generation_time=took).save(out / f"{name}.png")
        print(f"{name}: {took:.0f}s, peak {mx.get_peak_memory() / GB:.1f} GB", flush=True)


if __name__ == "__main__":
    main()
