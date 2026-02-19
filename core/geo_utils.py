
import json

def parse_view_title(title):
    """
    Parses 'VIEW:lat,lon,zoom' string.
    Returns a dict {'center': [lat, lon], 'zoom': zoom} or None if failed.
    """
    if not title.startswith("VIEW:"):
        return None
    try:
        parts = title[5:].split(',')
        if len(parts) == 3:
            lat = float(parts[0])
            lng = float(parts[1])
            zoom = int(parts[2])
            return {'center': [lat, lng], 'zoom': zoom}
    except Exception as e:
        print(f"VIEW Parse Error: {e}")
    return None

def parse_geojson_title(title):
    """
    Parses 'GEOJSON:{...}' string.
    Returns the geometry dictionary or None.
    """
    if not title.startswith("GEOJSON:"):
        return None
    try:
        json_str = title[8:]
        raw_json = json.loads(json_str)
        if 'geometry' in raw_json:
            return raw_json['geometry']
        else:
            return raw_json
    except Exception as e:
        print(f"GEOJSON Parse Error: {e}")
    return None

def load_saved_location(app, record_data):
    """
    Navigates the map to the location stored in the record.
    'app' is the main application instance.
    """
    try:
        # Save current view state before navigation
        if app.last_map_view:
            app.pre_navigation_view = app.last_map_view.copy()

        geo = record_data.get("geometry")
        view = record_data.get("view")

        # 1. Try to use Geometry (Best for "Go to Area" as it shows the polygon)
        if geo:
            # Ensure geo is in JSON format
            if isinstance(geo, dict):
                json_str = json.dumps(geo)
            else:
                json_str = str(geo) 
            
            js = f"window.showSavedGeometry({json_str});"
            app.browser.page().runJavaScript(js)
            app.lbl_status.setText(f"Showing saved area...")
            return
        
        # 2. Fallback to View Center (Legacy or missing geometry)
        if view:
            center = view.get('center')
            zoom = view.get('zoom')
            if center:
                lat, lng = center
                zoom_val = zoom if zoom else 12
                js = f"window.flyToLocation({lat}, {lng}, {zoom_val});"
                app.browser.page().runJavaScript(js)
                app.lbl_status.setText(f"Moved to saved location ({lat:.4f}, {lng:.4f})")
                return

        app.lbl_status.setText(" Location data not found in this record.")

    except Exception as e:
        app.lbl_status.setText(f"Navigation Error: {e}")
