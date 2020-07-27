import argparse

from .main.drivers.driver import run


def cli_run(args):
    """
    Description
    -----------
    Passes the CLI arguments into the run function in driver.

    Parameters
    ----------
    args : ANY TYPE
        Arguments passed in from the command line.

    Returns
    -------
    None.

    """
    run(args.obs_tickets, args.data, args.config, args.filter, args.logger, args.shutdown, args.calibration)


def main():
    """
    Description
    -----------
    Defines the 'run' CLI command and arguments.

    Returns
    -------
    None.

    """
    parser = argparse.ArgumentParser(description='Telescope automation code')
    subparsers = parser.add_subparsers()
    run_driver = subparsers.add_parser('run', help='Start an observation run')
    run_driver.add_argument('obs_tickets', nargs='+',
                            help='Paths to each observation ticket, or 1 path to a directory with observation tickets.')
    run_driver.add_argument('--data', '-d', metavar='PATH', dest='data',
                            help='Manual save path for CCD image files.')
    run_driver.add_argument('--config', '-c', metavar='PATH', dest='config',
                            help='Manual file path to the general config json file.')
    run_driver.add_argument('--filter', '-f', metavar='PATH', dest='filter',
                            help='Manual file path to the filter wheel config json file.')
    run_driver.add_argument('--logger', '-l', metavar='PATH', dest='logger',
                            help='Manual file path to the logging config json file.')
    run_driver.add_argument('--noshutdown', '-ns', action='store_false', default='store_true', dest='shutdown',
                            help='Use this option if you do not want to shutdown after running the tickets. '
                            'Note this will also stop the program from taking any darks and flats if the calibration '
                            'time is set to end.')
    run_driver.add_argument('--nocalibration', '-nc', action='store_false', default='store_true', dest='calibration',
                            help='This option is a placeholder for future additions.  Currently it will not do '
                                 'anything.')
    run_driver.set_defaults(func=cli_run)
    
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':      # Run the main function when -omegalambda is called.
    main()
