from io import BytesIO
import sqlite3

import database

class Color:
    def __init__(self, r = 255, g = 255, b = 255):
        self.r = r
        self.g = g
        self.b = b

    def as_tuple(self):
        return (self.r, self.g, self.b)

class SourceKind:
    UNKNOWN : int = 0
    MOVIE : int = 1

class ColorMode:
    AVERAGE : int = 0   # mean color of the frame
    BRIGHTEST : int = 1 # brightest pixel of the frame (see ingester.py)

class Source:
    def __init__(self):
        self.id : int = 0
        self.sha512: str = ""
        self.imdb_id: str = ""
        self.kind: int = SourceKind.UNKNOWN
        self.metadata_name: str = ""
        self.metadata_year: int = 0

class SourceFrame: 
    def __init__(self):
        self.id : int = 0
        self.source_id : int = 0
        self.frame_index : int = 0
        self.color_r : int = 0
        self.color_g : int = 0
        self.color_b : int = 0
        self.bright_r : int | None = None
        self.bright_g : int | None = None
        self.bright_b : int | None = None

    @property
    def color(self):
        return Color(self.color_r, self.color_g, self.color_b)

    @color.setter
    def color(self, value : Color):
        self.color_r = value.r
        self.color_g = value.g
        self.color_b = value.b

    @property
    def bright_color(self):
        if self.bright_r is None:
            return None

        return Color(self.bright_r, self.bright_g, self.bright_b)

    @bright_color.setter
    def bright_color(self, value : Color):
        self.bright_r = value.r
        self.bright_g = value.g
        self.bright_b = value.b

    def get_color(self, mode : int):
        if mode == ColorMode.BRIGHTEST:
            return self.bright_color

        return self.color

class SourceService:
    def __init__(self):
        pass

    @classmethod
    def create_source(cls, conn : sqlite3.Connection, source : Source, do_commit : bool = True):
        cur = conn.cursor()
        
        sql = "INSERT INTO Source(sha512, imdb_id, kind, metadata_name, metadata_year) VALUES (?, ?, ?, ?, ?);"

        params = [source.sha512, source.imdb_id, source.kind, source.metadata_name, source.metadata_year]

        print("params: ", params)

        cur.execute(sql, params)

        if do_commit:
            conn.commit()

        return cur.lastrowid

    @classmethod
    def get_source_by_id(cls, conn : sqlite3.Connection, id : int):
        cur = conn.cursor()

        sql = "SELECT id, sha512, imdb_id, kind, metadata_name, metadata_year FROM Source WHERE id = ?;"

        cur.execute(sql, [id])

        if cur.rowcount == 0:
            raise IndexError

        row = cur.fetchone()

        source = Source()

        source.id = row[0]
        source.sha512 = row[1]
        source.imdb_id = row[2]
        source.kind = row[3]
        source.metadata_name = row[4]
        source.metadata_year = row[5]

        return source

    @classmethod
    def get_sources(cls, conn : sqlite3.Connection):
        cur = conn.cursor()

        sql = "SELECT id, sha512, imdb_id, kind, metadata_name, metadata_year FROM Source;"

        cur.execute(sql)

        sources = []

        for row in cur.fetchall():
            source = Source()

            source.id = row[0]
            source.sha512 = row[1]
            source.imdb_id = row[2]
            source.kind = row[3]
            source.metadata_name = row[4]
            source.metadata_year = row[5]

            sources.append(source)

        return sources

    @classmethod
    def create_source_frame(cls, conn : sqlite3.Connection, source_id : int, source_frame : SourceFrame, do_commit : bool = True):
        cur = conn.cursor()

        source = cls.get_source_by_id(conn, source_id) # this is only here to make sure a source exists... we may do some other validation in the future with this values idk

        sql = "INSERT INTO SourceFrame(source_id, frame_index, color_r, color_g, color_b, bright_r, bright_g, bright_b) VALUES(?, ?, ?, ?, ?, ?, ?, ?);"

        cur.execute(sql, [source.id, source_frame.frame_index, source_frame.color_r, source_frame.color_g, source_frame.color_b, source_frame.bright_r, source_frame.bright_g, source_frame.bright_b])

        if do_commit:
            conn.commit()

        return cur.lastrowid

    @classmethod
    def create_source_frames(cls, conn : sqlite3.Connection, source_id : int, source_frames : list[SourceFrame], do_commit : bool = True):
        # bulk version of create_source_frame, a movie has ~170k frames so one INSERT per frame is slow
        cur = conn.cursor()

        source = cls.get_source_by_id(conn, source_id)

        sql = "INSERT INTO SourceFrame(source_id, frame_index, color_r, color_g, color_b, bright_r, bright_g, bright_b) VALUES(?, ?, ?, ?, ?, ?, ?, ?);"

        params = [[source.id, sf.frame_index, sf.color_r, sf.color_g, sf.color_b, sf.bright_r, sf.bright_g, sf.bright_b] for sf in source_frames]

        cur.executemany(sql, params)

        if do_commit:
            conn.commit()

    @classmethod
    def update_source_frames_bright(cls, conn : sqlite3.Connection, source_id : int, colors : list[Color], do_commit : bool = True):
        # colors[i] is the brightest color of the frame with frame_index = i
        cur = conn.cursor()

        sql = "UPDATE SourceFrame SET bright_r = ?, bright_g = ?, bright_b = ? WHERE source_id = ? AND frame_index = ?;"

        params = [[c.r, c.g, c.b, source_id, i] for i, c in enumerate(colors)]

        cur.executemany(sql, params)

        if do_commit:
            conn.commit()

    @classmethod
    def get_source_frames(cls, conn : sqlite3.Connection, source_id : int):
        cur = conn.cursor()

        sql = "SELECT id, source_id, frame_index, color_r, color_g, color_b, bright_r, bright_g, bright_b FROM SourceFrame WHERE source_id = ? ORDER BY frame_index;"

        cur.execute(sql, [source_id])

        frames = []

        for row in cur.fetchall():
            sf = SourceFrame()

            sf.id = row[0]
            sf.source_id = row[1]
            sf.frame_index = row[2]
            sf.color_r = row[3]
            sf.color_g = row[4]
            sf.color_b = row[5]
            sf.bright_r = row[6]
            sf.bright_g = row[7]
            sf.bright_b = row[8]

            frames.append(sf)

        return frames

    @classmethod
    def get_source_frame_count(cls, conn : sqlite3.Connection, source_id : int):
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM SourceFrame WHERE source_id = ?;", [source_id])

        return cur.fetchone()[0]

    @classmethod
    def do_source_has_bright(cls, conn : sqlite3.Connection, source_id : int):
        # true when every frame of the source has its brightest color stored
        cur = conn.cursor()

        sql = "SELECT COUNT(*) FROM SourceFrame WHERE source_id = ? AND bright_r IS NULL;"

        cur.execute(sql, [source_id])

        return cur.fetchone()[0] == 0

    @classmethod
    def get_source_id_by_imdb_id(cls, conn : sqlite3.Connection, imdb_id : str):
        cur = conn.cursor()

        cur.execute("SELECT id FROM Source WHERE imdb_id = ?;", [imdb_id])

        row = cur.fetchone()

        return row[0] if row else None

    @classmethod
    def do_source_exists(cls, conn : sqlite3.Connection, sha512 : str, imdb_id : str):
        cur = conn.cursor()

        sql = "SELECT id FROM Source WHERE sha512 = ? OR imdb_id = ?;"

        cur.execute(sql, [sha512, imdb_id])

        rows = cur.fetchall()
        
        return len(rows) > 0

    @classmethod
    def lookup_source(cls, conn : sqlite3.Connection, sha512 : str = "", imdb_id : str = ""):
        cur = conn.cursor()

        sql = "SELECT id FROM Source WHERE sha512 = ? OR imdb_id = ?;"

        cur.execute(sql, [sha512, imdb_id])

        rows = cur.fetchall()

        if len(rows) > 0:
            return rows[0]
        else:
            return 0

    @classmethod
    def get_source_thumbnail(cls, conn : sqlite3.Connection, source_id : int):
        cur = conn.cursor()

        cur.execute("SELECT thumbnail FROM Source WHERE id = ?", [source_id])

        r = cur.fetchone()

        if r[0]:
            return BytesIO(r[0])

        return None

    @classmethod
    def set_source_thumbnail(cls, conn : sqlite3.Connection, source_id : int, thumbanil : BytesIO):
        cur = conn.cursor()

        cur.execute("UPDATE Source SET thumbnail = ? WHERE id = ?", [thumbanil.getvalue(), source_id])

        conn.commit()

if __name__ == "__main__":
    conn = database.create_connection()

    sha512 = "a1eade7f53a2de16eac29687edaa5512051fd7c1e4bd18baccf5d8d656b92e81db3a8675fd2fc4dc1f24e6c12534a566a44c6cdbbb301bdda62859e93d44ed00"
    imdb_id = "tt1488353"

    r = SourceService.do_source_exists(conn, sha512, imdb_id)

    print(f"source exists: {r}")