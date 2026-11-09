-- brightest color of each frame (NULL until the source is ingested / backfilled with it)

ALTER TABLE SourceFrame ADD COLUMN bright_r INTEGER;
ALTER TABLE SourceFrame ADD COLUMN bright_g INTEGER;
ALTER TABLE SourceFrame ADD COLUMN bright_b INTEGER;