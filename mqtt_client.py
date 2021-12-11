#! /usr/bin/python3

"""
MQTT Client
"""
import logging
import argparse
import mqtt

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog='mqtt-client', description="Run a publisher or a subsriber. Publisher read values (as strings) from the standard input and Subscriber displays the values on the standard output.")
    parser.add_argument('-H', '--host', type=str, default="localhost",
                        help="address of the broker (default value: localhost)")
    parser.add_argument('-p', '--port', type=int, default=mqtt.PORT,
                        help=f"port used by the broker (default value: {mqtt.PORT})")
    parser.add_argument('-i', '--id', type=str,
                        default="pub 001", help="Only for publisher")
    parser.add_argument('-l', '--log', type=str, default='',
                        help="Filename to store log informations")
    parser.add_argument('--debug',  action='store_true',
                        help="log debug informations")
    parser.add_argument('-r', '--retain', action='store_true',
                        help="Only for publisher: indicates that the values published must be retained by the broker")
    parser.add_argument('-t', '--topic', type=str, required=True)
    parser.add_argument('cmd', type=str, choices=[
                        'pub', 'sub'], help="indicate if the client is a publisher (pub) or a subscriber (sub)")
    args = parser.parse_args()

    # logging
    loglevel = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(format='%(levelname)s:%(message)s',
                        level=loglevel, filename=args.log)

    # run publisher client
    if(args.cmd == 'pub'):
        topic = args.topic
        pub_id = args.id
        mqtt.run_publisher((args.host, args.port),
                           args.topic, args.id, args.retain)

    # run subscriber client
    if(args.cmd == 'sub'):
        topic = args.topic
        sub_id = args.id
        mqtt.run_subscriber((args.host, args.port), args.topic, sub_id)

# EOF