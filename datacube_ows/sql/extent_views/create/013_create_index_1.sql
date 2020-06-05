-- Creating Materialised View Index 1/4

CREATE INDEX space_time_view_geom_idx
  ON space_time_view
  USING GIST (spatial_extent)
