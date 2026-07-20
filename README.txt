UZEX CLOCK V2

The old version used an HTTP HEAD request. UZEX can forcibly close that request on Windows.
This version uses a normal GET request and falls back to Windows curl.exe.

1. Extract the ZIP.
2. Open Command Prompt in the folder.
3. Run: python server.py
4. Open: http://127.0.0.1:8000

Do not open index.html directly. Close the old server first with Ctrl+C.
