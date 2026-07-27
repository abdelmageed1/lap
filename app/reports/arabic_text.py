"""Arabic script needs letter-joining reshaping and right-to-left reordering before it can be drawn
by ReportLab (which, unlike a Qt/browser text layout engine, draws raw Unicode codepoints left-to-right
with no shaping). arabic_reshaper + python-bidi give the same visual correctness Word/Qt provide natively."""
import arabic_reshaper
from bidi.algorithm import get_display


def shape(text) -> str:
    if text is None:
        return ""
    text = str(text)
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)
