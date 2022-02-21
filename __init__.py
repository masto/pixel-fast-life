"""Game of Life

Conway's Life, optimized for performance.
"""

ROWS = 8
COLS = 32
COLORS = [
    (250, 250, 110),
    (255, 216, 81),
    (255, 180, 70),
    (255, 142, 76),
    (255, 101, 92),
    (255, 58, 114),
    (237, 1, 137),
    (197, 0, 160),
    (138, 27, 180),
]
BOARD_DENSITY = 0.3  # proportion of live cells when creating a new board
MAX_ROUNDS = 200  # reset if the same board runs for too long
PRINT_TIMING = False
DEFAULT_SETTINGS = {"delay_ms": 250}

from random import choice, random, seed
import sys
import time

APP_NAME = "fast_life"

if hasattr(sys, "mpycore"):
    import buttons
    import defines
    import rgb
    import valuestore
    import virtualtimers

    settings = valuestore.load(APP_NAME, "settings") or DEFAULT_SETTINGS
else:
    from unittest.mock import Mock

    buttons = Mock()
    defines = Mock()
    rgb = Mock()
    valuestore = Mock()
    virtualtimers = Mock()

    def vtimers_new(d, callback):
        while True:
            time.sleep(callback() / 1000)

    virtualtimers.new = vtimers_new
    time.ticks_ms = lambda: time.monotonic() * 1000
    time.ticks_diff = lambda a, b: a - b

    settings = DEFAULT_SETTINGS

# The actual board is inset in a larger board, leaving one cell of padding
# around each edge.
CELL_COUNT = (COLS + 2) * (ROWS + 2)
OFFSET = COLS + 3


def print_board(board):
    """Print the board to the console."""

    board_str = str(
        bytes(board)
        .replace(b"\x00", b" ")
        .replace(b"\x01", b"1")
        .replace(b"\x02", b"2")
        .replace(b"\x03", b"3")
        .replace(b"\x04", b"4")
        .replace(b"\x05", b"5")
        .replace(b"\x06", b"6")
        .replace(b"\x07", b"7")
        .replace(b"\x08", b"8")
        .replace(b"\x09", b"9"),
        "ascii",
    )
    for y in range(ROWS + 2):
        start = y * (COLS + 2)
        print(board_str[start : start + COLS + 2])


def show_board(board, color):
    """Put the board on the display."""

    rgb.disablecomp()

    rgb.clear()
    pos = OFFSET
    for r in range(ROWS):
        for c in range(COLS):
            if board[pos]:
                rgb.pixel(COLORS[board[pos] - 1], (c, r))
            pos += 1
        pos += 2

    rgb.enablecomp()


if not hasattr(sys, "mpycore"):
    show_board = lambda board, color: print_board(board)


def randomize_board(board, density=0.3):
    """Randomly populate cells in the board.

    We leave an empty cell of padding on all four sides to simplify neighbor
    calculation.
    """

    for i in range(COLS * ROWS):
        board[OFFSET + i + 2 * int(i / COLS)] = 9 if random() <= density else 0


def evolve_board(board_in, board_out):
    """Run the Life algorithm to convert board_in to board_out"""

    pos = OFFSET
    for r in range(ROWS):
        for c in range(COLS):
            count = (
                (board_in[pos - COLS - 3] == 9)
                + (board_in[pos - COLS - 2] == 9)
                + (board_in[pos - COLS - 1] == 9)
                + (board_in[pos - 1] == 9)
                + (board_in[pos + 1] == 9)
                + (board_in[pos + COLS + 1] == 9)
                + (board_in[pos + COLS + 2] == 9)
                + (board_in[pos + COLS + 3] == 9)
            )
            if board_in[pos] == 9:
                # Any live cell with two or three live neighbors survives.
                board_out[pos] = 9 if count in {2, 3} else max(0, board_in[pos] - 1)
            else:
                # Any dead cell with three live neighbors becomes a live cell.
                board_out[pos] = 9 if count == 3 else max(0, board_in[pos] - 1)
            pos += 1
        pos += 2


reset_flag = True


def reset_game():
    global reset_flag
    reset_flag = True


def run_game():
    board = bytearray(CELL_COUNT)
    next_board = bytearray(CELL_COUNT)
    board2 = bytearray(CELL_COUNT)
    board3 = bytearray(CELL_COUNT)
    round = 0

    color = COLORS[0]

    # improve randomness (taken from Simon Says)
    seed(int(1000000 * time.time()) % 1000000)

    def do_reset():
        global reset_flag
        nonlocal color, board, next_board, board2, board3, round

        randomize_board(board, BOARD_DENSITY)
        next_board = bytearray(CELL_COUNT)
        board2 = bytearray(CELL_COUNT)
        board3 = bytearray(CELL_COUNT)
        color = choice(COLORS)
        round = 0
        reset_flag = False

    def do_frame():
        nonlocal board, next_board, board2, board3, round
        global settings, reset_flag

        if reset_flag:
            do_reset()

        show_board(board, color)

        t1 = time.ticks_ms()
        evolve_board(board, next_board)
        t2 = time.ticks_ms()
        if PRINT_TIMING:
            print(
                "round {} evolved in {:.3f}s".format(
                    round, time.ticks_diff(t2, t1) / 1000
                )
            )

        if next_board == board or next_board == board2 or next_board == board3:
            print("Board finished; resetting.")
            reset_game()
            return settings["delay_ms"] * 3

        round += 1
        if round > MAX_ROUNDS:
            print("Bored of this board; resetting.")
            reset_game()
            return settings["delay_ms"] * 3

        (board3, board2, board, next_board) = (board2, board, next_board, board3)

        return settings["delay_ms"]

    def button_a(pressed):
        if pressed:
            rgb.clear()
            reset_game()

    def button_up(pressed):
        global settings, APP_NAME
        if pressed:
            new_delay = settings["delay_ms"] + 25
            if new_delay <= 5000:
                settings["delay_ms"] = new_delay
                valuestore.save(APP_NAME, "settings", settings)
            else:
                rgb.background((127, 127, 127))
                time.sleep(0.1)
                rgb.background((0, 0, 0))

    def button_down(pressed):
        global settings
        if pressed:
            new_delay = settings["delay_ms"] - 25
            if new_delay >= 25:
                settings["delay_ms"] = new_delay
                valuestore.save(APP_NAME, "settings", settings)
            else:
                rgb.background((127, 127, 127))
                time.sleep(0.1)
                rgb.background((0, 0, 0))

    buttons.register(defines.BTN_A, button_a)
    buttons.register(defines.BTN_UP, button_up)
    buttons.register(defines.BTN_DOWN, button_down)

    # Use 25 for period, because 10 interferes with button detection
    virtualtimers.begin(25)
    virtualtimers.new(25, do_frame)


run_game()
