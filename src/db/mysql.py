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
        print("adding a game")
        event_id = self.get_or_create_event(game.event)
        white_id = self.get_or_create_player(game.white_player)
        black_id = self.get_or_create_player(game.black_player)
        game_id = str(uuid4())

        with self.cnx.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO Games (
                    game_id,
                    event_id,
                    date,
                    round,
                    white_player_id,
                    black_player_id,
                    result,
                    eco,
                    white_elo,
                    black_elo,
                    set_up,
                    start_fen,
                    ply_count,
                    ply_limit
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """,
                (
                    game_id,
                    event_id,
                    game.date,
                    game.round,
                    white_id,
                    black_id,
                    game.result,
                    game.eco,
                    game.white_elo,
                    game.black_elo,
                    game.set_up,
                    game.start_fen,
                    game.ply_count,
                    game.ply_limit,
                ),
            )

            for move in game.moves:
                cursor.execute(
                    """
                    INERT INTO Moves (
                        game_id,
                        result_board_fen,
                        piece,
                        move_from,
                        move_to,
                    )
                    VALUES (%s, %s, %s, %s, %s);
                """,
                    (
                        game_id,
                        move.result_board_fen,
                        move.piece,
                        move.move_from,
                        move.move_to,
                    ),
                )

            self.cnx.commit()

    def get_or_create_player(self, player: Player) -> str:
        print("adding or acquiring a player ", player.player_alias)
        with self.cnx.cursor() as cursor:
            cursor.execute(
                "SELECT player_id FROM Players WHERE player_alias = %s;",
                (player.player_alias,),
            )
            row = cursor.fetchone()

            if row:
                return str(row[0])

            player_id = str(uuid4())
            cursor.execute(
                "INSERT INTO Players (player_id, player_alias) VALUES (%s, %s);",
                (player_id, player.player_alias),
            )

            self.cnx.commit()
            return player_id

    def get_or_create_event(self, event: Event) -> str:
        print("adding or acquiring event ", event.event_name)
        with self.cnx.cursor() as cursor:
            cursor.execute(
                "SELECT event_id FROM Events WHERE event_name = %s AND event_date = %s AND site = %s;",
                (event.event_name, event.event_date, event.site),
            )
            row = cursor.fetchone()

            if row:
                return str(row[0])

            event_id = str(uuid4())
            cursor.execute(
                "INSERT INTO Events (event_id, event_name, site, event_date) VALUES (%s, %s, %s, %s);",
                (event_id, event.event_name, event.event_date, event.site),
            )

            self.cnx.commit()
            return event_id
