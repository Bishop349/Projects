import sqlite3

# 2025-26 Minnesota Timberwolves Player Averages (Regular Season)
# Stats: G, Min, Pts, ORB, DRB, TRB, Ast, Stl, Blk, TO, PF
players = [
    ("Anthony Edwards",   43, 35.5, 29.8, 0.7, 4.6, 5.3, 3.7, 1.3, 0.8, 2.6, 1.8),
    ("Julius Randle",     53, 33.5, 22.2, 1.7, 5.2, 6.9, 5.4, 1.1, 0.2, 2.6, 2.8),
    ("Jaden McDaniels",   51, 32.1, 15.1, 1.1, 3.1, 4.3, 2.9, 0.9, 0.9, 1.7, 3.4),
    ("Naz Reid",          53, 26.4, 14.5, 1.2, 5.2, 6.4, 2.5, 1.0, 0.9, 1.6, 2.5),
    ("Donte DiVincenzo",  53, 31.4, 13.2, 1.1, 3.5, 4.5, 4.2, 1.4, 0.5, 1.5, 2.5),
    ("Rudy Gobert",       51, 31.4, 10.7, 3.8, 7.6, 11.4, 1.7, 0.8, 1.7, 1.2, 2.7),
    ("Bones Hyland",      44, 14.8,  7.2, 0.3, 1.4,  1.7, 2.6, 0.6, 0.2, 0.9, 1.7),
    ("Terrence Shannon Jr.", 22, 12.8, 4.5, 0.3, 1.0, 1.3, 0.6, 0.3, 0.0, 0.7, 1.3),
    ("Mike Conley",       44, 18.5,  4.4, 0.3, 1.4,  1.8, 2.9, 0.6, 0.3, 0.6, 1.5),
    ("Jaylen Clark",      50, 13.9,  3.8, 0.9, 1.0,  1.9, 0.6, 0.7, 0.2, 0.3, 1.5),
    ("Rob Dillingham",    35,  9.3,  3.5, 0.1, 1.0,  1.2, 1.7, 0.5, 0.1, 1.0, 1.0),
    ("Joan Beringer",     25,  6.9,  3.0, 1.0, 1.0,  2.1, 0.2, 0.1, 0.4, 0.3, 1.0),
    ("Leonard Miller",    19,  5.0,  2.3, 0.4, 0.9,  1.3, 0.3, 0.2, 0.0, 0.5, 0.6),
    ("Johnny Juzang",     21,  4.2,  2.0, 0.2, 0.6,  0.8, 0.3, 0.1, 0.0, 0.2, 0.1),
    ("Joe Ingles",        17,  4.0,  0.6, 0.0, 0.3,  0.3, 0.8, 0.4, 0.0, 0.4, 0.4),
]

# Connect to (or create) the SQLite database
conn = sqlite3.connect("timberwolves_2025_26.db")
cursor = conn.cursor()

# Create the table
cursor.execute("DROP TABLE IF EXISTS player_averages")
cursor.execute("""
    CREATE TABLE player_averages (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        player      TEXT    NOT NULL,
        games       INTEGER,
        minutes     REAL,
        points      REAL,
        off_reb     REAL,
        def_reb     REAL,
        rebounds    REAL,
        assists     REAL,
        steals      REAL,
        blocks      REAL,
        turnovers   REAL,
        fouls       REAL
    )
""")

# Insert all player rows
cursor.executemany("""
    INSERT INTO player_averages
        (player, games, minutes, points, off_reb, def_reb, rebounds,
         assists, steals, blocks, turnovers, fouls)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", players)

conn.commit()

# --- Pretty-print the table ---
print(f"\n{'2025-26 Minnesota Timberwolves — Per-Game Averages':^110}")
print("=" * 110)

header = (
    f"{'Player':<22} {'G':>4} {'Min':>5} {'Pts':>5} {'ORB':>5} "
    f"{'DRB':>5} {'REB':>5} {'AST':>5} {'STL':>5} {'BLK':>5} {'TO':>5} {'PF':>5}"
)
print(header)
print("-" * 110)

rows = cursor.execute("""
    SELECT player, games, minutes, points, off_reb, def_reb, rebounds,
           assists, steals, blocks, turnovers, fouls
    FROM player_averages
    ORDER BY points DESC
""").fetchall()

for r in rows:
    print(
        f"{r[0]:<22} {r[1]:>4} {r[2]:>5.1f} {r[3]:>5.1f} {r[4]:>5.1f} "
        f"{r[5]:>5.1f} {r[6]:>5.1f} {r[7]:>5.1f} {r[8]:>5.1f} {r[9]:>5.1f} "
        f"{r[10]:>5.1f} {r[11]:>5.1f}"
    )

print("-" * 110)
print(f"\nDatabase saved as: timberwolves_2025_26.db")
print(f"Table: player_averages  |  {len(rows)} players\n")

conn.close()