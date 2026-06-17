import numpy as np
from pathlib import Path

# from common.paths import X_BAND_DECODED_DIR

IMAGE_SHAPE = (3003, 3008)
ADC_OFFSET = 1024
FITS_BLOCK_SIZE = 2880


def read_bin(file_path, shape=IMAGE_SHAPE, offset=ADC_OFFSET):
    file_path = Path(file_path)
    expected_size = int(np.prod(shape))

    with file_path.open("rb") as file:
        array_data = np.fromfile(file, dtype=np.uint16)

    if array_data.size != expected_size:
        raise ValueError(
            f"Expected {expected_size} pixels for shape {shape}, "
            f"but {file_path} contains {array_data.size} pixels"
        )

    image = (array_data.astype(np.int32) - offset).astype(np.int16)
    image = image.reshape(shape)
    return image


def read_fits(file_path, ext=0, return_header=False):
    try:
        from astropy.io import fits
    except ImportError as exc:
        raise ImportError("read_fits requires astropy. Install it with `pip install astropy`.") from exc

    file_path = Path(file_path)
    with fits.open(file_path, memmap=False) as hdul:
        hdu = hdul[ext]
        if hdu.data is None:
            raise ValueError(f"No image data found in HDU {ext} of {file_path}")

        image = np.asarray(hdu.data)
        header = hdu.header.copy()

    if return_header:
        return image, header
    return image


def read_image(file_path):
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()

    if suffix == ".bin":
        return read_bin(file_path)
    if suffix in {".fits", ".fit", ".fts"}:
        return read_fits(file_path)

    raise ValueError(f"Unsupported image extension: {file_path.suffix}")


def _fits_card(keyword, value=None):
    if value is None:
        return keyword.ljust(80)

    if isinstance(value, bool):
        value_text = "T" if value else "F"
        return f"{keyword:<8}= {value_text:>20}".ljust(80)

    return f"{keyword:<8}= {value:>20}".ljust(80)


def _fits_header(shape):
    height, width = shape
    cards = [
        _fits_card("SIMPLE", True),
        _fits_card("BITPIX", 16),
        _fits_card("NAXIS", 2),
        _fits_card("NAXIS1", width),
        _fits_card("NAXIS2", height),
        _fits_card("BSCALE", 1),
        _fits_card("BZERO", 0),
        _fits_card("END"),
    ]
    header = "".join(cards).encode("ascii")
    padding = (-len(header)) % FITS_BLOCK_SIZE
    return header + (b" " * padding)



def save_bin_as_fits(bin_path, fits_path=None, shape=IMAGE_SHAPE, offset=ADC_OFFSET, overwrite=False):
    bin_path = Path(bin_path)
    if fits_path is None:
        fits_path = bin_path.with_suffix(".fits")

    image = read_bin(bin_path, shape=shape, offset=offset)
    return save_fits(image, fits_path, overwrite=overwrite)

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Read decoded X-band image data.")
    parser.add_argument("file_path")
    parser.add_argument("--show", action="store_true")
    args = parser.parse_args()

    image = read_image(args.file_path)
    print(f"shape={image.shape}, dtype={image.dtype}, min={image.min()}, max={image.max()}")

    if args.show:
        import matplotlib.pyplot as plt

        plt.imshow(image)
        plt.show()


if __name__ == '__main__':
    main()
