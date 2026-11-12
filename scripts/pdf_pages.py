"""Images made from a PDF: every page, or one region of a page.

The only module that opens a PDF. It draws pages and reads no text out of them: the
text of a PDF input is transcribed by an agent (`prompts/roles/transcriber.md`).
Another renderer can replace this one without changing the convert script.
"""
from __future__ import annotations

from pathlib import Path

import pypdfium2

from paper_model import ConversionError

POINTS_PER_INCH = 72
# A page image: 200 pixels to the inch, at which a table's values and a plot's axis
# labels can be read on a page of ordinary size.
PAGE_DPI = 200
# A region: 300 pixels to the inch or more, and enough for its longer side to have
# MIN_PIXELS, so that a small figure still shows its point markers.
REGION_DPI = 300
REGION_MIN_PIXELS = 2400
# No image has a side longer than this.
MAX_PIXELS = 8000


def _open(pdf: Path) -> pypdfium2.PdfDocument:
    try:
        return pypdfium2.PdfDocument(str(pdf))
    except (pypdfium2.PdfiumError, OSError) as error:
        raise ConversionError(f"the PDF {pdf} could not be read ({error})") from error


def page_count(pdf: Path) -> int:
    document = _open(pdf)
    try:
        return len(document)
    finally:
        document.close()


def write_pages(pdf: Path, folder: Path) -> int:
    """Write every page of `pdf` into `folder` as page-001.png, page-002.png and so on. Return how many."""
    document = _open(pdf)
    try:
        for number, page in enumerate(document, start=1):
            scale = min(PAGE_DPI / POINTS_PER_INCH, MAX_PIXELS / max(page.get_size()))
            page.render(scale=scale).to_pil().convert("RGB").save(folder / f"page-{number:03d}.png")
        return len(document)
    finally:
        document.close()


def write_region(pdf: Path, page_number: int, box: tuple[float, float, float, float], target: Path) -> tuple[int, int]:
    """Write a region of one page of `pdf` to `target`, and return the image's width and height.

    `page_number` counts from 1. `box` is (left, top, right, bottom), each a fraction of
    the page's width or height measured from its top left corner; (0, 0, 1, 1) is the
    whole page.
    """
    document = _open(pdf)
    try:
        if not 1 <= page_number <= len(document):
            raise ConversionError(f"the PDF has {len(document)} pages; there is no page {page_number}")
        page = document[page_number - 1]
        width, height = page.get_size()
        left, top, right, bottom = box
        longer = max((right - left) * width, (bottom - top) * height)
        scale = min(max(REGION_DPI / POINTS_PER_INCH, REGION_MIN_PIXELS / longer), MAX_PIXELS / longer)
        # What is cut off each border of the page, in points: left, bottom, right, top.
        crop = (left * width, (1 - bottom) * height, (1 - right) * width, top * height)
        image = page.render(scale=scale, crop=crop).to_pil().convert("RGB")
        image.save(target)
        return image.size
    finally:
        document.close()
