#!/usr/bin/env python3
"""Generate the LP's placeholder photography locally via ComfyUI + Z-Image Turbo (zero cost).

These stand in for the real product/lifestyle shoot so the prototype reads like the
wireframe (pastel product shots on white, high-key lifestyle crops, monochrome craft
photo). Every file is replaced by real photography before the Shopify build.

Start ComfyUI first:  cd ~/Workspace/ComfyUI && .venv/bin/python main.py --fp16-unet
Usage: gen_images.py [id ...] [--seed N] [--force]     (no ids = everything)
"""
import io, json, sys, time, urllib.parse, urllib.request
from pathlib import Path

from PIL import Image

HOST = "http://127.0.0.1:8188"
OUT = Path(__file__).resolve().parent.parent / "images"

BAG = ("Product photograph of a small soft hobo shoulder bag in COLOR smooth leather, one curved shoulder strap "
       "standing upright, a small silver metal clasp on the front, minimal clean design, centered front view, on a pure "
       "white seamless background, soft even studio light, faint soft shadow, high-key e-commerce catalog style. "
       "No text, no watermark, no hands, no people.")
COLORS = {
    "pink-beige": "pale pink beige", "camel": "warm camel tan", "mint": "pale mint green",
    "macaron-pink": "soft pastel macaron pink", "sumire": "soft violet lavender", "sage": "muted sage green",
    "beige": "light sand beige", "black": "matte black", "navy": "deep navy blue", "gray": "light warm gray",
    "silver": "pale metallic silver", "wine": "deep wine burgundy",
}
SNAP = ("Fashion lifestyle photograph, a young Japanese woman seen from the side from shoulders to hips, OUTFIT, "
        "carrying a small COLOR hobo shoulder bag on her shoulder, bright minimal white studio, soft diffused light, "
        "high-key, muted desaturated pastel tones, calm. No face visible, no text, no watermark.")


def snap(outfit, color):
    return SNAP.replace("OUTFIT", outfit).replace("COLOR", color)


SCENES = {
    "hero": ("Fashion lifestyle photograph, a young Japanese woman seen from the side, wearing a light beige knit top, "
             "carrying a small pale pink beige hobo shoulder bag on her shoulder, standing in a bright minimal white "
             "studio, soft diffused light, high-key, muted desaturated pastel tones, calm mood, generous empty space "
             "on the left. No text, no watermark.", 960, 1000),
    "intro": ("Close crop lifestyle photograph of the torso and arm of a woman in a light gray knit cardigan, a small "
              "pale hobo shoulder bag hanging from her shoulder, mid-step, bright white background, soft light, nearly "
              "monochrome light gray tones, high-key, minimal. No face, no text.", 1216, 608),
    "snap-1": (snap("wearing a soft white blouse and a cream skirt", "pale pink beige"), 1088, 864),
    "snap-2": (snap("wearing a light denim jacket and white tee", "camel tan"), 1088, 864),
    "snap-3": (snap("wearing a sage linen shirt dress", "pale mint"), 1088, 864),
    "snap-4": (snap("wearing a black long coat", "soft lavender"), 1088, 864),
    "inbag-items": ("Flat lay photograph from directly above on a white background: a black smartphone, a white card "
                    "case, a small gray leather pouch, a compact wallet, two lipsticks, a small cosmetic bottle, arranged "
                    "neatly with even spacing, soft even light, minimal, gray and white tones. No text.", 1024, 1024),
    "inbag-packed": ("Photograph of a small pale gray hobo shoulder bag standing open, seen slightly from above, showing "
                     "its contents inside: a white card case, a lipstick, a small pouch, a compact mirror, neatly packed, "
                     "white background, soft even light, minimal. No text.", 1024, 1024),
    "details-main": ("Macro close-up photograph of the flap edge of a pale pink beige pebbled leather bag with fine tonal "
                     "stitching and a soft fold, soft diffused light, high-key, minimal. No text.", 1216, 608),
    "detail-clasp": ("Macro photograph of a small polished silver metal clasp and strap ring on pale beige leather, soft "
                     "light, high-key, minimal. No text.", 1024, 1024),
    "detail-stitch": ("Macro photograph of neat tonal stitching along a seam of pale beige leather, soft light, high-key, "
                      "minimal. No text.", 1024, 1024),
    "detail-material": ("Macro photograph of pale beige fine-grained pebbled leather texture filling the frame, soft "
                        "light, high-key, minimal. No text.", 1024, 1024),
    "detail-inside": ("Photograph looking into the open interior of a pale beige leather shoulder bag showing the gray "
                      "fabric lining and an inner zip pocket, white background, soft light, minimal. No text.", 1024, 1024),
    "japan": ("Black and white photograph of a Japanese craftsman's hands guiding pale leather through an industrial "
              "sewing machine in a workshop, shallow depth of field, soft window light, monochrome documentary style. "
              "No text.", 1216, 608),
}


def workflow(prompt, seed, prefix, width, height):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "z_image_turbo_bf16.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "lumina2"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "4": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 3}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": prompt}},
        "6": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["5", 0]}},
        "7": {"class_type": "EmptySD3LatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "8": {"class_type": "KSampler", "inputs": {"model": ["4", 0], "positive": ["5", 0], "negative": ["6", 0], "latent_image": ["7", 0],
              "seed": seed, "steps": 9, "cfg": 1.0, "sampler_name": "res_multistep", "scheduler": "simple", "denoise": 1.0}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}},
        "10": {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": prefix}},
    }


def call(path, body=None):
    req = urllib.request.Request(HOST + path, data=json.dumps(body).encode() if body else None, headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def spec(iid):
    if iid.startswith("bag-"):
        return BAG.replace("COLOR", COLORS[iid[4:]]), 896, 1120
    return SCENES[iid]


def generate(iid, seed):
    prompt, w, h = spec(iid)
    pid = call("/prompt", {"prompt": workflow(prompt, seed, "kcs_" + iid, w, h)})["prompt_id"]
    t0 = time.time()
    while True:
        hist = call("/history/" + pid).get(pid)
        if hist and hist.get("status", {}).get("completed"):
            break
        if hist and hist.get("status", {}).get("status_str") == "error":
            raise RuntimeError(iid + ": ComfyUI error " + str(hist["status"]))
        if time.time() - t0 > 1800:
            raise TimeoutError(iid)
        time.sleep(3)
    img = hist["outputs"]["10"]["images"][0]
    q = urllib.parse.urlencode({"filename": img["filename"], "subfolder": img["subfolder"], "type": img["type"]})
    png = urllib.request.urlopen(HOST + "/view?" + q, timeout=60).read()
    dest = OUT / (iid + ".jpg")
    Image.open(io.BytesIO(png)).convert("RGB").save(dest, "JPEG", quality=86, optimize=True, progressive=True)
    print("%s: %.0fs -> %s (%d KB)" % (iid, time.time() - t0, dest.name, dest.stat().st_size // 1024), flush=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    seed = 369
    if "--seed" in args:
        i = args.index("--seed"); seed = int(args[i + 1]); del args[i:i + 2]
    force = "--force" in args
    ids = [a for a in args if a != "--force"] or ["bag-" + c for c in COLORS] + list(SCENES)
    OUT.mkdir(parents=True, exist_ok=True)
    for iid in ids:
        if (OUT / (iid + ".jpg")).exists() and not force:
            continue
        generate(iid, seed)
