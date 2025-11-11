import os
from pathlib import Path
from dotenv import load_dotenv
import multiprocessing
import sys
from jafar.voice.jafar_core import main as voice_main
from jafar.cli.main import main as cli_main

def run_voice_assistant(interrupt_event, queue, main_exit_event):
    """Wrapper to run the voice assistant in a separate process."""
    print("Starting voice assistant process...")
    try:
        voice_main(interrupt_event, queue, main_exit_event)
    except KeyboardInterrupt:
        print("Voice assistant process interrupted.")
    finally:
        print("Voice assistant process finished.")

def run_cli():
    """Wrapper to run the CLI."""
    print("Starting CLI...")
    try:
        cli_main()
    except KeyboardInterrupt:
        print("\nCLI interrupted.")
    finally:
        print("CLI finished.")

if __name__ == "__main__":
    # Load environment variables from .env file
    dotenv_path = Path(__file__).parent / '.env'
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path)
        print(f".env file loaded from {dotenv_path}")
    else:
        print("Warning: .env file not found. API keys may not be available.")

    # Create multiprocessing components
    interrupt_event = multiprocessing.Event()
    main_exit_event = multiprocessing.Event()
    queue = multiprocessing.Queue()

    # Create and start the voice assistant process
    voice_process = multiprocessing.Process(
        target=run_voice_assistant,
        args=(interrupt_event, queue, main_exit_event)
    )
    voice_process.start()

    # Run the CLI in the main process
    run_cli()

    # When CLI exits, signal the voice assistant to exit
    print("CLI has exited. Signaling voice assistant to terminate...")
    main_exit_event.set()

    # Wait for the voice process to finish
    voice_process.join(timeout=5)
    if voice_process.is_alive():
        print("Voice assistant process did not terminate gracefully. Forcing termination.")
        voice_process.terminate()

    print("Jafar Unified has shut down.")
