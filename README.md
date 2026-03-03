# RobCo_BBS
*_A simple RobCo terminal hack game running on telnet_*
________________________
- launch it with `python robco.py`
- launch with `python robco-c64.py` for C64 ASCII compliant terminal
- launch with `python robco-c64+match.py` for C64 safe terminal hacking game with matching game as 2nd level
- launch with `python robco-c64-full.py` for C64 safe terminal hacking game with three levels

- connect to the game with `telnet (your server ip) 6023`
- 
- full, 3 level c64 version, requires a chatgpt, gemini, or claude API key
make sure to use the following to set the API key as an environment variable
```bash
pip install openai
export OPENAI_API_KEY=your_chatgpi_api_key_here
export GEMINI_API_KEY=your_gemini_api_key_here
export CLAUDE_API_KEY=your_claude_api_key_here
```
WARNING: please do NOT modify the code to set your keys in external files, or worse, embed them, directly, in the python code. This is very insecure.
