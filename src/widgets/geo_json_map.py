from gi.repository import GObject, Gtk, Shumate, Gdk
from ..utils.utilities import format_json
import json

class GeoJsonMap(Shumate.SimpleMap):
    __gtype_name__ = "GeoJsonMap"

    def __init__(self):
        super().__init__()
        registry = Shumate.MapSourceRegistry.new()
        registry.populate_defaults()
        source = registry.get_by_id(Shumate.MAP_SOURCE_OSM_MAPNIK)
        if source is None:
            raise RuntimeError("Could not find OSM Mapnik source")

        self.set_map_source(source)
        self.viewport = self.get_viewport()
        self.marker_layer = Shumate.MarkerLayer.new(self.viewport)
        self.add_overlay_layer(self.marker_layer)
        self.path_layers = []

        # Default styles
        self.default_styles = {
            "marker": {
                "icon": "mark-location-symbolic",
                "color": "#c01c28",
                "scale": 1.0
            },
            "line": {
                "color": "#0077ff",
                "width": 3.0,
                "opacity": 1.0,
                "dash": None
            },
            "polygon": {
                "fill_color": "#ff7700",
                "stroke_color": "#ff7700",
                "stroke_width": 2.0,
                "fill_opacity": 0.3,
                "stroke_opacity": 1.0
            }
        }

    def parse_color(self, color_str, default_color):
        """Parse color string and return Gdk.RGBA"""

        if not color_str:
            color_str = default_color
        rgba = Gdk.RGBA()
        rgba.parse(color_str)
        return rgba

    def get_feature_styles(self, feature):
        """Extract styles from feature properties"""

        properties = feature.get("properties", {})
        style = properties.get("style", {})

        if isinstance(style, str):
            try:
                style = json.loads(style)
            except json.JSONDecodeError:
                style = {}

        return style

    def parse(self, json_string):
        """Create new map from geo json"""

        try:
            geo_json = json.loads(format_json(json_string))
        except Exception as e:
            print(e)
            return

        if geo_json.get("type") == "FeatureCollection":
            features = geo_json.get("features", [])
        else:
            features = [geo_json]

        for feature in features:
            feature_type = feature.get("type")
            style = self.get_feature_styles(feature)
            match feature_type:
                case "Feature":
                    self.parse_geometry(feature.get("geometry", {}), style)
                case "GeometryCollection":
                    for geometry in feature.get("geometries", []):
                        self.parse_geometry(geometry, style)
                case _:
                    print(f"Unsupported feature type: {geometry_type}")

    def parse_geometry(self, geometry, style):
        """Parses a geometry"""

        geometry_type = geometry.get("type")
        coordinates = geometry.get("coordinates")

        match geometry_type:
            case "Point":
                self.add_point(*coordinates, style)
            case "MultiPoint":
                for coords in coordinates:
                    self.add_point(*coords, style)
            case "LineString":
                self.add_line(coordinates, style)
            case "MultiLineString":
                for line in coordinates:
                    self.add_line(line, style)
            case "Polygon":
                self.add_polygon(coordinates, style)
            case "MultiPolygon":
                for polygon in coordinates:
                    self.add_polygon(polygon, style)
            case _:
                print(f"Unsupported geometry type: {geometry_type}")

    def add_point(self, longitude, latitude, style=None):
        """Adds a point to the map"""

        marker = self.get_marker(style)
        marker.set_location(longitude, latitude)
        self.marker_layer.add_marker(marker)

    def add_line(self, coordinates, style=None):
        """Adds a line made from coordinates points"""

        path_layer = Shumate.PathLayer.new(self.viewport)
        self.path_layers.append(path_layer)

        # Apply line styles
        line_style = {**self.default_styles["line"]}
        if style and "line" in style:
            line_style.update(style["line"])

        # Set color and opacity
        rgba = self.parse_color(
            line_style["color"], self.default_styles["line"]["color"])
        rgba.alpha = float(line_style.get("opacity", 1.0))
        path_layer.set_stroke_color(rgba)

        # Set width
        path_layer.set_stroke_width(
            float(line_style.get(
                "width", self.default_styles["line"]["width"])))

        # Set dash pattern if specified
        if line_style.get("dash"):
            path_layer.set_dash(line_style["dash"])

        for lon, lat in coordinates:
            position = Shumate.Coordinate.new()
            position.set_location(lat, lon)
            path_layer.add_node(position)

        self.add_overlay_layer(path_layer)

    def add_polygon(self, rings, style=None):
        """Adds a polygon"""

        polygon_style = {**self.default_styles["polygon"]}
        if style and "polygon" in style:
            polygon_style.update(style["polygon"])

        if len(rings) != 0:
            path_layer = Shumate.PathLayer.new(self.viewport)
            self.path_layers.append(path_layer)

            # Set fill color and opacity
            fill_rgba = self.parse_color(
                polygon_style.get("fill_color"),
                self.default_styles["polygon"]["fill_color"])
            fill_rgba.alpha = float(polygon_style.get("fill_opacity", 0.3))
            path_layer.set_fill(True)
            path_layer.set_fill_color(fill_rgba)

            # Set stroke color and opacity
            stroke_rgba = self.parse_color(
                polygon_style.get("stroke_color"),
                self.default_styles["polygon"]["stroke_color"])
            stroke_rgba.alpha = float(polygon_style.get("stroke_opacity", 1.0))
            path_layer.set_stroke_color(stroke_rgba)

            # Set stroke width
            path_layer.set_stroke_width(
                float(polygon_style.get(
                        "stroke_width",
                        self.default_styles["polygon"]["stroke_width"])))
            path_layer.set_closed(True)

        for i, ring in enumerate(rings):
            for lon, lat in ring:
                position = Shumate.Coordinate.new()
                position.set_location(lat, lon)
                path_layer.add_node(position)

            self.add_overlay_layer(path_layer)

    def get_marker(self, style=None):
        marker_style = {**self.default_styles["marker"]}
        if style and "marker" in style:
            marker_style.update(style["marker"])

        marker = Shumate.Marker()
        marker_img = Gtk.Image.new_from_icon_name("mark-location-symbolic")
        marker_img.add_css_class("map-pin")
        marker_img.set_icon_size(Gtk.IconSize.NORMAL)

        if "color" in marker_style:
            context = marker_img.get_style_context()
            css_provider = Gtk.CssProvider()
            css = f'.map-pin {{ color: {marker_style["color"]}; }}'
            css_provider.load_from_data(css.encode())
            context.add_provider(
                css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        marker.set_child(marker_img)
        return marker
