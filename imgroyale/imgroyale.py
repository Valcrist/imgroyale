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
    out_dir: str | None = None,
    quality: int = 75,
) -> str:
    """Convert an image to WebP. Returns the output path on success."""
    try:
        if not os.path.exists(src):
            raise ImgRoyaleError(f"Missing image: {src}")
        base = os.path.splitext(os.path.basename(src))[0]
        dst_dir = out_dir if out_dir else os.path.dirname(src)
        dst = slash_nix(os.path.join(dst_dir, base + ".webp"))
        with Image.open(src) as img:
            if img.format == "WEBP":
                debug(f"{src} already WebP", "Conversion skipped", lvl=2)
                return src
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert(
                    "RGBA" if img.mode in ("P", "PA", "LA", "L") else "RGB"
                )
            img.save(dst, format="WEBP", lossless=quality == 100, quality=quality)
        debug(f"{src} -> {dst}", "Converted to webp", lvl=2)
        return dst
    except ImgRoyaleError:
        raise
    except Exception as e:
        raise ImgRoyaleError(f"Error converting to WebP: {src} [{e}]")


def perceptual_hash(img: str) -> str:
    """Compute the perceptual hash of an image file.

    Converts the image to RGB before hashing to ensure consistent results
    across different source modes. Returns the hash as a hex string.
    """
    try:
        if not os.path.exists(img):
            raise ImgRoyaleError(f"Missing image to hash: {img}")
        with Image.open(img) as image:
            if image.mode != "RGB":
                image = image.convert("RGB")
            return str(imagehash.phash(image))
    except ImgRoyaleError:
        raise
    except Exception as e:
        raise ImgRoyaleError(f"Error computing perceptual hash: {img} [{e}]")


def format_hash(text: str) -> str:
    """Format a hex hash string into a slash-separated directory path.

    Splits the hash into 2-character segments separated by slashes, suitable
    for use as a nested directory structure (e.g. ``ab/cd/ef/12/rest``).
    """
    formatted = (
        text[:2] + "/" + text[2:4] + "/" + text[4:6] + "/" + text[6:8] + "/" + text[8:]
    )
    return formatted


def get_image_size(img: str | Image.Image) -> tuple[int, int]:
    """Return the (width, height) of an image given a path or open handle."""
    if isinstance(img, str):
        with Image.open(img) as f:
            return f.size
    return img.size


def compute_psnr(
    img1: str | Image.Image,
    img2: str | Image.Image,
) -> tuple[float, float]:
    """Compute PSNR in both directions between two images.

    Accepts file paths or open Image handles. Returns ``(psnr1, psnr2)`` where
    psnr1 measures img1 relative to img2 and psnr2 the reverse. Returns
    ``(100.0, 100.0)`` for identical images and ``(0.0, 0.0)`` on error.
    """
    try:

        def to_arr(img: str | Image.Image) -> np.ndarray:
            if isinstance(img, str):
                with Image.open(img) as f:
                    return np.array(f)
            return np.array(img)

        arr1, arr2 = to_arr(img1), to_arr(img2)
        mse = mean_squared_error(arr1, arr2)
        if mse == 0:
            return (100.0, 100.0)
        data_range = (
            int(np.iinfo(arr1.dtype).max)
            if np.issubdtype(arr1.dtype, np.integer)
            else 1.0
        )
        return (
            psnr(arr1, arr2, data_range=data_range),
            psnr(arr2, arr1, data_range=data_range),
        )
    except Exception:
        return (0.0, 0.0)


def pick_best(img1: str, img2: str) -> str:
    """Compare two images and return the path of the better one.

    Prefers higher resolution; falls back to PSNR when sizes match.
    Returns img1 if img1 is better, img2 otherwise.
    """
    try:
        if not os.path.exists(img1):
            raise ImgRoyaleError(f"Image does not exist: {img1}")
        if not os.path.exists(img2):
            return img1

        debug(f"{img1} vs {img2} ..", "Comparing", lvl=2)
        with Image.open(img1) as img1_file, Image.open(img2) as img2_file:
            img1_size = get_image_size(img1_file)
            img2_size = get_image_size(img2_file)
            if img1_size != img2_size:
                if img1_size[0] * img1_size[1] > img2_size[0] * img2_size[1]:
                    debug(
                        f"img1 has better resolution : "
                        f"img1={img1_size} vs img2={img2_size}",
                        "Comparison result",
                        lvl=2,
                    )
                    return img1
                else:
                    debug(
                        f"img2 has better resolution : "
                        f"img1={img1_size} vs img2={img2_size}",
                        "Comparison result",
                        lvl=2,
                    )
                    return img2

            psnr_img1, psnr_img2 = compute_psnr(img1_file, img2_file)
            if psnr_img1 > psnr_img2:
                debug(
                    f"img1 has higher PSNR : "
                    f"img1={psnr_img1:.2f} vs img2={psnr_img2:.2f}",
                    "Comparison result",
                    lvl=2,
                )
                return img1
            else:
                comparison = "the same" if psnr_img1 == psnr_img2 else "higher"
                debug(
                    f"img2 has {comparison} PSNR : "
                    f"img1={psnr_img1:.2f} vs img2={psnr_img2:.2f}",
                    "Comparison result",
                    lvl=2,
                )
                return img2

    except ImgRoyaleError:
        raise
    except Exception as e:
        raise ImgRoyaleError(f"[pick_best] Failed: {img1} vs {img2} [{e}]")


def save_best(src: str, dst: str) -> bool:
    """Copy src to dst only if src is the better image.

    If dst does not exist, copies unconditionally. If dst exists, compares
    the two with ``pick_best`` and overwrites dst only when src wins.
    Returns True on success.
    """
    try:
        if not os.path.exists(src):
            raise ImgRoyaleError(f"Source image does not exist: {src}")

        if not os.path.exists(dst):
            debug(dst, "New image; nothing to compare")
            success = copy(src, dst)
            if not success:
                raise ImgRoyaleError(f"Failed to copy: {src} to {dst}")
            return success

        best = pick_best(src, dst)
        if best == src:
            success = copy(src, dst)
            if not success:
                raise ImgRoyaleError(f"Failed to copy: {src} to {dst}")
            return success
        return True

    except ImgRoyaleError:
        raise
    except Exception as e:
        raise ImgRoyaleError(f"[save_best] Failed: {src} -> {dst} [{e}]")


def dedupe_image(
    in_file: str, out_dir: str, scratch_dir: str, del_scratch_dir: bool = False
) -> str:
    """Deduplicate an image by converting it to WebP and storing it by hash.

    Converts ``in_file`` to WebP in ``scratch_dir``, computes its perceptual
    hash, then calls ``save_best`` to write or replace the file at the
    hash-derived path inside ``out_dir``. The scratch WebP is removed after
    the operation. Returns the destination path on success, or ``in_file`` if
    the copy step fails.
    """
    try:
        if not os.path.exists(in_file):
            raise ImgRoyaleError(f"Missing image source: {in_file}")
        create_path(out_dir)
        create_path(scratch_dir)
        webp = slash_nix(to_webp(in_file, out_dir=scratch_dir))
        phash = perceptual_hash(webp)
        dst_path = slash_nix(os.path.join(out_dir, f"{format_hash(phash)}.webp"))
        success = save_best(webp, dst_path)
        if os.path.dirname(webp) == slash_nix(os.path.normpath(scratch_dir)):
            os.remove(webp)
        if (
            del_scratch_dir
            and os.path.isdir(scratch_dir)
            and not os.listdir(scratch_dir)
        ):
            os.rmdir(scratch_dir)
        if not success:
            raise ImgRoyaleWarning(f"Failed to save best image in: {dst_path}")
        return dst_path
    except ImgRoyaleError:
        raise
    except Exception as e:
        raise ImgRoyaleError(f"[dedupe_image] Failed: {in_file} -> {out_dir} [{e}]")
