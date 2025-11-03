#!/usr/bin/env python3
"""
DCS Natural Language ATC - Main Application Entry Point

This application provides natural language ATC services for DCS World
using Ollama for AI processing.
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dcs_nl_atc.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def setup_ollama():
    """Initialize and start Ollama"""
    from src.ollama_manager import OllamaManager

    logger.info("Setting up Ollama...")
    ollama = OllamaManager()

    if not ollama.start():
        logger.error("Failed to start Ollama")
        return None

    logger.info("Ensuring model is downloaded...")
    if not ollama.ensure_model():
        logger.warning("Failed to download model, but continuing...")

    return ollama


def configure_dcs(dcs_path=None):
    """Configure DCS integration"""
    from src.dcs_configurator import DCSConfigurator

    logger.info("Configuring DCS integration...")
    configurator = DCSConfigurator()

    if not configurator.configure(dcs_path):
        logger.error("Failed to configure DCS")
        return False

    # Display status
    status = configurator.get_status()
    logger.info(f"DCS Configuration Status:")
    logger.info(f"  Detected: {status['dcs_detected']}")
    logger.info(f"  Variant: {status['dcs_variant']}")
    logger.info(f"  Path: {status['dcs_path']}")
    logger.info(f"  ATC Configured: {status['atc_configured']}")

    return True


def unconfigure_dcs():
    """Remove DCS integration"""
    from src.dcs_configurator import DCSConfigurator

    logger.info("Removing DCS integration...")
    configurator = DCSConfigurator()

    if not configurator.unconfigure():
        logger.error("Failed to remove DCS integration")
        return False

    logger.info("DCS integration removed successfully")
    return True


def test_nlp():
    """Test NLP processing"""
    from src.nlp_processor import NLPProcessor

    logger.info("Testing NLP processor...")

    processor = NLPProcessor()

    test_commands = [
        "Viper 1-1, request takeoff clearance",
        "Request landing clearance runway 27 Left",
        "Request climb to flight level 350",
        "Turn right heading 270",
        "Request taxi to active runway",
    ]

    for command in test_commands:
        logger.info(f"\nTesting: {command}")
        result = processor.process(command)
        logger.info(f"Intent: {result['intent']}")
        logger.info(f"Entities: {result['entities']}")
        logger.info(f"Response: {result['response']}")


def run_interactive():
    """Run interactive ATC session"""
    from src.nlp_processor import NLPProcessor

    logger.info("Starting interactive ATC session...")
    logger.info("Type 'quit' or 'exit' to stop\n")

    processor = NLPProcessor()

    while True:
        try:
            command = input("Pilot: ").strip()

            if command.lower() in ['quit', 'exit', 'q']:
                break

            if not command:
                continue

            result = processor.process(command)
            print(f"ATC: {result['response']}\n")

        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error processing command: {e}")

    logger.info("Interactive session ended")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='DCS Natural Language ATC System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --configure              # Configure DCS integration
  %(prog)s --test-nlp               # Test NLP processing
  %(prog)s --interactive            # Run interactive session
  %(prog)s --unconfigure            # Remove DCS integration
        """
    )

    parser.add_argument(
        '--configure',
        action='store_true',
        help='Configure DCS World integration'
    )

    parser.add_argument(
        '--unconfigure',
        action='store_true',
        help='Remove DCS World integration'
    )

    parser.add_argument(
        '--dcs-path',
        type=str,
        help='Manual DCS installation path'
    )

    parser.add_argument(
        '--test-nlp',
        action='store_true',
        help='Test NLP processing with sample commands'
    )

    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Run interactive ATC session'
    )

    parser.add_argument(
        '--setup-ollama',
        action='store_true',
        help='Setup and test Ollama'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("=" * 60)
    logger.info("DCS Natural Language ATC System")
    logger.info("=" * 60)

    try:
        # Setup Ollama if requested
        if args.setup_ollama:
            ollama = setup_ollama()
            if ollama:
                logger.info("Ollama setup complete")
                # Test chat
                logger.info("Testing Ollama chat...")
                response = ollama.chat("Say hello")
                logger.info(f"Response: {response}")
            return 0

        # Configure DCS
        if args.configure:
            dcs_path = Path(args.dcs_path) if args.dcs_path else None
            if configure_dcs(dcs_path):
                logger.info("Configuration complete!")
                return 0
            return 1

        # Unconfigure DCS
        if args.unconfigure:
            if unconfigure_dcs():
                return 0
            return 1

        # Test NLP
        if args.test_nlp:
            test_nlp()
            return 0

        # Interactive mode
        if args.interactive:
            run_interactive()
            return 0

        # No arguments, show help
        parser.print_help()
        return 0

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        return 130
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
