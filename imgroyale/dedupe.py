import os
import imagehash
import numpy as np
from PIL import Image
from skimage.metrics import peak_signal_noise_ratio as psnr, mean_squared_error
from toolbox.fs import slash_nix, create_path, copy
from toolbox.exceptions import ToolboxError, ToolboxWarning
from toolbox.utils import debug


class ImgRoyaleError(ToolboxError):
    pass


class ImgRoyaleWarning(ToolboxWarning):
    pass


def to_webp(
    src: str,
    scratch_dir: str | None = None,
    quality: int = 75,
) -> str | None:
    """Convert an image to WebP. Returns the output path on success, None on failure."""
    try:
        if not os.path.exists(src):
            raise ImgRoyaleError(f"Missing image: {src}")
        base = os.path.splitext(os.path.basename(src))[0]
        out_dir = scratch_dir if scratch_dir else os.path.dirname(src)
        dst = slash_nix(os.path.join(out_dir, base + ".webp"))
        with Image.open(src) as img:
            if img.format == "WEBP":
                debug(f"{src} already WebP", "Conversion skipped", lvl=2)
                return src
            if img.mode in ("P", "PA"):
                img = img.convert("RGBA")
            img.save(dst, format="WEBP", lossless=quality == 100, quality=quality)
        debug(f"{src} -> {dst}", "Converted to webp", lvl=2)
        return dst
    except Exception as e:
        raise ImgRoyaleError(f"Error converting to WebP: {src} [{e}]")


def perceptual_hash(img):
    try:
        if not os.path.exists(img):
            raise ImgRoyaleError(f"Missing image to hash: {img}")
        with Image.open(img) as image:
            if image.mode != "RGB":
                image = image.convert("RGB")
            return str(imagehash.phash(image))
    except Exception as e:
        raise ImgRoyaleError(f"Error computing perceptual hash: {img} [{e}]")


def format_hash(text):
    formatted = (
        text[:2] + "/" + text[2:4] + "/" + text[4:6] + "/" + text[6:8] + "/" + text[8:]
    )
    return formatted


def save_best(src, dst):
    try:
        if not os.path.exists(src):
            raise ImgRoyaleError(f"Source image does not exist: {src}")

        if not os.path.exists(dst):
            debug(dst, "New image; nothing to compare")
            success = copy(src, dst)
            if not success:
                raise ImgRoyaleError(f"Failed to copy: {src} to {dst}")
            return success

        debug(f"{src} vs {dst} ..", "Comparing", lvl=2)
        with Image.open(src) as src_img, Image.open(dst) as dst_img:
            src_size = src_img.size
            dst_size = dst_img.size

            if src_size != dst_size:
                if src_size[0] * src_size[1] > dst_size[0] * dst_size[1]:
                    success = copy(src, dst)
                    if not success:
                        raise ImgRoyaleError(f"Failed to copy: {src} to {dst}")
                    debug(
                        f"New image has better resolution : "
                        f"new={src_size} vs old={dst_size}",
                        "Comparison result",
                        lvl=2,
                    )
                    return success

                else:
                    debug(
                        f"Old image has better resolution : "
                        f"new={src_size} vs old={dst_size}",
                        "Comparison result",
                        lvl=2,
                    )
                    return True

            try:
                src_img = np.array(src_img)
                dst_img = np.array(dst_img)
                mse = mean_squared_error(src_img, dst_img)
                if mse == 0:
                    psnr_src = 100  # Arbitrary high value for identical images
                    psnr_dst = 100
                else:
                    psnr_src = psnr(
                        src_img, dst_img, data_range=src_img.max() - src_img.min()
                    )
                    psnr_dst = psnr(
                        dst_img, src_img, data_range=dst_img.max() - dst_img.min()
                    )
            except:
                psnr_src = 0
                psnr_dst = 0

            if psnr_src > psnr_dst:
                success = copy(src, dst)
                if not success:
                    raise ImgRoyaleError(f"Failed to copy: {src} to {dst}")
                debug(
                    f"New image has higher PSNR : "
                    f"new={psnr_src:.2f} vs old={psnr_dst:.2f}",
                    "Comparison result",
                    lvl=2,
                )
                return success
            else:
                comparison = "the same" if psnr_src == psnr_dst else "higher"
                debug(
                    f"Old image has {comparison} PSNR : "
                    f"new={psnr_src:.2f} vs old={psnr_dst:.2f}",
                    "Comparison result",
                    lvl=2,
                )
                return True

    except ImgRoyaleError:
        raise
    except Exception as e:
        raise ImgRoyaleError(f"[save_best] Failed: {src} -> {dst} [{e}]")


def dedupe_image(in_file: str, out_dir: str, scratch_dir: str):
    try:
        if not os.path.exists(in_file):
            raise ImgRoyaleError(f"Missing image source: {in_file}")
        create_path(out_dir)
        create_path(scratch_dir)
        webp = slash_nix(to_webp(in_file, scratch_dir=scratch_dir))
        phash = perceptual_hash(webp)
        dst_path = slash_nix(os.path.join(out_dir, f"{format_hash(phash)}.webp"))
        success = save_best(webp, dst_path)
        if os.path.dirname(webp) == slash_nix(os.path.normpath(scratch_dir)):
            os.remove(webp)
        if not success:
            ImgRoyaleWarning(f"Failed to copy: {webp} to {dst_path}")
            return in_file
        return dst_path
    except ImgRoyaleError:
        raise
    except Exception as e:
        raise ImgRoyaleError(f"[dedupe_image] Failed: {in_file} -> {out_dir} [{e}]")
