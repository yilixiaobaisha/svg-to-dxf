import svg_to_dxf as std
import sys


if __name__ == "__main__":
    std.convert(svg_in=sys.stdin, dxf_out=sys.stdout, layer_to_style={}, debug_out=sys.stderr)
