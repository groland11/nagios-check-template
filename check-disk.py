#!/usr/bin/env python3
import argparse
import logging
import sys

from subprocess import run, TimeoutExpired, PIPE

# Nagios return codes: https://nagios-plugins.org/doc/guidelines.html#AEN78
OK = 0
WARNING = 1
CRITICAL = 2
UNKNOWN = 3


def get_args():
    '''
    Defining command-line arguments
    '''
    parser = argparse.ArgumentParser(description="Disk Check")
    parser._optionals.title = "Options"
    parser.add_argument(
        '-m', '--mountpoint', nargs='?', required=False,
        help='mount point, default: "/"',
        dest='mount_point', type=str, default='/')
    parser.add_argument(
        '-w', '--warning', nargs='?', required=False,
        help='max. disk usage in percentage (warning), default: "90%%"',
        dest='maxsize_warning', type=str, default='80%')
    parser.add_argument(
        '-c', '--critical', nargs='?', required=False,
        help='max. disk usage in percentage (critical), default: "95%%"',
        dest='maxsize_critical', type=str, default='90%')
    parser.add_argument(
        '-v', '--verbose', required=False,
        help='enable verbose output', dest='verbose',
        action='store_true')
    parser.add_argument(
        '--log-file', nargs=1, required=False,
        help='file to log to, default: <stdout>',
        dest='logfile', type=str)

    args = parser.parse_args()

    return args


def get_logger(args: argparse.Namespace) -> logging.Logger:
    '''
    Defining logging
    '''
    if args.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO

    log_file = None
    if args.logfile:
        log_file = args.logfile[0]

    logging.basicConfig(filename=log_file,
                        format='%(levelname)s - %(message)s',
                        level=loglevel)

    return logging.getLogger(__name__)


def main():
    status = ""
    result = OK
    # Logging settings

    args = get_args()
    mylogger = get_logger(args)

    # Checking command line arguments
    wmax = int(args.maxsize_warning.replace("%", ""))
    cmax = int(args.maxsize_critical.replace("%", ""))
    if(wmax > cmax):
        wmax = cmax

    if(wmax < 0 or wmax > 100 or cmax < 0 or cmax > 100):
        mylogger.unknown("Invalid threshold for disk size")
        sys.exit(UNKNOWN)

    # Run check command
    try:
        cmd_df = ["df", "-h"]
        mylogger.debug(f'Running OS command line: {cmd_df}')
        process = run(cmd_df, check=True, timeout=10, stdout=PIPE)
    except (OSError, TimeoutExpired, ValueError) as e:
        mylogger.unknown(f'{e}')
        sys.exit(UNKNOWN)
    except Exception as e:
        mylogger.unknown(f'Unexpected exception: {e}')
        sys.exit(UNKNOWN)

    # Parse result
    used_space = -1
    try:
        for line in process.stdout.splitlines():
            (fs, sz, used, avail, use, mnt) = line.split(maxsplit=5)
            if(mnt.decode("utf-8") == args.mount_point):
                used_space = int(use.decode("utf-8").replace("%", ""))
        if(used_space < 0):
            mylogger.unknown(f'Unable to find {args.mount_point}')
            sys.exit(UNKNOWN)
    except Exception as e:
        mylogger.unknown(f'{e}')
        sys.exit(UNKNOWN)

    # Verify result and print output in Nagios format
    if used_space < wmax:
        print("OK - Usage of {1}: {0}%|{1}={0}".format(
            used_space,
            args.mount_point))
        sys.exit(OK)
    elif used_space >= cmax:
        print("CRITICAL - Usage of {1}: {0}%|{1}={0}".format(
            used_space,
            args.mount_point))
        sys.exit(CRITICAL)
    elif used_space >= wmax:
        print("WARNING - Usage of {1}: {0}%|{1}={0}".format(
            used_space,
            args.mount_point))
        sys.exit(WARNING)

if __name__ == "__main__":
    main()
