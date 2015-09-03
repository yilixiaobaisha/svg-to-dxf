from __future__ import print_function
import pysvg.parser
from pysvg.core import TextContent
import pysvg.structure as structure
import pysvg.shape as shape
import svg.path as path
import ezdxf
import transform as x
import math

# noinspection PyUnusedLocal
def _noop(*args, **kwargs):
    pass


def _complex_to_2tuple(c, transform=x.IDENTITY):
    return transform.mult_point((c.real, c.imag))


def _complex_to_3tuple(c, transform=x.IDENTITY):
    return transform.mult_point((c.real, c.imag, 0))


def _convert_line_to_path(line):
    aspath = shape.Path(style=line.get_style())
    aspath.appendMoveToPath(float(line.get_x1()), float(line.get_y1()), relative=False)
    aspath.appendLineToPath(float(line.get_x2()), float(line.get_y2()), relative=False)
    return aspath


def _convert_rect_to_path(rect):
    if not rect.get_x():
        rect.set_x(0)
    if not rect.get_y():
        rect.set_y(0)
    aspath = shape.Path(style=rect.get_style())
    edgePoints = rect.getEdgePoints()
    aspath.appendMoveToPath(edgePoints[-1][0], edgePoints[-1][1], relative=False)
    for p in rect.getEdgePoints():
        aspath.appendLineToPath(p[0], p[1], relative=False)
    return aspath


def _convert_polygon_to_path(polyline):
    aspath = shape.Path(style=polyline.get_style())
    points = [p.split(",") for p in polyline.get_points().split(" ")]
    aspath.appendMoveToPath(points[-1][0], points[-1][1], relative=False)
    for p in points:
        aspath.appendLineToPath(p[0], p[1], relative=False)
    return aspath


def _convert_polyline_to_path(polyline):
    aspath = shape.Path(style=polyline.get_style())
    points = [p.split(",") for p in polyline.get_points().split(" ")]
    aspath.appendMoveToPath(points[0][0], points[0][1], relative=False)
    for p in points[1:]:
        aspath.appendLineToPath(p[0], p[1], relative=False)
    return aspath


def _cubic_approx_ellipse(cx, cy, rx, ry):
    control_offsetx = rx * 0.55228
    control_offsety = ry * 0.55228
    aspath = shape.Path()
    aspath.appendMoveToPath(cx - rx, cy, relative=False)
    aspath.appendCubicCurveToPath(cx - rx, cy - control_offsety,
                                  cx - control_offsetx,
                                  cy - ry, cx,
                                  cy - ry,
                                  relative=False)
    aspath.appendCubicCurveToPath(cx + control_offsetx, cy - ry,
                                  cx + rx, cy - control_offsety,
                                  cx + rx, cy,
                                  relative=False)
    aspath.appendCubicCurveToPath(cx + rx, cy + control_offsety,
                                  cx + control_offsetx, cy + ry,
                                  cx, cy + ry,
                                  relative=False)
    aspath.appendCubicCurveToPath(cx - control_offsetx, cy + ry,
                                  cx - rx, cy + control_offsety,
                                  cx - rx, cy,
                                  relative=False)
    return aspath


def _convert_ellipse_to_path(element):
    if not element.get_cx():
        element.set_cx(0)
    if not element.get_cy():
        element.set_cy(0)
    cx = float(element.get_cx())
    cy = float(element.get_cy())
    rx = float(element.get_rx())
    ry = float(element.get_ry())
    aspath = _cubic_approx_ellipse(cx, cy, rx, ry)
    aspath.set_style(element.get_style())
    return aspath


def _convert_circle_to_path(element):
    if not element.get_cx():
        element.set_cx(0)
    if not element.get_cy():
        element.set_cy(0)

    cx = float(element.get_cx())
    cy = float(element.get_cy())
    r = float(element.get_r())
    aspath = _cubic_approx_ellipse(cx, cy, r, r)
    aspath.set_style(element.get_style())
    return aspath


def __append_path_to_dxf(element, msp, debug, transform):
    parsed = path.parser.parse_path(element.get_d())
    for segment in parsed:
        debug(segment)
        if isinstance(segment, path.Line):
            start = _complex_to_2tuple(segment.start, transform)
            end = _complex_to_2tuple(segment.end, transform)
            msp.add_line(start=start, end=end)

        elif isinstance(segment, path.QuadraticBezier):
            start = _complex_to_3tuple(segment.start, transform)
            control = _complex_to_3tuple(segment.control, transform)
            end = _complex_to_3tuple(segment.end, transform)

            spline = msp.add_spline()
            spline.set_control_points((start, control, control, end))
            spline.set_knot_values((0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0))

        elif isinstance(segment, path.CubicBezier):
            start = _complex_to_3tuple(segment.start, transform)
            control1 = _complex_to_3tuple(segment.control1, transform)
            control2 = _complex_to_3tuple(segment.control2, transform)
            end = _complex_to_3tuple(segment.end, transform)

            spline = msp.add_spline()
            spline.set_control_points((start, control1, control2, end))
            spline.set_knot_values((0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0))

        else:
            debug(segment)


def _convert_element(element, msp, debug, transform):
    if hasattr(element, 'get_transform') and element.get_transform():
        transform = transform.mult(x.parse(element.get_transform()))

    if isinstance(element, structure.G):
        _append_subelements(element, msp, debug, transform)

    elif isinstance(element, shape.Path):
        __append_path_to_dxf(element, msp, debug, transform)

    elif isinstance(element, shape.Line):
        aspath = _convert_line_to_path(element)
        __append_path_to_dxf(aspath, msp, debug, transform)

    elif isinstance(element, shape.Rect):
        aspath = _convert_rect_to_path(element)
        __append_path_to_dxf(aspath, msp, debug, transform)

    elif isinstance(element, shape.Polygon):
        aspath = _convert_polygon_to_path(element)
        __append_path_to_dxf(aspath, msp, debug, transform)

    elif isinstance(element, shape.Polyline):
        aspath = _convert_polyline_to_path(element)
        __append_path_to_dxf(aspath, msp, debug, transform)

    elif isinstance(element, shape.Circle):
        aspath = _convert_circle_to_path(element)
        __append_path_to_dxf(aspath, msp, debug, transform)

    elif isinstance(element, shape.Ellipse):
        aspath = _convert_ellipse_to_path(element)
        __append_path_to_dxf(aspath, msp, debug, transform)

    elif isinstance(element, TextContent):
        pass

    else:
        debug(element)


def _append_subelements(element, msp, debug, transform):
    for e in element.getAllElements():
        _convert_element(e, msp, debug, transform)


def convert(svg_in, dxf_out, debug_out=None):
    svg = pysvg.parser.parse(svg_in)
    dwg = ezdxf.new('AC1027')
    msp = dwg.modelspace()

    if debug_out is not None:
        debug = lambda *objects: print(*objects, file=debug_out)
    else:
        debug = _noop

    _append_subelements(svg, msp, debug, x.matrix(1, 0, 0, -1, 0, 0))

    dwg.write(dxf_out)
