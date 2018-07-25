#!/usr/bin/env python

"""cons3rt -- entry point for pycons3rtapi

Usage: %s [options]

Options:
setup -- configures

"""

import sys
import argparse

from cons3rtconfig import manual_config

# Commands for setting up the cons3rtapi configuration
setup_command_options = [
    'setup',
    'config',
    'configure'
]

# List of valid CLI commands
valid_commands = setup_command_options

# String representation of valid commands
valid_commands_str = 'Valid commands: {c}'.format(c=', '.join(valid_commands))


def main():
    parser = argparse.ArgumentParser(description='CONS3RT command line interface (CLI)')
    parser.add_argument('command', help='Command for the cons3rt CLI')
    args = parser.parse_args()

    # Get the command
    command = args.command.strip()

    if command not in valid_commands:
        print('Invalid command found [{c}]\n'.format(c=command) + valid_commands_str)

    if args.command in setup_command_options:
        manual_config()
    return 0


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
