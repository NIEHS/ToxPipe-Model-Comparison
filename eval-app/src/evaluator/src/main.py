from evaluation import runTest
import sys
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("eval", help="Eval set name")
    parser.add_argument("-r", "--replace", action="store_true", help="Replace execution and evaluation")
    parser.add_argument("-s", "--skip-run", action="store_true", help="Skip execution, run evaluation only")

    if len(sys.argv) == 1:
        parser.print_help()
        exit(1)

    args = parser.parse_args()

    runTest(args.eval, replace=args.replace, skip_run=args.skip_run)