"""Connect to BeamNG.tech; does not load scenarios or control vehicles."""

import argparse
import os


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", default=os.environ.get("BNG_HOME"),
                        help="BeamNG.tech installation directory (or set BNG_HOME)")
    parser.add_argument("--port", type=int, default=25252)
    parser.add_argument("--existing", action="store_true",
                        help="Connect to an instance already listening on the port")
    args = parser.parse_args()
    if not args.existing and not args.home:
        parser.error("Pass --home /path/to/BeamNG.tech or set BNG_HOME")
    if args.home and not os.path.isdir(args.home):
        parser.error(f"Installation directory does not exist: {args.home}")

    try:
        from beamngpy import BeamNGpy
    except ImportError:
        parser.exit(1, "Install the dependency first: python -m pip install beamngpy\n")

    bng = BeamNGpy("localhost", args.port, home=args.home)
    try:
        bng.open(launch=not args.existing)
        print("Connected to BeamNG.tech")
    finally:
        bng.disconnect()


if __name__ == "__main__":
    main()
