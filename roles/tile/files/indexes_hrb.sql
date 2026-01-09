-- These are indexes for rendering performance with OpenStreetMap Carto.
-- This file is generated with scripts/indexes.py
CREATE INDEX view_osmhrb_line_label ON planet_osm_line USING GIST (way) WHERE COALESCE(tags->'name:hsb',tags->'name:dsb',name) IS NOT NULL OR ref IS NOT NULL;
CREATE INDEX view_osmhrb_point_place ON planet_osm_point USING GIST (way) WHERE place IS NOT NULL AND COALESCE(tags->'name:hsb',tags->'name:dsb',name) IS NOT NULL;
CREATE INDEX view_osmhrb_polygon_admin ON planet_osm_polygon USING GIST (ST_PointOnSurface(way)) WHERE COALESCE(tags->'name:hsb',tags->'name:dsb',name) IS NOT NULL AND boundary = 'administrative' AND admin_level IN ('0', '1', '2', '3', '4');
CREATE INDEX view_osmhrb_polygon_name ON planet_osm_polygon USING GIST (ST_PointOnSurface(way)) WHERE COALESCE(tags->'name:hsb',tags->'name:dsb',name) IS NOT NULL;
CREATE INDEX view_osmhrb_polygon_name_z6 ON planet_osm_polygon USING GIST (ST_PointOnSurface(way)) WHERE COALESCE(tags->'name:hsb',tags->'name:dsb',name) IS NOT NULL AND way_area > 5980000;
