# AI Subtitle Translator

A robust, cross-platform desktop application built with Python and CustomTkinter for translating subtitle files (VTT/SRT) using various AI APIs.

The application allows defining pre-contexts to ensure highly accurate, context-aware translations while avoiding formatting problems in subtitle structures.

## Features

- **Multi-API Support**: Out-of-the-box support for **OpenAI** and **Gemini** models.
- **Custom Providers**: Easily configure custom OpenAI-compatible endpoints by specifying a Base URL, Provider ID, and Custom Auth Headers (useful for self-hosted LLMs or third-party API aggregators).
- **Auto-Rotation & Rate Limit Resilience**: Assign multiple API keys to any provider. The application will seamlessly fallback and rotate to the next key whenever an HTTP 429 Rate Limit exception is caught.
- **Background Processing**: Heavy string processing and network requests execute in background threads, keeping the User Interface perfectly responsive.
- **Pre-Context Instructions**: Add specific background notes and logic instructions directly accessible to the LLM agent before it translates your VTT chunks.

## Project Structure

This project follows SOLID principles to ensure maintainability and high decoupling:
- `main.py` & `ui/`: Defines the pure frontend GUI layer running on `CustomTkinter`.
- `core/vtt_parser.py`: Pure logic for chunking and combining VTT documents.
- `core/translator.py`: Implementation of `BaseProvider` logic and Key Management strategy.
- `core/engine.py`: Bridging layer orchestrating prompts with system rules to avoid splitting subtitle lines.

## How to Run

1. Clone or clone the repository.
2. Initialize virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```

## How to Build Executables

To build standalone packages natively for macOS (`.app`) or Windows (`.exe`):

- **MacOS / Linux**:
  Run `./build.sh` within the virtual environment. Ensure you have given execute permissions: `chmod +x build.sh`.
  
- **Windows**:
  Run `pyinstaller --noconfirm --onedir --windowed --name "SubtitleTranslator" --add-data "core;core" --add-data "ui;ui" main.py` using your command prompt.

The output will be found in the `dist/` directory.

## License

MIT License.
