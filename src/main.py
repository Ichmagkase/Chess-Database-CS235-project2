from parser.parser import Parser
from db.mysql import Database
import os


def main() -> None:
    config = {
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST"),
        "database": os.getenv("DB_NAME"),
    }

    db = Database(config)
    parser = Parser("data/twic210-874.pgn")
    parser.get_one()
    game = parser.get_one()

    # fail_limit = 10
    # fails = 0
    while game is not None:
        try:
            db.add_game(game)
            game = parser.get_one()
        except Exception as e:
            print(f"Skipping malformed game: {e}")


if __name__ == "__main__":
    main()
