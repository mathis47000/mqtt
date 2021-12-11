#!/usr/bin/python3

"""
MQTT Server Command.
"""
import logging
import argparse
import mqtt

HOST = ''
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='mqtt-server', description="Run the broker")
    parser.add_argument('-p', '--port', type=int, default=mqtt.PORT,
                        help=f"port used by the broker (default value: {mqtt.PORT})")
    parser.add_argument('-l', '--log', type=str, default='',
                        help="Filename to store log informations")
    parser.add_argument('--debug',  action='store_true',
                        help="log debug informations")
    args = parser.parse_args()

    # logging
    loglevel = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(format='%(levelname)s:%(message)s',
                        level=loglevel, filename=args.log)

    # run main server loop
    mqtt.run_server(('', args.port))