import argparse, sys, json, time, os, csv
from subprocess import run, PIPE
from tempfile import NamedTemporaryFile


def die(message):
    print(message)
    sys.exit(1)


def mktmp(contents, suffix):
    if type(contents) == bytes:
        contents = contents.decode('utf-8')

    f = NamedTemporaryFile('w+', suffix=suffix)
    f.write(contents)
    f.seek(0)

    return f


def pipe_to_csv(command):
    p = run(command + ['--csv'], stdout=PIPE)

    return mktmp(p.stdout, suffix='.csv')


try:
    with open('config.json', 'r') as f:
        config = json.loads(f.read())
except (FileNotFoundError, json.decoder.JSONDecodeError):
    die("config.json not found or corrupted!")


defaults = config.get('defaults', {})
connections = config.get('connections', {})

parser = argparse.ArgumentParser(description="Execute a query in the current session")
parser.add_argument('--query',
                    help="The query to execute")
parser.add_argument('--output',
                    help="Output mode",
                    default=defaults.get('output', 'default'),
                    choices=["libreoffice", "default", "jq", "json"])

args = parser.parse_args()

try:
    with open('session.json', 'r') as f:
        session = json.loads(f.read())
except (FileNotFoundError, json.decoder.JSONDecodeError):
    die("session.json not found or corrupted!")

conn_name = session['connection']

if not conn_name:
    die("No connection selected")

connection = connections.get(conn_name)

if not connection:
    die(f"No info for connection {conn_name}")

query = args.query
if connection.get('prepend_sql'):
    query = connection['prepend_sql'] + query

if 'confirm' in connection.get('flags', []):
    print("You are about to run the following query:\n")

    for line in query.split("\n"):
        print("  " + line)

    print(f"\nYou are using your \033[1m{conn_name}\033[0m connection.\n\n")

    if 'y' != input("Are you sure you want to run this query? (y/n) "):
        die("Query execution aborted")

command = ['psql', connection['url'], '-c', query]

if args.output == 'default':
    print("Results:\n")
    run(command)
    input("Press enter to exit.")

if args.output == 'json':
    csv_fh = pipe_to_csv(command)
    reader = csv.DictReader(csv_fh)
    json_data = json.dumps(list(reader))
    run(['jq', '-SC', '.'], input=json_data.encode('utf-8'))
    input("\nPress enter to exit.")

if args.output == 'jq':
    csv_fh = pipe_to_csv(command)
    reader = csv.DictReader(csv_fh)
    json_fh = mktmp(json.dumps(list(reader)), '.json')
    run(['python', './jq_interactive.py', json_fh.name],
        stdin=sys.stdin)

if args.output == 'libreoffice':
    fh = pipe_to_csv(command)

    run(['libreoffice', '--nologo', fh.name])

