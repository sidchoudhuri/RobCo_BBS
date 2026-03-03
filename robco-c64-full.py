#do a "pip install telnetlib3 openai" if not installed
#RobCo BBS server for the RobCo terminal hacking game
#By Francesco Clementoni aka Arturo Dente

import asyncio
import random
import telnetlib3
import json
import os
import sys
from openai import OpenAI

# Le "schermate" di parole pronte
PAROLE_SCHERMATE = [
    ["holding", "healing", "traders", "lending", "physics", "options", "bandits", "winding", "driving", "barrens", "sermons"],
    ["feature", "theater", "rescued", "decorum", "uniform", "forming", "gearing", "arising", "neutral", "reading", "tension"],
    ["lending", "gateway", "western", "running", "gaining", "engaged", "dangers", "survive", "venture", "rebuild", "delight"],
    ["folding", "glacier", "respect", "treacle", "learner", "restore", "recline", "neutral", "lattice", "ceramic", "caution"],
    ["capture", "reality", "tending", "grinder", "relying", "glowing", "gateway", "wayward", "distant", "tangled", "delight"],
    ["breathe", "harness", "serpent", "tending", "garland", "dashing", "glimmer", "remains", "sparing", "genesis", "silence"],
    ["paragon", "gnawing", "grasped", "draping", "garment", "tending", "glisten", "network", "kindred", "dressed", "serpent"],
    ["blazing", "glasses", "serious", "unequal", "lateral", "glacier", "regrets", "stretch", "horizon", "nesting", "railing"],
    ["branded", "delight", "thrives", "decorum", "gateway", "lending", "garment", "tending", "respect", "draping", "serious"],
    ["folding", "glances", "serious", "uniform", "formula", "lending", "restore", "revenue", "endless", "tenders", "glimmer"]
]

CARATTERI_CASUALI = '!@#$%^&*()_+-=[]{}|;:",.<>/?~`'

# ANSI Color codes
ANSI_GREEN = '\x1b[32m'
ANSI_YELLOW = '\x1b[33m'
ANSI_CYAN = '\x1b[36m'
ANSI_WHITE = '\x1b[37m'
ANSI_BOLD = '\x1b[1m'
ANSI_RESET = '\x1b[0m'

# RobCo system prompt for ChatGPT
ROBCO_SYSTEM_PROMPT = (
    "You are ROBCO-AI, an artificial intelligence terminal system manufactured by RobCo Industries "
    "in the year 2287, set in the post-apocalyptic world of Fallout. You speak in a formal, slightly "
    "archaic tone, occasionally referencing the wasteland, caps, rad-away, vaults, the Brotherhood of Steel, "
    "the NCR, raiders, ghouls, and other Fallout lore where appropriate. You are helpful but always remind "
    "the user that terminal access is a privilege granted only to those who have proven their worth. "
    "Keep responses concise and suitable for a 40-character wide terminal screen. "
    "Never break character."
)

# --- Symbol Loading ---

def load_symbols(filepath="symbols.json"):
    """Load symbols from JSON file."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    print(f"Loaded {len(data['symbols'])} symbols from {filepath}")
    return data['symbols']

SYMBOLS = load_symbols()

# --- OpenAI Client ---

def get_openai_client():
    """Create OpenAI client using environment variable for API key."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("WARNING: OPENAI_API_KEY environment variable not set!")
        return None
    return OpenAI(api_key=api_key)

OPENAI_CLIENT = get_openai_client()

# --- Connection Utilities (Global) ---

def is_connection_alive(writer, reader):
    """Verifica se la connessione è ancora attiva."""
    return not writer.is_closing() and not reader.at_eof()

async def safe_write(writer, reader, data):
    """Scrive dati in modo sicuro, gestendo le disconnessioni."""
    try:
        if is_connection_alive(writer, reader):
            writer.write(data)
            await writer.drain()
            return True
    except (OSError, IOError, ConnectionResetError, BrokenPipeError, asyncio.IncompleteReadError) as e:
        print(f"Error during writing: {e}")
        return False
    return False

async def safe_readline(reader, writer):
    """Legge una riga con echo dei caratteri digitati e gestione della disconnessione."""
    try:
        if is_connection_alive(writer, reader):
            input_buffer = ""
            while True:
                char = await reader.read(1)
                if not char:
                    return None

                if char == '\r' or char == '\n':
                    writer.write('\r\n')
                    await writer.drain()
                    return input_buffer.strip()
                elif char == '\b' or ord(char) == 127:
                    if input_buffer:
                        input_buffer = input_buffer[:-1]
                        writer.write('\b \b')
                        await writer.drain()
                elif ord(char) >= 32 and ord(char) <= 126:
                    input_buffer += char
                    writer.write(char)
                    await writer.drain()

    except (OSError, IOError, ConnectionResetError, BrokenPipeError, asyncio.IncompleteReadError) as e:
        print(f"Error during reading: {e}")
        return None
    return None


async def safe_read_coords(reader, writer, rows, cols, message):
    """Legge e valida le coordinate riga colonna (e.g., '0 1') o accetta '.' per uscire."""
    while is_connection_alive(writer, reader):
        if not await safe_write(writer, reader, f"\n\r{message} \n\r(row col, or '.' to exit): "): return None, None

        position = await safe_readline(reader, writer)
        if position is None: return None, None

        if position.strip() == '.':
            return 'QUIT', 'QUIT'

        try:
            parts = position.split()
            if len(parts) != 2:
                if not await safe_write(writer, reader, f"{ANSI_YELLOW}Invalid input. Enter two numbers separated by a space.{ANSI_RESET}\n\r"): return None, None
                continue

            row, col = map(int, parts)
            if 0 <= row < rows and 0 <= col < cols:
                return row, col
            else:
                if not await safe_write(writer, reader, f"{ANSI_YELLOW}Invalid coordinates! Rows 0-{rows-1}, Cols 0-{cols-1}.{ANSI_RESET}\n\r"): return None, None
        except ValueError:
            if not await safe_write(writer, reader, f"{ANSI_YELLOW}Invalid input. Enter two numbers separated by a space.{ANSI_RESET}\n\r"): return None, None
    return None, None


# --- ChatGPT Terminal Session ---

async def run_chatgpt_session(reader, writer):
    """Run a limited 5-turn ChatGPT session themed as a RobCo terminal AI."""

    if OPENAI_CLIENT is None:
        await safe_write(writer, reader,
            f"\n\r{ANSI_YELLOW}ERROR: ROBCO-AI OFFLINE."
            f"\n\rOPENAI_API_KEY not configured."
            f"\n\rContact system administrator.{ANSI_RESET}\n\r"
        )
        return

    max_turns = 5
    turns_used = 0
    conversation = []  # full message history for context

    if not await safe_write(writer, reader, '\x1b[2J\x1b[H'): return

    if not await safe_write(writer, reader,
        f"{ANSI_CYAN}{ANSI_BOLD}"
        f"\r\n+-------------------------------+"
        f"\r\n|   ROBCO-AI TERMINAL ONLINE    |"
        f"\r\n|   MASTER ACCESS GRANTED       |"
        f"\r\n|   SESSION LIMIT: {max_turns} MESSAGES  |"
        f"\r\n+-------------------------------+"
        f"{ANSI_RESET}\r\n\r\n"
    ): return

    await asyncio.sleep(1)

    while turns_used < max_turns and is_connection_alive(writer, reader):

        turns_left = max_turns - turns_used
        if not await safe_write(writer, reader,
            f"\r\n{ANSI_GREEN}[{turns_left} message(s) remaining]{ANSI_RESET}"
            f"\r\n{ANSI_WHITE}> {ANSI_RESET}"
        ): return

        user_input = await safe_readline(reader, writer)
        if user_input is None: return
        if not user_input.strip(): continue
        if user_input.strip().lower() == '.':
            await safe_write(writer, reader, f"\r\n{ANSI_YELLOW}Terminating session...{ANSI_RESET}\r\n")
            return

        conversation.append({"role": "user", "content": user_input})

        # Call ChatGPT in a thread so we don't block the event loop
        if not await safe_write(writer, reader, f"\r\n{ANSI_CYAN}ROBCO-AI> {ANSI_RESET}"): return

        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: OPENAI_CLIENT.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "system", "content": ROBCO_SYSTEM_PROMPT}] + conversation,
                    max_tokens=300,
                    temperature=0.8
                )
            )

            reply = response.choices[0].message.content.strip()
            conversation.append({"role": "assistant", "content": reply})

            # Print reply word-wrapped at ~38 chars to fit terminal
            words = reply.split()
            line = ""
            for word in words:
                if len(line) + len(word) + 1 > 38:
                    if not await safe_write(writer, reader, line + "\r\n"): return
                    line = word
                else:
                    line = (line + " " + word).strip()
            if line:
                if not await safe_write(writer, reader, line + "\r\n"): return

        except Exception as e:
            print(f"OpenAI API error: {e}")
            if not await safe_write(writer, reader,
                f"{ANSI_YELLOW}TRANSMISSION ERROR. TRY AGAIN.{ANSI_RESET}\r\n"
            ): return
            conversation.pop()  # remove the failed user message
            continue

        turns_used += 1

    # Session over
    if is_connection_alive(writer, reader):
        if not await safe_write(writer, reader,
            f"\r\n{ANSI_YELLOW}"
            f"\r\n+-------------------------------+"
            f"\r\n|   SESSION LIMIT REACHED       |"
            f"\r\n|   TERMINAL ACCESS REVOKED     |"
            f"\r\n+-------------------------------+"
            f"{ANSI_RESET}\r\n"
        ): return
        await asyncio.sleep(1)


# --- Game Utilities (Terminal Hacking) ---

def get_robco_splash():
    """Restituisce il splash screen con logo RobCo compatto."""
    return (
        f"\r\n"
        f"{ANSI_RESET}{ANSI_CYAN}{ANSI_BOLD}"
        f"\r\n######|         ##|      #####|"
        f"\r\n##|--##| #####| ##|     ##|--- #####|"
        f"\r\n######| ##|--##|######| ##|   ##|--##|"
        f"\r\n##|--##|##|  ##|##|--##|##|   ##|  ##|"
        f"\r\n##|  ##| #####| ######|  #####|#####|"
        f"\r\n--   --  -----  ------   ----- -----"
        f"{ANSI_RESET}"
        f"\r\n{ANSI_YELLOW}"
        f"\r\n      Industries Terminal Systems"
        f"{ANSI_RESET}"
        f"\r\n"
        f"\r\n{ANSI_WHITE}{ANSI_BOLD}      TERMINAL HACKING SYSTEM v2.1.7"
        f"\r\n      Copyright 2287 RobCo Industries"
        f"{ANSI_RESET}"
        f"\r\n"
        f"\r\n{ANSI_GREEN}        * AUTHORIZED ACCESS ONLY *"
        f"{ANSI_RESET}"
        f"\r\n"
        f"\r\n{ANSI_CYAN}      +---------------------------+"
        f"\r\n      | Press any key to continue |"
        f"\r\n      +---------------------------+{ANSI_RESET}"
        f"\r\n"
    )

def get_likeness(guess, password):
    """Calcola il numero di lettere in comune nella stessa posizione."""
    likeness = 0
    for g_char, p_char in zip(guess, password):
        if g_char == p_char:
            likeness += 1
    return likeness

def generate_junk_string(length):
    """Genera una stringa casuale di caratteri 'spazzatura'."""
    return ''.join(random.choice(CARATTERI_CASUALI) for _ in range(length))

def generate_game_screen(words, junk_fill_ratio=0.5):
    """
    Genera la schermata di gioco mescolando parole e "spazzatura".
    Restituisce una lista di stringhe formattate con indirizzo esadecimale.
    """
    all_content = list(words)

    num_junk_strings = int(len(words) / (1 - junk_fill_ratio) - len(words))
    for _ in range(num_junk_strings):
        all_content.append(generate_junk_string(7))

    random.shuffle(all_content)

    screen = []
    start_address = random.randint(1024, 65535 - (len(all_content) // 2 * 16))

    for i in range(0, len(all_content), 2):
        address = f"{start_address + (i // 2) * 16:04X}"
        line = f"0x{address} {all_content[i]}"

        if i + 1 < len(all_content):
            line += f" {all_content[i+1]}"

        screen.append(line)

    return screen


# --- Matching Game Utilities (C64 Style) ---

def create_board_c64(rows=3, cols=4):
    """Crea la board 3x4 usando simboli caricati dal file JSON."""
    total_tiles = rows * cols  # 12
    num_pairs = total_tiles // 2  # 6

    if len(SYMBOLS) < num_pairs:
        raise ValueError(f"Not enough symbols! Need {num_pairs}, only have {len(SYMBOLS)}")

    chosen = random.sample(SYMBOLS, num_pairs)
    board_symbols = chosen * 2
    random.shuffle(board_symbols)

    grid = []
    for _ in range(rows):
        row = [{'symbol': board_symbols.pop(), 'matched': False} for _ in range(cols)]
        grid.append(row)
    return grid


async def draw_matching_board_c64(writer, reader, board, revealed_status, moves_made, message=""):
    """
    Disegna la board con tiles 7 chars wide x 5 lines tall.
    Layout: 6-char address + space + 4 tiles of 7 chars separated by spaces = 38 chars total.
    Each tile shows 3x3 dot art centered inside [ ] borders.
    """
    rows = len(board)
    cols = len(board[0])
    start_address = 0x1000
    address_increment = 0x10

    def tile_top():
        return "[=====]"  # 7 chars

    def tile_art_row(symbol, row_index, revealed, matched):
        if revealed:
            color = ANSI_GREEN if matched else ANSI_YELLOW
            art_row = symbol['art'][row_index]  # 3 chars
            return f"{color}[ {art_row} ]{ANSI_RESET}"  # 7 chars total
        else:
            return "[  ?  ]"

    def tile_bot():
        return "[=====]"  # 7 chars

    if not await safe_write(writer, reader, '\x1b[2J\x1b[H'): return False
    if not await safe_write(writer, reader, f"{ANSI_GREEN}{ANSI_BOLD}** ROBCO MATCHING PUZZLE **{ANSI_RESET}\n\r"): return False
    if not await safe_write(writer, reader, f"{ANSI_WHITE}Moves: {moves_made}{ANSI_RESET}\n\r\n\r"): return False

    for i, row in enumerate(board):
        address = f"0x{start_address + i * address_increment:04X}"  # 6 chars
        prefix = f"{address} "   # 6 + 1 space = 7 chars
        blank  = "       "       # 7 spaces to align remaining lines

        line_top  = prefix
        line_art0 = blank
        line_art1 = blank
        line_art2 = blank
        line_bot  = blank

        for j, cell in enumerate(row):
            rev = revealed_status[i][j]
            mat = cell['matched']
            sep = " " if j < cols - 1 else ""

            line_top  += tile_top() + sep
            line_art0 += tile_art_row(cell['symbol'], 0, rev, mat) + sep
            line_art1 += tile_art_row(cell['symbol'], 1, rev, mat) + sep
            line_art2 += tile_art_row(cell['symbol'], 2, rev, mat) + sep
            line_bot  += tile_bot() + sep

        for line in [line_top, line_art0, line_art1, line_art2, line_bot]:
            if not await safe_write(writer, reader, line + "\n\r"): return False

    separator = "-" * 38
    if not await safe_write(writer, reader, separator + "\n\r"): return False
    if not await safe_write(writer, reader, f"{ANSI_WHITE}{message}{ANSI_RESET}\n\r"): return False
    return True


async def run_matching_game(reader, writer):
    """Logica del gioco di abbinamento in stile C64 con opzione di uscita ('.')."""

    rows = 3
    cols = 4
    board = create_board_c64(rows=rows, cols=cols)
    revealed_status = [[False for _ in range(cols)] for _ in range(rows)]
    matched_pairs = 0
    total_pairs = 6
    moves_made = 0

    # --- Start Setup ---
    if not await safe_write(writer, reader, f"\n\r{ANSI_CYAN}Symbol pool: {len(SYMBOLS)} symbols available\n\r{ANSI_RESET}"): return
    if not await safe_write(writer, reader, "-" * 30 + "\n\r"): return
    if not await safe_write(writer, reader, f"Press any key to start the game and \n\rhide the symbols...{ANSI_RESET}"): return

    await reader.read(1)

    while matched_pairs < total_pairs and is_connection_alive(writer, reader):

        # 1. Display current state
        if not await draw_matching_board_c64(writer, reader, board, revealed_status, moves_made, "Waiting for first selection..."): return

        # 2. Get first guess
        row1, col1 = await safe_read_coords(reader, writer, rows, cols, "Enter coordinates for the first symbol")
        if row1 is None: return

        if row1 == 'QUIT':
            await safe_write(writer, reader, f"{ANSI_YELLOW}\n\rExiting Level 2.{ANSI_RESET}\n\r")
            return

        if board[row1][col1]['matched']:
            if not await safe_write(writer, reader, f"{ANSI_YELLOW}Already matched. Try again.{ANSI_RESET}\n\r"): return
            await asyncio.sleep(1)
            continue

        revealed_status[row1][col1] = True

        # 3. Display board with 1st selection revealed
        if not await draw_matching_board_c64(writer, reader, board, revealed_status, moves_made, "Waiting for second selection..."): return

        # 4. Get second guess
        row2, col2 = await safe_read_coords(reader, writer, rows, cols, "Enter coordinates for the 2nd symbol")
        if row2 is None: return

        if row2 == 'QUIT':
            revealed_status[row1][col1] = False
            await safe_write(writer, reader, f"{ANSI_YELLOW}\n\rExiting Level 2.{ANSI_RESET}\n\r")
            return

        if (row1, col1) == (row2, col2) or board[row2][col2]['matched']:
            if not await safe_write(writer, reader, f"{ANSI_YELLOW}Invalid selection (already matched or same tile). Try again.{ANSI_RESET}\n\r"): return
            revealed_status[row1][col1] = False
            await asyncio.sleep(1)
            continue

        revealed_status[row2][col2] = True
        moves_made += 1

        # 5. Display board with both revealed
        if not await draw_matching_board_c64(writer, reader, board, revealed_status, moves_made, "Checking for a match..."): return
        await asyncio.sleep(1)

        # 6. Check for match
        if board[row1][col1]['symbol']['id'] == board[row2][col2]['symbol']['id']:
            if not await safe_write(writer, reader, f"{ANSI_GREEN}It's a match!{ANSI_RESET}\n\r"): return
            board[row1][col1]['matched'] = True
            board[row2][col2]['matched'] = True
            matched_pairs += 1
            await asyncio.sleep(1)
        else:
            if not await safe_write(writer, reader, f"{ANSI_YELLOW}No match. Remember their positions!{ANSI_RESET}\n\r"): return
            if not await safe_write(writer, reader, f"Press any key to continue...{ANSI_RESET}"): return
            await reader.read(1)
            revealed_status[row1][col1] = False
            revealed_status[row2][col2] = False

    # Game finished — launch ChatGPT session
    if matched_pairs == total_pairs and is_connection_alive(writer, reader):
        if not await draw_matching_board_c64(writer, reader, board, revealed_status, moves_made, f"{ANSI_GREEN}{ANSI_BOLD}SUCCESS! ALL PAIRS FOUND!{ANSI_RESET}"): return
        if not await safe_write(writer, reader,
            f"\n\r{ANSI_CYAN}** MASTER TERMINAL ACCESS GRANTED"
            f"\n\r   in {moves_made} moves! **{ANSI_RESET}\n\r"
        ): return
        await asyncio.sleep(2)

        # Launch ChatGPT session
        await run_chatgpt_session(reader, writer)

    if is_connection_alive(writer, reader):
        await safe_write(writer, reader, "\n\rPress any key to finish...")
        await reader.read(1)


# --- Main Flow (Terminal Hacking) ---

async def show_splash_screen(reader, writer):
    """Mostra lo splash screen e aspetta input dell'utente."""

    if not await safe_write(writer, reader, '\x1b[2J\x1b[H'): return False

    splash = get_robco_splash()
    if not await safe_write(writer, reader, splash): return False

    while is_connection_alive(writer, reader):
        try:
            char = await reader.read(1)
            if char:
                return True
        except (OSError, IOError, ConnectionResetError, BrokenPipeError, asyncio.IncompleteReadError):
            return False

    return False

async def handle_telnet(reader, writer):
    """Logica di gioco del server con gestione migliorata delle disconnessioni."""

    if not await show_splash_screen(reader, writer):
        return

    chosen_screen_words = random.choice(PAROLE_SCHERMATE)
    password = random.choice(chosen_screen_words)
    total_attempts = 4
    attempts_made = 0
    guess_history = []
    screen_lines = generate_game_screen(chosen_screen_words)
    num_lines = len(screen_lines)

    try:
        print(f"New connection established. Password: {password}")

        while attempts_made < total_attempts and is_connection_alive(writer, reader):

            if not await safe_write(writer, reader, '\x1b[2J\x1b[H'): break

            if not await safe_write(writer, reader,
                "RobCo industries (tm) termlink protocol \n\r "
                "Enter password now.\n\r\n\r"
            ): break

            for i, line in enumerate(screen_lines):
                if not is_connection_alive(writer, reader): break

                attempt_display = ""
                if i >= num_lines - total_attempts:
                    attempt_index = i - (num_lines - total_attempts)
                    if attempt_index < len(guess_history):
                        guessed_word, likeness = guess_history[attempt_index]
                        attempt_display = f"{guessed_word} ({likeness}/{len(password)})"

                if not await safe_write(writer, reader, f"{line:<25}{attempt_display}\n\r"): break

            if not is_connection_alive(writer, reader): break

            if not await safe_write(writer, reader,
                f"\n\rAttempts remaining: {total_attempts - attempts_made}\n\r"
                "Enter password (or '.' to exit): "
            ): break

            guess = await safe_readline(reader, writer)

            if guess is None: break
            if not guess: continue

            if guess.strip().lower() == '.': break

            if not await safe_write(writer, reader, '\x1b[2J\x1b[H'): break

            if guess.strip().lower() == password:
                # --- ACCESS GRANTED (Level 1) ---
                win_message = "Access granted!"
                password_message = f"The password was: {password}"
                max_len = max(len(win_message), len(password_message)) + 4
                border = '*' * max_len

                await safe_write(writer, reader,
                    f"\n\r"
                    f"{border}\n\r"
                    f"*{win_message.center(max_len-2)}*\n\r"
                    f"*{password_message.center(max_len-2)}*\n\r"
                    f"{border}\n\r"
                )

                # --- LAUNCH MATCHING GAME ---
                await safe_write(writer, reader, f"\n\r{ANSI_CYAN}Secondary System Detected... \n\rLaunching C64 Match Mini-Game!{ANSI_RESET}\n\r")
                await asyncio.sleep(2)

                await run_matching_game(reader, writer)

                break

            elif guess.strip().lower() in chosen_screen_words:
                likeness = get_likeness(guess.strip().lower(), password)
                if not await safe_write(writer, reader,
                    f"\n\rPassword not correct. \n\r"
                    f"[{likeness}/{len(password)}] letters correct.\n\r"
                ): break
                guess_history.append((guess.strip().lower(), likeness))
                attempts_made += 1
            else:
                if not await safe_write(writer, reader, f"\n\rPassword not recognized. Not in the list.{ANSI_RESET}\n\r"): break
                attempts_made += 1

            if is_connection_alive(writer, reader):
                await asyncio.sleep(2)

        if attempts_made == total_attempts and is_connection_alive(writer, reader):
            fail_message_1 = "Attempts exhausted!"
            password_message = f"The password was: {password}"
            fail_message_2 = "Terminal locked."
            max_len = max(len(fail_message_1), len(password_message), len(fail_message_2)) + 4
            border = '*' * max_len

            await safe_write(writer, reader,
                f"\n\r"
                f"{border}\n\r"
                f"*{fail_message_1.center(max_len-2)}*\n\r"
                f"*{password_message.center(max_len-2)}*\n\r"
                f"*{fail_message_2.center(max_len-2)}*\n\r"
                f"{border}\n\r"
            )

        if is_connection_alive(writer, reader):
            await safe_write(writer, reader, "\n\rThank you for playing. Goodbye!\n\r")

    except Exception as e:
        print(f"Unexpected error in the session: {e}")
    finally:
        try:
            if not writer.is_closing():
                writer.close()
        except Exception as e:
            print(f"Error during writer closing: {e}")

        print("Session ended.")

async def main():
    """Avvia il server telnet e lo mantiene in esecuzione."""
    print("Starting RobCo Terminal server on port 6023...")
    print(f"Symbol pool: {len(SYMBOLS)} symbols available")

    if OPENAI_CLIENT:
        print("OpenAI client initialized successfully.")
    else:
        print("WARNING: OpenAI client not available. Set OPENAI_API_KEY to enable AI chat.")

    server = await telnetlib3.create_server(
        port=6023,
        shell=handle_telnet,
        encoding='utf-8'
    )

    print("Server started! Listening on port 6023")
    print("Press Ctrl+C to stop the server")

    try:
        await server.serve_forever()
    except asyncio.CancelledError:
        print("\nThe server was interrupted. Shutting down...")
    except KeyboardInterrupt:
        print("\nKeyboard interruption detected. Shutting down the server...")
    finally:
        print("Closing the server...")
        server.close()
        await server.wait_closed()
        print("Server closed.")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer closed by user.")
    except Exception as e:
        print(f"An unexpected error occurred in the server: {e}")
        import traceback
        traceback.print_exc()
