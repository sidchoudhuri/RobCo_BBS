#do a "pip install telnetlib3" if telnetlib3 is not installed
#RobCo BBS server for the RobCo terminal hacking game
#By Francesco Clementoni aka Arturo Dente

import asyncio
import random
import telnetlib3
import sys

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
MATCHING_SYMBOLS_C64 = ['C=', '64', '8B', 'm0', 'F1', 'F3', 'F5', 'F7'] # 2-char symbols

# ANSI Color codes
ANSI_GREEN = '\x1b[32m'
ANSI_YELLOW = '\x1b[33m'
ANSI_CYAN = '\x1b[36m'
ANSI_WHITE = '\x1b[37m'
ANSI_BOLD = '\x1b[1m'
ANSI_RESET = '\x1b[0m'

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
                if not char:  # Connessione chiusa
                    return None
                
                # Gestisci caratteri speciali
                if char == '\r' or char == '\n':
                    writer.write('\r\n')
                    await writer.drain()
                    return input_buffer.strip().lower()
                elif char == '\b' or ord(char) == 127:  # Backspace o DEL
                    if input_buffer:
                        input_buffer = input_buffer[:-1]
                        writer.write('\b \b')  # Cancella carattere visivamente
                        await writer.drain()
                elif ord(char) >= 32 and ord(char) <= 126:  # Caratteri stampabili
                    input_buffer += char
                    writer.write(char)  # Echo del carattere
                    await writer.drain()
                    
    except (OSError, IOError, ConnectionResetError, BrokenPipeError, asyncio.IncompleteReadError) as e:
        print(f"Error during reading: {e}")
        return None
    return None


async def safe_read_coords(reader, writer, board_size, message):
    """Legge e valida le coordinate riga colonna (e.g., '0 1')"""
    while is_connection_alive(writer, reader):
        if not await safe_write(writer, reader, f"\n\r{message} (row col, e.g., 0 1): "): return None
        
        position = await safe_readline(reader, writer)
        if position is None: return None
        
        try:
            parts = position.split()
            if len(parts) != 2:
                if not await safe_write(writer, reader, f"{ANSI_YELLOW}Invalid input. Enter two numbers separated by a space.{ANSI_RESET}\n\r"): return None
                continue
                
            row, col = map(int, parts)
            if 0 <= row < board_size and 0 <= col < board_size:
                return row, col
            else:
                if not await safe_write(writer, reader, f"{ANSI_YELLOW}Invalid coordinates! Use 0-{board_size-1}.{ANSI_RESET}\n\r"): return None
        except ValueError:
            if not await safe_write(writer, reader, f"{ANSI_YELLOW}Invalid input. Enter two numbers separated by a space.{ANSI_RESET}\n\r"): return None
    return None

# --- Game Utilities (Terminal Hacking) ---
# ... (Keep get_robco_splash, get_likeness, generate_junk_string, generate_game_screen unchanged) ...

def get_robco_splash():
    """Restituisce il splash screen con logo RobCo compatto."""
    return (
        f"\r\n"
        f"{ANSI_CYAN}{ANSI_BOLD}"
        f"\r\n######|       ##|       #####|"
        f"\r\n##|--##| #####| ##|     ##|---  #####|"
        f"\r\n######| ##|--##|######| ##|   ##|--##|"
        f"\r\n##|--##|##|  ##|##|--##|##|   ##|  ##|"
        f"\r\n##|  ##| #####| ######|  #####| #####|" 
        F"\r\n--  --  -----  ------   -----  -----"
        f"{ANSI_RESET}"
        f"\r\n{ANSI_YELLOW}"
        f"\r\n      Industries Terminal Systems"
        f"{ANSI_RESET}"
        f"\r\n"
        f"\r\n{ANSI_WHITE}{ANSI_BOLD}     TERMINAL HACKING SYSTEM v2.1.7"
        f"\r\n     Copyright 2287 RobCo Industries"
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
    
    # Calculate number of junk strings needed
    num_junk_strings = int(len(words) / (1 - junk_fill_ratio) - len(words))
    for _ in range(num_junk_strings):
        # Junk length matches word length (7)
        all_content.append(generate_junk_string(7)) 

    random.shuffle(all_content)

    screen = []
    # Arbitrary starting address to match the style
    start_address = random.randint(1024, 65535 - (len(all_content) // 2 * 16)) 
    
    for i in range(0, len(all_content), 2):
        address = f"{start_address + (i // 2) * 16:04X}"
        line = f"0x{address} {all_content[i]}"
        
        if i + 1 < len(all_content):
            line += f" {all_content[i+1]}"
            
        screen.append(line)

    return screen


# --- Matching Game Utilities (C64 Style) ---

def create_board_c64(size=4):
    """Crea la board 4x4 con simboli C64 a 2 caratteri."""
    symbols = MATCHING_SYMBOLS_C64
    
    # Ensure we have enough symbols (8 pairs for a 4x4)
    board_symbols = symbols[:(size * size // 2)] * 2
    random.shuffle(board_symbols)

    grid = []
    for _ in range(size):
        row = [{'symbol': board_symbols.pop(), 'matched': False} for _ in range(size)]
        grid.append(row)
    return grid

async def draw_matching_board_c64(writer, reader, board, revealed_status, moves_made, message=""):
    """Disegna la board C64 con formato row/col e XX per i non rivelati."""
    board_size = len(board)
    if not await safe_write(writer, reader, '\x1b[2J\x1b[H'): return False
    
    # Title and Moves
    if not await safe_write(writer, reader, f"{ANSI_GREEN}{ANSI_BOLD}** ROBCO MATCHING PUZZLE (LEVEL 2) **{ANSI_RESET}\n\r"): return False
    if not await safe_write(writer, reader, f"{ANSI_WHITE}Moves made: {moves_made}{ANSI_RESET}\n\r\n\r"): return False
    
    # Print column headers
    col_headers = "  " + " ".join(f"{i:2}" for i in range(board_size))
    if not await safe_write(writer, reader, col_headers + "\n\r"): return False
    
    # Print rows
    for i, row in enumerate(board):
        line = f"{i} "
        for j, cell in enumerate(row):
            if revealed_status[i][j]:
                # Matched or revealed this turn
                color = ANSI_GREEN if cell['matched'] else ANSI_YELLOW
                line += f"{color}{cell['symbol']}{ANSI_RESET} "
            else:
                # Hidden
                line += f"XX "
        if not await safe_write(writer, reader, line + "\n\r"): return False
    
    # Separator
    separator = "-" * (board_size * 3 + 2)
    if not await safe_write(writer, reader, separator + "\n\r"): return False

    # Status message
    if not await safe_write(writer, reader, f"\n\r{ANSI_WHITE}Status: {message}{ANSI_RESET}\n\r"): return False
    return True


async def run_matching_game(reader, writer):
    """Logica del gioco di abbinamento in stile C64."""
    
    board_size = 4
    board = create_board_c64(board_size)
    revealed_status = [[False for _ in range(board_size)] for _ in range(board_size)]
    matched_pairs = 0
    total_pairs = board_size * board_size // 2
    moves_made = 0
    
    # --- Start Setup: Display Symbols before game starts ---
    all_symbols = set()
    for row in board:
        for cell in row:
            all_symbols.add(cell['symbol'])

    if not await safe_write(writer, reader, f"\n\r{ANSI_CYAN}Symbols to match: {ANSI_RESET}"): return
    if not await safe_write(writer, reader, " ".join(sorted(list(all_symbols))) + "\n\r"): return
    if not await safe_write(writer, reader, "-" * 30 + "\n\r"): return
    if not await safe_write(writer, reader, f"Press any key to start the game and hide the symbols...{ANSI_RESET}"): return
    
    await reader.read(1) # Wait for input
    # --- End Setup ---

    while matched_pairs < total_pairs and is_connection_alive(writer, reader):
        
        # 1. Display current state
        if not await draw_matching_board_c64(writer, reader, board, revealed_status, moves_made, "Waiting for first selection..."): return

        # 2. Get first guess
        row1, col1 = await safe_read_coords(reader, writer, board_size, "Enter coordinates for the first symbol")
        if row1 is None: return
        
        if board[row1][col1]['matched']:
            if not await safe_write(writer, reader, f"{ANSI_YELLOW}That's already been matched. Try again.{ANSI_RESET}\n\r"): return
            await asyncio.sleep(1)
            continue
        
        revealed_status[row1][col1] = True

        # 3. Display board with 1st selection revealed
        if not await draw_matching_board_c64(writer, reader, board, revealed_status, moves_made, "Waiting for second selection..."): return

        # 4. Get second guess
        row2, col2 = await safe_read_coords(reader, writer, board_size, "Enter coordinates for the 2nd symbol")
        if row2 is None: return
        
        # Check if tile was selected twice or is already matched
        if (row1, col1) == (row2, col2) or board[row2][col2]['matched']:
            if not await safe_write(writer, reader, f"{ANSI_YELLOW}Invalid selection (already matched or same tile). Try again.{ANSI_RESET}\n\r"): return
            revealed_status[row1][col1] = False # Hide the 1st symbol
            await asyncio.sleep(1)
            continue
        
        revealed_status[row2][col2] = True
        moves_made += 1 # Valid turn completed, increment moves counter

        # 5. Display board with both revealed
        if not await draw_matching_board_c64(writer, reader, board, revealed_status, moves_made, "Checking for a match..."): return
        await asyncio.sleep(1)

        # 6. Check for match
        if board[row1][col1]['symbol'] == board[row2][col2]['symbol']:
            if not await safe_write(writer, reader, f"{ANSI_GREEN}It's a match!{ANSI_RESET}\n\r"): return
            board[row1][col1]['matched'] = True
            board[row2][col2]['matched'] = True
            matched_pairs += 1
            await asyncio.sleep(1)
        else:
            if not await safe_write(writer, reader, f"{ANSI_YELLOW}No match. Take a moment to remember their positions!{ANSI_RESET}\n\r"): return
            if not await safe_write(writer, reader, f"Press any key to continue...{ANSI_RESET}"): return
            
            await reader.read(1) # Wait for input
            revealed_status[row1][col1] = False
            revealed_status[row2][col2] = False


    # Game finished
    if matched_pairs == total_pairs and is_connection_alive(writer, reader):
        if not await draw_matching_board_c64(writer, reader, board, revealed_status, moves_made, f"{ANSI_GREEN}{ANSI_BOLD}SUCCESS! ALL PAIRS FOUND!{ANSI_RESET}"): return
        if not await safe_write(writer, reader, f"\n\r{ANSI_CYAN}** MASTER TERMINAL ACCESS GRANTED in {moves_made} moves! **{ANSI_RESET}\n\r"): return
        
    if is_connection_alive(writer, reader):
        await safe_write(writer, reader, "\n\rPress any key to finish...")
        await reader.read(1) 


# --- Main Flow (Terminal Hacking) ---

async def show_splash_screen(reader, writer):
    """Mostra lo splash screen e aspetta input dell'utente."""
    
    if not await safe_write(writer, reader, '\x1b[2J\x1b[H'): return False
    
    splash = get_robco_splash()
    if not await safe_write(writer, reader, splash): return False

    # Aspetta che l'utente prema un tasto
    while is_connection_alive(writer, reader):
        try:
            char = await reader.read(1)
            if char:  # Qualsiasi tasto premuto
                return True
        except (OSError, IOError, ConnectionResetError, BrokenPipeError, asyncio.IncompleteReadError):
            return False
            
    return False
    
async def handle_telnet(reader, writer):
    """Logica di gioco del server con gestione migliorata delle disconnessioni."""
    
    if not await show_splash_screen(reader, writer):
        return  # Connessione persa durante lo splash
    
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
            
            # Mostra la schermata di gioco
            for i, line in enumerate(screen_lines):
                if not is_connection_alive(writer, reader): break
                    
                attempt_display = ""
                if i >= num_lines - total_attempts:
                    attempt_index = i - (num_lines - total_attempts)
                    if attempt_index < len(guess_history):
                        guessed_word, likeness = guess_history[attempt_index]
                        attempt_display = f"{guessed_word} ({likeness}/{len(password)})"
                
                if not await safe_write(writer, reader, f"{line:<32}{attempt_display}\n\r"): break

            if not is_connection_alive(writer, reader): break

            if not await safe_write(writer, reader,
                f"\n\rAttempts remaining: {total_attempts - attempts_made}\n\r"
                "Enter password (or '.' to exit): "
            ): break

            # Leggi input utente
            guess = await safe_readline(reader, writer)
            
            if guess is None: break
            if not guess: continue

            if guess == '.': break

            if not await safe_write(writer, reader, '\x1b[2J\x1b[H'): break

            if guess == password:
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
                await safe_write(writer, reader, f"\n\r{ANSI_CYAN}Secondary System Detected... Launching C64 Match Mini-Game!{ANSI_RESET}\n\r")
                await asyncio.sleep(2)
                
                await run_matching_game(reader, writer)
                
                break # Exit the hacking game loop
                
            elif guess in chosen_screen_words:
                likeness = get_likeness(guess, password)
                if not await safe_write(writer, reader,
                    f"\n\rPassword not correct. \n\r"
                    f"[{likeness}/{len(password)}] letters correct.\n\r"
                ): break
                guess_history.append((guess, likeness))
                attempts_made += 1
            else:
                if not await safe_write(writer, reader, f"\n\rPassword not recognized. Not in the list.{ANSI_RESET}\n\r"): break
                attempts_made += 1
                
            if is_connection_alive(writer, reader):
                await asyncio.sleep(2)

        # Messaggi finali solo se la connessione è ancora attiva
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
