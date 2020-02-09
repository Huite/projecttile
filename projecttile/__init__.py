"""
WebMapTileService tile utilities

Based the mercantile package: https://github.com/mapbox/mercantile
Which has the following copyright statement and BSD license:


    Copyright (c) 2014-2017, Sean C. Gillies
    All rights reserved.
    
    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:
    
        * Redistributions of source code must retain the above copyright
        notice, this list of conditions and the following disclaimer.
        * Redistributions in binary form must reproduce the above copyright
        notice, this list of conditions and the following disclaimer in the
        documentation and/or other materials provided with the distribution.
        * Neither the name of Sean C. Gillies nor the names of
        its contributors may be used to endorse or promote products derived from
        this software without specific prior written permission.
    
    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
    AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
    IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
    ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
    LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
    CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
    SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
    INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
    CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
    ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
    POSSIBILITY OF SUCH DAMAGE.


"""

from collections import namedtuple
from collections import defaultdict
import math
import sys
import warnings

if sys.version_info < (3,):
    from collections import Sequence
else:
    from collections.abc import Sequence


__version__ = "0.1"


class ProjecttileError(Exception):
    """Base exception"""


class TileArgParsingError(ProjecttileError):
    """Raised when errors occur in parsing a function's tile arg(s)"""


WMTSTile = namedtuple("Tile", ["x", "y", "z", "provider_bounds"])
"""An XYZ web mercator tile

Attributes
----------
x, y, z : int
    x and y indexes of the tile and zoom level z.
provider_bounds : Bbox
    Bounding boxes of the tile providing service.
"""


Bbox = namedtuple("Bbox", ["left", "bottom", "right", "top"])
"""A web mercator bounding box

Attributes
----------
left, bottom, right, top : float
    Bounding values in cartesian coordinates.
"""

XY = namedtuple("XY", ["x", "y"])
"""An x and y pair

Attributes
----------
x, y : float
    x and y in cartesian coordinates.
"""


def _parse_tile_arg(*args):
    if len(args) == 1:
        args = args[0]
    if len(args) == 4:
        return WMTSTile(*args)
    else:
        raise TileArgParsingError(
            "the tile argument may have 1 or 4 values. Note that zoom is a keyword-only argument"
        )


def ul(*tile):
    """Upper left of a tile, for WMTS"""
    tile = _parse_tile_arg(*tile)
    xtile, ytile, zoom, provider_bounds = tile
    left, bottom, right, top = provider_bounds
    n = 2.0 ** zoom
    tile_dx = (right - left) / n
    tile_dy = (top - bottom) / n
    x = left + (xtile * tile_dx)
    y = top - (ytile * tile_dy)
    return XY(x, y)


def truncate_xy(x, y, provider_bounds):
    left, bottom, right, top = provider_bounds
    if x > right:
        x = right
    elif x < left:
        x = left
    if y > top:
        y = top
    elif y < bottom:
        y = bottom
    return x, y


def bounds(*tile):
    """Returns the bounding box of a tile

    Parameters
    ----------
    tile : Tile or sequence of int
        May be be either an instance of Tile or 3 ints and provider bounding box, X, Y, Z, provider_bounds.

    Returns
    -------
    BBox

    """
    tile = _parse_tile_arg(*tile)
    xtile, ytile, zoom, provider_bounds = tile
    a = ul(xtile, ytile, zoom, provider_bounds)
    b = ul(xtile + 1, ytile + 1, zoom, provider_bounds)
    return Bbox(a[0], b[1], b[0], a[1])


def _tile(x, y, zoom, provider_bounds, truncate=False):
    """WMTS specific"""
    left, bottom, right, top = provider_bounds
    # TODO: check if inbounds
    n = 2.0 ** zoom
    tile_dx = (right - left) / n
    tile_dy = (top - bottom) / n
    xtile = (x - left) / tile_dx
    ytile = (top - y) / tile_dy
    return xtile, ytile, zoom


def tile(x, y, zoom, provider_bounds, truncate=False):
    xtile, ytile, zoom = _tile(x, y, zoom, provider_bounds, truncate=truncate)
    xtile = int(math.floor(xtile))
    ytile = int(math.floor(ytile))
    return WMTSTile(xtile, ytile, zoom, provider_bounds)


def tiles(west, south, east, north, zooms, provider_bounds, truncate=False):
    """Get the tiles overlapped by a geographic bounding box

    Parameters
    ----------
    west, south, east, north : sequence of float
        Bounding values in meters.
    zooms : int or sequence of int
        One or more zoom levels.
    provider_bounds : sequence of float
        Bounding values of the tile provider in meters.
    truncate : bool, optional
        Whether or not to truncate inputs to provider bound mercator limits.

    Yields
    ------
    Tile

    Notes
    -----
    A small epsilon is used on the south and east parameters so that this
    function yields exactly one tile when given the bounds of that same tile.

    """
    if truncate:
        west, south = truncate_xy(west, south, provider_bounds)
        east, north = truncate_xy(east, north, provider_bounds)
    else:
        bboxes = [(west, south, east, north)]

    left, bottom, right, top = provider_bounds

    for w, s, e, n in bboxes:

        # Clamp bounding values.
        w = max(left, w)
        s = max(bottom, s)
        e = min(right, e)
        n = min(top, n)

        if not isinstance(zooms, Sequence):
            zooms = [zooms]

        epsilon = 1.0e-9

        for z in zooms:
            llx, lly, llz = _tile(w, s, z, provider_bounds)

            if lly % 1 < epsilon / 10:
                lly = lly - epsilon

            urx, ury, urz = _tile(e, n, z, provider_bounds)
            if urx % 1 < epsilon / 10:
                urx = urx - epsilon

            # Clamp left x and top y at 0.
            llx = 0 if llx < 0 else llx
            ury = 0 if ury < 0 else ury

            llx, urx, lly, ury = map(lambda x: int(math.floor(x)), [llx, urx, lly, ury])

            for i in range(llx, min(urx + 1, 2 ** z)):
                for j in range(ury, min(lly + 1, 2 ** z)):
                    yield WMTSTile(i, j, z, provider_bounds)


def provider_bounds(bboxwgs84, crs):
    import pyproj
    n, e, s, w = bboxwgs84
    transformer = pyproj.Transformer.from_crs("EPSG:4326", crs)
    left, top = transformer.transform(w, n)
    right, bottom = transformer.transform(e, s)
    return Bbox(left, bottom, right, top)


def wmts_metadata(wmts_url):
    """Discover what's available"""
    from owslib.wmts import WebMapTileService
    wmts = WebMapTileService(wmts_url)
    
    tilematrixsets = {}
    for identifier, tilematrix in wmts.tilematrixsets.items():
        # Store information of identifier and associated crs
        zooms = [int(key) for key in tilematrix.tilematrix]
        tilematrixsets[identifier] = {
            "crs" : tilematrix.crs,
            "min_zoom" : min(zooms),
            "max_zoom" : max(zooms),
        }
    
    provider_metadata = {}
    for name, variant in wmts.contents.items():
        d = defaultdict(list)

        for attribute in ("formats", "layers"):
            for key in getattr(variant, attribute):
                d[attribute].append(key)

        for style in variant.styles:
            if style is None:
                d["styles"].append("default")
            else:
                d["styles"].append(style)

        for url in variant.resourceURLs:
            d["url"].append(url["template"])
            
        for identifier in variant._tilematrixsets:
            d["tilematrixset"].append(identifier)
        
        d["bboxWGS84"] = variant.boundingBoxWGS84
        provider_metadata[name] = d

    return provider_metadata, tilematrixsets
