
import ee
import geemap.foliumap as geemap
from folium import plugins
import os


def create_map_html(date1, date2=None, mode="range", center=None, zoom=None, output_file="temp_map.html"):
    if mode == "range":
        s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterDate(date1, date2).filter(
            ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)).median()
    else:
        t = ee.Date(date1)
        s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterDate(t.advance(-15, 'day'),
                                                                          t.advance(15, 'day')).median()

    # Use stored view if available, otherwise default to Turkey
    map_center = center if center else [39.0, 35.0]
    map_zoom = zoom if zoom else 6

    m = geemap.Map(center=map_center, zoom=map_zoom, tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
                   attr="Google Hybrid")

    draw = plugins.Draw(export=False, position='topleft',
                        draw_options={'polyline': False, 'circle': False, 'marker': False, 'circlemarker': False},
                        edit_options={'edit': False})
    draw.add_to(m)
    m.save(output_file)

    js = """
    <style>
    #btnExitView {
        position: absolute;
        bottom: 30px;
        left: 50%;
        transform: translateX(-50%);
        background-color: #D32F2F;
        color: white;
        font-size: 16px;
        font-weight: bold;
        padding: 10px 25px;
        border: none;
        border-radius: 8px;
        z-index: 9999;
        cursor: pointer;
        box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        display: none;
    }
    #btnExitView:hover {
        background-color: #B71C1C;
    }
    </style>
    <button id="btnExitView" onclick="exitSavedView()">Alan Görünümünden Çık</button>
    <script>
    document.addEventListener("DOMContentLoaded", function() {
        var mapInstance = null;
        var attempts = 0;
        var viewDebounceTimer = null;

        function findMap() {
            var found = false;
            for(var k in window){
                if(window[k] && window[k].on && window[k].addLayer && window[k].dragging){
                    var map = window[k];
                    mapInstance = map;
                    mapInstance = map;
                    console.log("Map Found!");
                    // alert("DEBUG: Map Found!");

                    // --- NEW: Track Map Movement with JS Debounce ---
                    map.on('movestart', function() {
                        clearTimeout(viewDebounceTimer);
                        document.title = "MOVING";
                    });

                    map.on('moveend', function() {
                        clearTimeout(viewDebounceTimer);
                        viewDebounceTimer = setTimeout(function() {
                            var center = map.getCenter();
                            var zoom = map.getZoom();
                            // Send view state to Python via title after 3s stability
                            document.title = "VIEW:" + center.lat + "," + center.lng + "," + zoom;
                        }, 3000);
                    });

                    map.on(L.Draw.Event.CREATED, function(e){
                        var layer = e.layer;
                        var geojson = layer.toGeoJSON();
                        document.title = "GEOJSON:" + JSON.stringify(geojson);
                        map.addLayer(layer);
                    });
                    map.on(L.Draw.Event.DELETED, function(e){
                        document.title = "RESET";
                    });
                    found = true;
                    break;
                }
            }
            if(!found && attempts < 20) {
                attempts++;
                setTimeout(findMap, 500);
            }
        }
        findMap();
        window.flyToLocation = function(lat, lon, zoom) {
            if (mapInstance) {
                var z = zoom || 12;
                mapInstance.flyTo([lat, lon], z, {animate: true, duration: 1.5});
            }
        };

        // --- NEW: Show Saved Polygon & Zoom ---
        window.showSavedGeometry = function(geojson) {
            if (mapInstance) {
                try {
                    // Clear existing manually drawn layer if strict needed, but here we add "Saved View"
                    if (window.savedLayer) {
                        mapInstance.removeLayer(window.savedLayer);
                    }

                    window.savedLayer = L.geoJSON(geojson, {
                        style: {color: "#3388ff", weight: 3, opacity: 1, fillOpacity: 0.2}
                    });
                    window.savedLayer.addTo(mapInstance);
                    mapInstance.fitBounds(window.savedLayer.getBounds());

                    // Show Exit Button
                    var btn = document.getElementById('btnExitView');
                    if(btn) btn.style.display = 'block';

                } catch(e) {
                     console.error("Error showing geometry: " + e);
                }
            }
        };

        // --- NEW: Exit Saved View ---
        window.exitSavedView = function() {
            if (mapInstance) {
                if (window.savedLayer) {
                    mapInstance.removeLayer(window.savedLayer);
                    window.savedLayer = null;
                }
                var btn = document.getElementById('btnExitView');
                if(btn) btn.style.display = 'none';

                document.title = "EXIT_VIEW";
            }
        };

        // --- NEW: Sentinel Layer Management ---
        window.sentinelLayer = null;

        window.addSentinelLayer = function(url, opacity) {
            if (mapInstance) {
                if (window.sentinelLayer) {
                    mapInstance.removeLayer(window.sentinelLayer);
                }
                var op = opacity !== undefined ? opacity : 1.0;
                window.sentinelLayer = L.tileLayer(url, {
                    attribution: 'Sentinel-2',
                    opacity: op,
                    maxZoom: 18
                });
                window.sentinelLayer.addTo(mapInstance);

                console.log("Sentinel Layer Added: " + url + " Opacity: " + op);
            }
        };

        window.removeSentinelLayer = function() {
            if (mapInstance && window.sentinelLayer) {
                mapInstance.removeLayer(window.sentinelLayer);
                window.sentinelLayer = null;
                console.log("Sentinel Layer Removed");
            }
        };
    });
    </script>
    """
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            content = f.read()
        if "</body>" in content:
            new_content = content.replace("</body>", js + "</body>")
        else:
            new_content = content + js
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(new_content)
    except Exception as e:
        print(f"Map file error: {e}")




