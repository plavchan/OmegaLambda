import argparse
import os

from main.drivers.driver import run

def cli_run(args):
    run(args.folder, args.obs_ticket, args.filter)

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    run_driver = subparsers.add_parser('run')
    run_driver.add_argument('folder',
                            help='Path where images are to be saved.')
    run_driver.add_argument('obs_ticket',
                            help='Path to observation ticket JSON file.')
    run_driver.add_argument('filter',
                            help='Path to filter JSON file.')
    run_driver.set_defaults(func=cli_run)