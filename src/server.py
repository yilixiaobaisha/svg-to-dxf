from __future__ import print_function
import sys
import web
import StringIO
from version import version as api_version
from svg_to_dxf import convert as std_convert

urls = (
    '/', 'convert_svg'
)


class convert_svg(object):
    def _common(self):
        # web.header("Access-Control-Allow-Origin", "*")
        return

    def GET(self):
        self._common()
        return api_version

    def POST(self):
        self._common()
        try:
            svg = web.data()
            layer_to_style = self._parse_layer_styles()

            if svg:
                svg_in = StringIO.StringIO(svg)
                dxf_out = StringIO.StringIO()
                std_convert(svg_in=svg_in, dxf_out=dxf_out, layer_to_style=layer_to_style, debug_out=None)
                web.header("Content-Type", "application/dxf")
                web.header("Service-Version", api_version)
                return dxf_out.getvalue()
            else:
                return ""

        except Exception, e:
            print(str(e), file=sys.stderr)
            return web.internalerror(str(e))

    # noinspection PyMethodMayBeStatic
    def _parse_layer_styles(self):
        layer_to_style = {}
        for layer, s in web.input().items():
            layer_styles = [e.strip() for e in s.split(',') if e.strip()]
            if layer_styles:
                layer_to_style[layer] = {}
                for layer_style in layer_styles:
                    layer_style = layer_style.split(":")
                    if len(layer_style) == 2:
                        style, style_value = layer_style[0], layer_style[1]
                        layer_to_style[layer][style] = style_value
        return layer_to_style


if __name__ == "__main__":
    app = web.application(urls, globals())
    app.run()
