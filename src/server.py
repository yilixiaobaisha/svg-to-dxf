from __future__ import print_function
import web
import StringIO
from version import version as api_version
from svg_to_dxf import convert as std_convert

urls = (
    '/', 'convert_svg'
)


class convert_svg(object):
    def POST(self):
        try:
            svg = web.data()

            if svg:
                svg_in = StringIO.StringIO(svg)
                dxf_out = StringIO.StringIO()
                std_convert(svg_in, dxf_out, None)

            web.header("Content-Type", "application/dxf")
            web.header("Service-Version", api_version)
            return dxf_out.getvalue()
        except Exception, e:
            print(e)


if __name__ == "__main__":
    app = web.application(urls, globals())
    app.run()
