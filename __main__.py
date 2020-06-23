import argparse

from .main.drivers.driver import run

def cli_run(args):
    run(args.obs_ticket, args.data, args.config, args.filter, args.logger)

def main():
    parser = argparse.ArgumentParser(description='Telescope automation code')
    subparsers = parser.add_subparsers()
    run_driver = subparsers.add_parser('run', help='Start an observation run')
    run_driver.add_argument('obs_ticket',
                            help='Path to observation ticket JSON file.')
    run_driver.add_argument('--data', '-d', metavar='PATH', dest='data',
                            help='Manual save path for CCD image files.')
    run_driver.add_argument('--config', '-c', metavar='PATH', dest='config',
                            help='Manual file path to the general config json file.')
    run_driver.add_argument('--filter', '-f', metavar='PATH', dest='filter',
                            help='Manual file path to the filter wheel config json file.')
    run_driver.add_argument('--logger', '-l', metavar='PATH', dest='logger',
                            help='Manual file path to the logging config json file.')
    run_driver.set_defaults(func=cli_run)
    
    args = parser.parse_args()
    args.func(args)
    
if __name__ == '__main__':
    main()