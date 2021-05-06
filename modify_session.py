import argparse, os, sys, json

parser = argparse.ArgumentParser(description="Modify db session data")
parser.add_argument('--clear', help="Clear current session", action='store_true')
parser.add_argument('--connection', help="Set current connection")

args = parser.parse_args()

if args.clear:
    try:
        os.remove('session.json')
    except FileNotFoundError:
        pass

    sys.exit(0)

try:
    with open('session.json', 'r') as f:
        session = json.loads(f.read())
except (FileNotFoundError, json.decoder.JSONDecodeError):
    session = {}

if args.connection:
    session['connection'] = args.connection

with open('session.json', 'w+') as f:
    f.write(json.dumps(session))
