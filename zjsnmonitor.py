"""
This example shows how one can add a custom contentview to mitmproxy.
The content view API is explained in the mitmproxy.contentviews module.
"""
from mitmproxy import contentviews
import zlib
import json


class ViewZjsn(contentviews.View):
    name = "zjsn"

    # We don't have a good solution for the keyboard shortcut yet -
    # you manually need to find a free letter. Contributions welcome :)
    content_types = ["application/octet-stream"]

    def __call__(self, data, **metadata):
        jp = json.loads(zlib.decompress(data).decode("utf8"))
        return "zjsn json body", contentviews.format_text(json.dumps(jp, sort_keys=True, indent=4, ensure_ascii=False))


view = ViewZjsn()


def load(l):
    contentviews.add(view)


def done():
    contentviews.remove(view)