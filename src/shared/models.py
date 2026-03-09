from dataclasses import dataclass


@dataclass
class Move:
    ply_number: int
    result_board_fen: str
    piece: str
    move_from: str
    move_to: str


@dataclass
class Event:
    event_name: str
    site: str
    event_date: str


@dataclass
class Player:
    player_alias: str


@dataclass
class GameCompatible:
    event: Event
    moves: list[Move]
    date: str
    round: int
    white_player: Player
    black_player: Player
    result: str
    eco: str
    white_elo: int
    black_elo: int
    set_up: int
    start_fen: str
    ply_count: int
    ply_limit: int
