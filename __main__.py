import argparse

from .main.drivers.driver import run

def cli_run(args):
    run(args.obs_ticket, args.datapath)

def main():
    parser = argparse.ArgumentParser(description='Telescope automation code')
    subparsers = parser.add_subparsers()
    run_driver = subparsers.add_parser('run', help='Start an observation run')
    run_driver.add_argument('obs_ticket',
                            help='Path to observation ticket JSON file.')
    run_driver.add_argument('--manualpath', '-mp', metavar='PATH', dest='datapath',
                            help='Toggle for manual data filepath saving.')
    run_driver.set_defaults(func=cli_run)
    
    args = parser.parse_args()
    args.func(args)
    
if __name__ == '__main__':
    main()