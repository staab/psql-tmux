import argparse, sys, json, time, os, csv
from subprocess import run, PIPE
from tempfile import NamedTemporaryFile
from pynput.keyboard import Key, Listener

def die(message):
    print(message)
    sys.exit(1)


def watch_input(cb):
    s = ''

    def press(key):
        nonlocal s

        if key == Key.esc:
            return False

        if key == Key.backspace:
            s = s[:-1]
        elif key == Key.space:
            s += ' '
        elif hasattr(key, 'char'):
            s += key.char

        cb(s)

    with Listener(on_press=press) as listener:
        listener.join()


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


def pipe_to_jq(fh, expr):
    cat_stream = run(['cat', fh.name], stdout=PIPE)
    jq_stream = run(['jq', '-SC', expr],
                    capture_output=True,
                    input=cat_stream.stdout)

    return jq_stream

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
                    choices=["libreoffice", "default", "jq"])

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
    input("Press any key to close.")

if args.output == 'jq':
    csv_fh = pipe_to_csv(command)
    reader = csv.DictReader(csv_fh)
    json_fh = mktmp(json.dumps(list(reader)), '.json')
    jq_stream = pipe_to_jq(json_fh, '.')
    out = jq_stream.stdout
    err = jq_stream.stderr

    def print_jq(expr):
        os.system('clear')

        print('>', expr)
        print(out.decode('utf-8'))
        print(err.decode('utf-8'))

    print_jq('')

    @watch_input
    def run_jq(expr):
        global out
        global err

        s = pipe_to_jq(json_fh, expr)

        err = s.stderr

        if not s.stderr:
            out = s.stdout

        print_jq(expr)


if args.output == 'libreoffice':
    fh = pipe_to_csv(command)

    run(['libreoffice', '--nologo', fh.name])

