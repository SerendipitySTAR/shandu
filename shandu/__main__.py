"""
Shandu package main entry point.
Allows running shandu as a module with `python -m shandu`.
"""

from .cli import cli

if __name__ == "__main__":
    cli()
