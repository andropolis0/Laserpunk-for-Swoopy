import pygame
import sqlite3
import datetime
import json
import globals as glb
import settings

class DBData:
    player_name = ""
    first_time = True
    opened_save = None

    def __init__(self):
        self.connection = sqlite3.connect("saves.db")
        self.cursor = self.connection.cursor()

        # NOTE: Movement is stored as tinyint, so when its read, its final array is based on if its true or false

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS saves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name VARCHAR(100),
                save_name VARCHAR(100),
                save_score INT,

                settings_darkness TINYINT,
                settings_hints TINYINT,
                settings_music_volume INT,
                settings_movement TINYINT,
                settings_sprint_key INT,

                progress TEXT
            )
        """)

    def checkFirstTime(self):
        # Check if its the player's first time
        self.cursor.execute("SELECT settings_darkness FROM saves WHERE player_name = ? LIMIT 1", (DBData.player_name,))

        DBData.first_time = self.cursor.fetchone() is None

    def readPlayerSaves(self):
        self.cursor.execute("""
            SELECT save_name, save_score
            FROM saves 
            WHERE player_name = ?
        """, (DBData.player_name,))

        rows = self.cursor.fetchall()

        if rows is None: return []

        return rows

    def readPlayerSettings(self, from_save):
        self.cursor.execute("""
            SELECT 
            settings_darkness,
            settings_hints,
            settings_music_volume,
            settings_movement,
            settings_sprint_key 

            FROM saves 
            WHERE player_name = ? AND save_name = ?
        """, (DBData.player_name, from_save))

        row = self.cursor.fetchone()

        if row is None: return []

        return row

    def readTopScores(self):
        self.cursor.execute("""
            SELECT player_name, save_score
            FROM saves
            ORDER BY save_score DESC
            LIMIT 9
        """)

        rows = self.cursor.fetchall()

        if rows is None: return []

        return rows

    def readSaveScore(self, from_save):
        self.cursor.execute("""
            SELECT save_score
            FROM saves 
            WHERE player_name = ? AND save_name = ?
        """, (DBData.player_name, from_save))

        row = self.cursor.fetchone()

        if row is None: return 0

        return row[0]

    def readProgress(self, from_save):
        self.cursor.execute("""
            SELECT progress
            FROM saves
            WHERE save_name = ? AND player_name = ?
        """, (from_save, DBData.player_name))

        row = self.cursor.fetchone()

        if row is None: return None

        return json.loads(row[0])

    def writeData(self):
        # Check if the player actually did anything
        if not hasattr(glb.engine, "score") or glb.engine.score == 0:
            return

        # PROGRESS SAVING IS ONLY DONE HERE

        progress_dict = {
            "player_weapon": glb.engine.player.inventory.weapon_slot.name,
            "player_inventory_slots": [(slot.name, slot.image_path, glb.engine.player.inventory.slot_amounts[i]) for i, slot in enumerate(glb.engine.player.inventory.slots)]
        }

        progress_json = json.dumps(progress_dict)

        # The player was playing an already created save
        if DBData.opened_save != None:
            self.cursor.execute("""
                UPDATE saves
                SET
                    save_score = ?,

                    settings_darkness = ?,
                    settings_hints = ?,
                    settings_music_volume = ?,
                    settings_movement = ?,
                    settings_sprint_key = ?,

                    progress = ?
                WHERE player_name = ? AND save_name = ?
            """, (
                glb.engine.score,

                settings.darkness,
                settings.hints,
                settings.music_volume,
                1 if settings.movement == [pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d] else 0,
                settings.sprint_key,

                progress_json,

                DBData.player_name,
                DBData.opened_save
            ))

        # Save a new save
        else:
            # Get the number of already saved saves
            self.cursor.execute("SELECT COUNT(*) FROM saves WHERE player_name = ?", (DBData.player_name,))

            save_num = self.cursor.fetchone()[0] + 1

            self.cursor.execute("""
                INSERT OR REPLACE INTO saves (
                    player_name,
                    save_name,
                    save_score,

                    settings_darkness,
                    settings_hints,
                    settings_music_volume,
                    settings_movement,
                    settings_sprint_key,

                    progress
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                DBData.player_name,
                f"Save {save_num}",
                glb.engine.score,

                settings.darkness,
                settings.hints,
                settings.music_volume,
                1 if settings.movement == [pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d] else 0,
                settings.sprint_key,

                progress_json
            ))

        self.connection.commit()
