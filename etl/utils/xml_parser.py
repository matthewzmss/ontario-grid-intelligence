"""
IESO XML parsing utilities.

IESO XML files use namespaces that vary between report types.
This module provides helpers to handle namespace detection and
streaming parsing for large XML files.
"""

from lxml import etree
from io import BytesIO


def get_namespace(xml_content: bytes) -> str:
    """
    Detect the XML namespace from an IESO XML file.

    Returns the namespace string wrapped in braces (e.g., '{http://...}')
    or empty string if no namespace is found.
    """
    try:
        # Parse just enough to get the root element
        for event, elem in etree.iterparse(BytesIO(xml_content), events=("start",)):
            nsmap = elem.nsmap
            if None in nsmap:
                return f"{{{nsmap[None]}}}"
            return ""
    except etree.XMLSyntaxError:
        return ""


def iter_elements(xml_content: bytes, tag: str):
    """
    Memory-efficient XML element iterator.

    Uses iterparse to stream through large XML files without
    loading the entire DOM into memory. Clears elements after
    processing to keep memory usage low.

    Args:
        xml_content: raw XML bytes
        tag: element tag name to find (without namespace)

    Yields:
        lxml Element objects matching the tag
    """
    ns = get_namespace(xml_content)
    full_tag = f"{ns}{tag}"

    for event, elem in etree.iterparse(BytesIO(xml_content), events=("end",), tag=full_tag):
        yield elem
        # Free memory — critical for 6.8MB+ XML files
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]


def find_text(element, tag: str, ns: str = "") -> str | None:
    """Find a child element and return its text, or None."""
    child = element.find(f"{ns}{tag}")
    return child.text.strip() if child is not None and child.text else None


def find_float(element, tag: str, ns: str = "") -> float | None:
    """Find a child element and return its text as float, or None."""
    text = find_text(element, tag, ns)
    if text is None:
        return None
    try:
        return float(text)
    except ValueError:
        return None
