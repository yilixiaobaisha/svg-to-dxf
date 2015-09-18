from __future__ import print_function, division
import math
from contextlib import contextmanager
import sys
import os

import pysvg.parser
from pysvg.core import TextContent
import pysvg.structure as structure
import pysvg.shape as shape
import svg.path as path
import ezdxf

import transform as transform
import colortrans


@contextmanager
def stdout_ignore():
    old_stdout = sys.stdout
    sys.stdout = open(os.devnull, "w")
    try:
        yield
    finally:
        sys.stdout.close()
        sys.stdout = old_stdout


# noinspection PyUnusedLocal
def _noop(*args, **kwargs):
    pass


def _complex_to_2tuple(c, transform_=transform.IDENTITY):
    return transform_.mult_point((c.real, c.imag))


def _complex_to_3tuple(c, transform_=transform.IDENTITY):
    return transform_.mult_point((c.real, c.imag, 0))


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


def _point_on_arc(theta, c, r):
    return complex(math.cos(math.radians(theta)) * r.real + c.real, math.sin(math.radians(theta)) * r.imag + c.imag)


def __append_path_to_dxf(element, msp, debug, context):
    parsed = path.parser.parse_path(element.get_d())

    for segment in parsed:
        if isinstance(segment, path.Line):
            start = _complex_to_2tuple(segment.start, context.transform)
            end = _complex_to_2tuple(segment.end, context.transform)
            line = msp.add_line(start=start, end=end)
            line.set_dxf_attrib('layer', context.layer)

        elif isinstance(segment, path.QuadraticBezier):
            start = _complex_to_3tuple(segment.start, context.transform)
            control = _complex_to_3tuple(segment.control, context.transform)
            end = _complex_to_3tuple(segment.end, context.transform)

            spline = msp.add_spline()
            spline.set_control_points((start, control, control, end))
            spline.set_knot_values((0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0))
            spline.set_dxf_attrib('layer', context.layer)

        elif isinstance(segment, path.CubicBezier):
            start = _complex_to_3tuple(segment.start, context.transform)
            control1 = _complex_to_3tuple(segment.control1, context.transform)
            control2 = _complex_to_3tuple(segment.control2, context.transform)
            end = _complex_to_3tuple(segment.end, context.transform)

            spline = msp.add_spline()
            spline.set_control_points((start, control1, control2, end))
            spline.set_knot_values((0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0))
            spline.set_dxf_attrib('layer', context.layer)

        elif isinstance(segment, path.Arc):
            num_segments = int(math.ceil(math.fabs(segment.delta) / 30.0))
            delta_segment_inc = segment.delta / num_segments

            def point_on_arc(theta):
                return _point_on_arc(theta, segment.center, segment.radius)

            for segment_index in range(0, num_segments):
                segment_mults = [segment_index, segment_index + 1 / 3, segment_index + 2 / 3, segment_index + 1]
                segment_angles = [segment.theta + delta_segment_inc * x for x in
                                  segment_mults]
                fit_points = [_complex_to_3tuple(point_on_arc(a), context.transform) for a in segment_angles]
                if segment_index == 0:
                    fit_points[0] = _complex_to_3tuple(segment.start, context.transform)

                if segment == num_segments - 1:
                    fit_points[-1] = _complex_to_3tuple(segment.end, context.transform)

                # msp.add_spline(fit_points=fit_points)
                line = msp.add_lwpolyline(points=fit_points)  # todo use splines
                line.set_dxf_attrib('layer', context.layer)

        else:
            debug(segment)


def _append_element(element, msp, debug, context):
    if isinstance(element, structure.G):
        _append_subelements(element, msp, debug, context)

    elif isinstance(element, shape.Path):
        __append_path_to_dxf(element, msp, debug, context)

    elif isinstance(element, shape.Line):
        aspath = _convert_line_to_path(element)
        __append_path_to_dxf(aspath, msp, debug, context)

    elif isinstance(element, shape.Rect):
        aspath = _convert_rect_to_path(element)
        __append_path_to_dxf(aspath, msp, debug, context)

    elif isinstance(element, shape.Polygon):
        aspath = _convert_polygon_to_path(element)
        __append_path_to_dxf(aspath, msp, debug, context)

    elif isinstance(element, shape.Polyline):
        aspath = _convert_polyline_to_path(element)
        __append_path_to_dxf(aspath, msp, debug, context)

    elif isinstance(element, shape.Circle):
        aspath = _convert_circle_to_path(element)
        __append_path_to_dxf(aspath, msp, debug, context)

    elif isinstance(element, shape.Ellipse):
        aspath = _convert_ellipse_to_path(element)
        __append_path_to_dxf(aspath, msp, debug, context)

    elif isinstance(element, TextContent):
        pass

    else:
        debug(element)


def _append_subelements(element, msp, debug, context):
    for e in element.getAllElements():
        _append_element(e, msp, debug, context.element(e))


__units = {
    "unitless": 0,
    "in": 1,
    "ft": 2,
    "mi": 3,
    "mm": 4,

}


class ElementContext(object):
    def __init__(self, transform_=transform.IDENTITY, layer='default'):
        self.transform = transform_
        self.layer = layer

    # noinspection PyProtectedMember
    def element(self, element):
        transform_ = self.transform
        if hasattr(element, 'get_transform') and element.get_transform():
            transform_ = transform_.mult(transform.parse(element.get_transform()))

        layer = 'default'
        if hasattr(element, 'getAttribute') and element.get_class():
            classes = element.get_class().split(" ")
            for class_ in classes:
                if class_.startswith('dxf-layer-'):
                    layer = class_[len('dxf-layer-'):].strip()
                    break

        return ElementContext(transform_, layer)


def create_layers(dwg, layer_to_style):
    if layer_to_style is None:
        layer_to_style = {}

    if 'default' not in layer_to_style:
        layer_to_style['default'] = {'color': '#000000'}

    for name, styles in layer_to_style.items():
        layer = dwg.layers.create(name=name, dxfattribs={})
        if 'color' in styles:
            layer.set_color(colortrans.rgb2short(styles['color']))


def convert(svg_in, dxf_out, layer_to_style=None, debug_out=None):
    if debug_out is not None:
        debug = lambda *objects: print(*objects, file=debug_out)
    else:
        debug = _noop

    with stdout_ignore():
        svg = pysvg.parser.parse(svg_in)
    dwg = ezdxf.new('AC1015')
    create_layers(dwg, layer_to_style)

    msp = dwg.modelspace()
    transform_ = transform.matrix(1, 0, 0, -1, 0, 0)
    context = ElementContext(transform_=transform_).element(svg)
    _append_subelements(svg, msp, debug, context)

    dwg.write(dxf_out)
