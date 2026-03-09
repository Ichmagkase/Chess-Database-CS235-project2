from io import TextIOWrapper
import chess.pgn

from shared.models import GameCompatible
from shared.models import Player
from shared.models import Event
from shared.models import Move


class Parser:
    def __init__(self, pgn_path: str):
        self.pgn: TextIOWrapper = open(pgn_path)

    def get_one(self) -> GameCompatible | None:
        game = chess.pgn.read_game(self.pgn)

        if game is None:
            return None

        moves = []
        count = 0
        board = game.board()
        for move in game.mainline_moves():
            count += 1
            board.push(move)
            piece = str(board.piece_at(move.from_square))
            moves.append(
                Move(
                    ply_number=count,
                    result_board_fen=board.board_fen(),
                    piece=piece,
                    move_from=piece + str(move.from_square),
                    move_to=piece + str(move.to_square),
                )
            )

        black_player = Player(verify_s(game.headers.get("Black")))
        white_player = Player(verify_s(game.headers.get("White")))

        event = Event(
            event_name=verify_s(game.headers.get("Event")),
            site=verify_s(game.headers.get("Site")),
            event_date=verify_s(game.headers.get("EventDate")),
        )

        game = GameCompatible(
            event=event,
            date=verify_s(game.headers.get("Date")),
            round=verify_i(game.headers.get("Round")),
            white_player=white_player,
            black_player=black_player,
            result=verify_s(game.headers.get("Result")),
            eco=verify_s(game.headers.get("ECO")),
            white_elo=verify_i(game.headers.get("WhiteElo")),
            black_elo=verify_i(game.headers.get("BlackElo")),
            set_up=verify_b(game.headers.get("SetUp")),
            start_fen=verify_s(game.headers.get("FEN")),
            ply_limit=verify_i(game.headers.get("PlyCount")),
            moves=[],
            ply_count=len(moves),
        )

        return game


def verify_s(x) -> str:
    return x if x is not None else "N/A"


def verify_i(x) -> int:
    return x if x is not None else 0


def verify_b(x) -> bool:
    return x if x is not None else False
