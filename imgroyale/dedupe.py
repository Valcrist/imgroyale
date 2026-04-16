import os
import imagehash
import numpy as np
from PIL import Image
from skimage.metrics import peak_signal_noise_ratio as psnr, mean_squared_error
from toolbox.fs import (
    basedir,
    strip_basedir,
    create_path,
    dissect_path,
    os_path,
    copy,
    move,
    copy_move,
)
from toolbox.exceptions import ToolboxError, ToolboxWarning
from toolbox.utils import debug, err


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
            err(f"Missing image: {src}")
            return None
        base = os.path.splitext(os.path.basename(src))[0]
        out_dir = scratch_dir if scratch_dir else os.path.dirname(src)
        dst = os_path(os.path.join(out_dir, base + ".webp"))
        with Image.open(src) as img:
            if img.format == "WEBP":
                debug(src, "Skipped; already webp", lvl=2)
                return src
            if img.mode in ("P", "PA"):
                img = img.convert("RGBA")
            img.save(dst, format="WEBP", lossless=quality == 100, quality=quality)
        debug(dst, "Converted to webp", lvl=2)
        return dst
    except Exception as e:
        raise ImgRoyaleError(f"Error converting to WebP: {src} [{e}]")


def perceptual_hash(img):
    try:
        if not os.path.exists(img):
            err(f"Missing image to hash: {img}")
            return None
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


def copy_best(src, dst, no_move=False):
    try:
        if not os.path.exists(src):
            raise ImgRoyaleError(f"Source image does not exist: {src}")

        if not os.path.exists(dst):
            debug(dst, "New image; nothing to compare")
            success = copy(src, dst)
            if not success:
                err(f"Failed to copy: {src} to {dst}")
            return success

        print(f"compare {src} vs {dst} ..")
        with Image.open(src) as src_img, Image.open(dst) as dst_img:
            src_size = src_img.size
            dst_size = dst_img.size

            if src_size != dst_size:
                if src_size[0] * src_size[1] > dst_size[0] * dst_size[1]:
                    success = copy(src, dst)
                    if not success:
                        err(f"Failed to copy: {src} to {dst}")
                    return success

                else:
                    print(
                        f"[copy_best] Skipped; existing image has higher "
                        f"resolution: {dst}"
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
                    err(f"Failed to copy: {src} to {dst}")
                return success

            else:
                print(f"[copy_best] Skipped; existing image is better: {dst}")

            return True

    except Exception as e:
        raise ImgRoyaleError(f"Error comparing images: {src}, {dst} [{e}]")


def deduped_img_path(src, basedir=basedir()):
    return (
        strip_basedir(src, basedir=basedir)
        .replace(f"media{os.sep}", "")
        .replace("\\", "/")
    )


def dedupe_image(in_file: str, out_dir: str, scratch_dir: str):
    if not os.path.exists(in_file):
        err(f"Missing image source: {in_file}")
        return None
    create_path(out_dir)
    create_path(scratch_dir)
    webp = to_webp(in_file, scratch_dir=scratch_dir)
    phash = perceptual_hash(webp)
    path = os_path(f"{format_hash(phash)}.webp")
    debug(path)
    dst_path = os_path(os.path.join(out_dir, path) if out_dir else path)
    debug(dst_path)
    success = copy_best(webp, dst_path)
    if not success:
        err(f"Failed to copy: {webp} to {dst_path}")
        return in_file
    # return deduped_img_path(dst_path, basedir=out_dir) if out_dir else dst_path
