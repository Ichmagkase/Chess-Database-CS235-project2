import mysql.connector
from uuid import uuid4
from mysql.connector import errorcode
from shared.models import GameCompatible
from shared.models import Player
from shared.models import Event


class Database:
    def __init__(self, config: dict) -> None:
        try:
            print(config)
            self.cnx = mysql.connector.connect(**config)
            if not (self.cnx and self.cnx.is_connected()):
                print("could not connect")
                return

            with self.cnx.cursor() as cursor:
                print("creating tables")
                cursor.execute("""
                    CREATE TABLE Events (
                        event_id CHAR(36) NOT NULL,
                        event_name VARCHAR(255), 
                        site VARCHAR(255),
                        event_date VARCHAR(255),

                        PRIMARY KEY (event_id) 
                    );
                """)

                cursor.execute("""
                    CREATE TABLE Players (
                        player_id CHAR(36) NOT NULL,
                        player_alias VARCHAR(255) NOT NULL,

                        PRIMARY KEY (player_id)
                    );
                """)

                cursor.execute("""
                    CREATE TABLE Games (
                        game_id CHAR(36) NOT NULL,
                        event_id CHAR(36),
                        white_player_id CHAR(36),
                        black_player_id CHAR(36),
                        date VARCHAR(16),
                        round VARCHAR(16),
                        result VARCHAR(255),
                        eco VARCHAR(16),
                        white_elo INT,
                        black_elo INT,
                        set_up TINYINT(1),
                        start_fen VARCHAR(93),
                        ply_count INT,
                        ply_limit INT, 

                        PRIMARY KEY (game_id),
                        FOREIGN KEY (event_id) REFERENCES Events(event_id),
                        FOREIGN KEY (white_player_id) REFERENCES Players(player_id),
                        FOREIGN KEY (black_player_id) REFERENCES Players(player_id)
                    );
                """)

                cursor.execute("""
                    CREATE TABLE Moves (
                        ply_number INT NOT NULL,
                        game_id CHAR(36) NOT NULL,
                        result_board_fen VARCHAR(93),
                        piece CHAR(1),
                        move_from VARCHAR(8),
                        move_to VARCHAR(8),

                        PRIMARY KEY (ply_number, game_id),
                        FOREIGN KEY (game_id) REFERENCES Games(game_id)
                    );
                """)
                print("tables created")

        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                print("Something is wrong with your user name or password")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                print("Database does not exist")
            else:
                print(err)

    def add_game(self, game: GameCompatible) -> None:
        self.add_games([game])

    def add_games(self, games: list[GameCompatible]) -> None:
        print(f"adding {len(games)} game(s)")

        # --- Resolve events ------------------------------------------------
        # Fetch all existing events in one query, create missing ones in batch
        unique_events = {
            (g.event.event_name, g.event.event_date, g.event.site): g.event
            for g in games
        }
        event_id_map = self._get_or_create_events(unique_events)

        # --- Resolve players -----------------------------------------------
        unique_players = {
            g.white_player.player_alias: g.white_player for g in games
        } | {g.black_player.player_alias: g.black_player for g in games}
        player_id_map = self._get_or_create_players(unique_players)

        # --- Batch insert Games and Moves -----------------------------------
        games_data = []
        moves_data = []

        for game in games:
            game_id = str(uuid4())
            event_key = (game.event.event_name, game.event.event_date, game.event.site)
            games_data.append(
                (
                    game_id,
                    event_id_map[event_key],
                    game.date,
                    game.round,
                    player_id_map[game.white_player.player_alias],
                    player_id_map[game.black_player.player_alias],
                    game.result,
                    game.eco,
                    game.white_elo,
                    game.black_elo,
                    game.set_up,
                    game.start_fen,
                    game.ply_count,
                    game.ply_limit,
                )
            )
            for ply_number, move in enumerate(game.moves, start=1):
                moves_data.append(
                    (
                        ply_number,
                        game_id,
                        move.result_board_fen,
                        move.piece,
                        move.move_from,
                        move.move_to,
                    )
                )

        with self.cnx.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO Games (
                    game_id, event_id, date, round,
                    white_player_id, black_player_id,
                    result, eco, white_elo, black_elo,
                    set_up, start_fen, ply_count, ply_limit
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """,
                games_data,
            )
            if moves_data:
                cursor.executemany(
                    """
                    INSERT INTO Moves (
                        ply_number, game_id, result_board_fen,
                        piece, move_from, move_to
                    )
                    VALUES (%s, %s, %s, %s, %s, %s);
                    """,
                    moves_data,
                )

        self.cnx.commit()

    def _get_or_create_events(self, unique_events: dict) -> dict:
        """Returns a mapping of (event_name, event_date, site) -> event_id."""
        if not unique_events:
            return {}

        # Fetch all existing matches in one query
        placeholders = ", ".join(["(%s, %s, %s)"] * len(unique_events))
        params = [v for key in unique_events for v in key]
        with self.cnx.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT event_id, event_name, event_date, site FROM Events
                WHERE (event_name, event_date, site) IN ({placeholders});
                """,
                params,
            )
            rows = cursor.fetchall()

        event_id_map = {(row[1], row[2], row[3]): str(row[0]) for row in rows}

        # Batch insert any missing events
        missing = [
            (str(uuid4()), event.event_name, event.event_date, event.site)
            for key, event in unique_events.items()
            if key not in event_id_map
        ]
        if missing:
            with self.cnx.cursor() as cursor:
                cursor.executemany(
                    "INSERT INTO Events (event_id, event_name, event_date, site) VALUES (%s, %s, %s, %s);",
                    missing,
                )
            self.cnx.commit()
            for event_id, event_name, event_date, site in missing:
                event_id_map[(event_name, event_date, site)] = event_id

        return event_id_map

    def _get_or_create_players(self, unique_players: dict) -> dict:
        """Returns a mapping of player_alias -> player_id."""
        if not unique_players:
            return {}

        # Fetch all existing matches in one query
        placeholders = ", ".join(["%s"] * len(unique_players))
        with self.cnx.cursor() as cursor:
            cursor.execute(
                f"SELECT player_id, player_alias FROM Players WHERE player_alias IN ({placeholders});",
                list(unique_players.keys()),
            )
            rows = cursor.fetchall()

        player_id_map = {row[1]: str(row[0]) for row in rows}

        # Batch insert any missing players
        missing = [
            (str(uuid4()), alias)
            for alias in unique_players
            if alias not in player_id_map
        ]
        if missing:
            with self.cnx.cursor() as cursor:
                cursor.executemany(
                    "INSERT INTO Players (player_id, player_alias) VALUES (%s, %s);",
                    missing,
                )
            self.cnx.commit()
            for player_id, alias in missing:
                player_id_map[alias] = player_id

        return player_id_map

    def create_player(self, player: Player) -> str:
        print("adding or acquiring a player ", player.player_alias)
        with self.cnx.cursor() as cursor:
            player_id = str(uuid4())
            cursor.execute(
                "INSERT INTO Players (player_id, player_alias) VALUES (%s, %s);",
                (player_id, player.player_alias),
            )

            self.cnx.commit()
            return player_id

    def get_player(self, player: Player) -> str:
        with self.cnx.cursor() as cursor:
            cursor.execute(
                "SELECT player_id FROM Players WHERE player_alias = %s;",
                (player.player_alias,),
            )
            row = cursor.fetchone()

            if row:
                return str(row[0])
            else:
                return ""

    def create_event(self, event: Event) -> str:
        print("adding or acquiring event ", event.event_name)
        with self.cnx.cursor() as cursor:
            event_id = str(uuid4())
            cursor.execute(
                "INSERT INTO Events (event_id, event_name, site, event_date) VALUES (%s, %s, %s, %s);",
                (event_id, event.event_name, event.event_date, event.site),
            )

            self.cnx.commit()
            return event_id

    def get_event(self, event: Event) -> str:
        with self.cnx.cursor() as cursor:
            cursor.execute(
                "SELECT event_id FROM Events WHERE event_name = %s AND event_date = %s AND site = %s;",
                (event.event_name, event.event_date, event.site),
            )
            row = cursor.fetchone()

            if row:
                return str(row[0])
            else:
                return ""
