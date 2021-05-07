import argparse, sys, json, time, os, csv, traceback
from subprocess import run, PIPE
from tempfile import NamedTemporaryFile

parser = argparse.ArgumentParser(description="Execute a query")
parser.add_argument('--query',
                    help="The query to execute")
parser.add_argument('--connection',
                    help="The name of the connection to use")
parser.add_argument('--interactive',
                    help="Whether to pipe output to interactive prompt",
                    action='store_true')
parser.add_argument('--output',
                    help="Output mode",
                    choices=["default", "libreoffice", "csv", "json"])


def main(command, output, interactive):
    if output == 'default':
        return print_output(get_stdout(command), interactive)

    csv_data = get_stdout(command + ['--csv'])

    if output == 'csv':
        print_output(csv_data, interactive)

    if output == 'json':
        reader = csv.DictReader(mktmp(csv_data, '.csv'))
        json_data = json.dumps(list(reader)).encode('utf-8')
        json_data = get_stdout(['jq'], input=json_data)

        print_output(json_data, interactive)

    if output == 'libreoffice':
        fh = mktmp(csv_data, '.csv')
        run(['libreoffice', '--nologo', fh.name])


# Utilities


def die(message):
    print(message)
    sys.exit(1)


def get_stdout(command, **kw):
    proc = run(command, capture_output=True, **kw)

    if proc.stderr:
        print("Query failed!")
        die(proc.stderr)

    return proc.stdout.decode('utf-8')


def mktmp(contents, suffix='.txt'):
    if type(contents) == bytes:
        contents = contents.decode('utf-8')

    f = NamedTemporaryFile('w+', suffix=suffix)
    f.write(contents)
    f.seek(0)

    return f


def get_opts(args):
    try:
        with open('config.json', 'r') as f:
            config = json.loads(f.read())
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        die("config.json not found or corrupted!")

    defaults = config.get('defaults', {})
    connections = config.get('connections', {})
    conn_name = args.connection or defaults.get('connection')

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

        print(f"\nYou are using your \033[1m{conn_name}\033[0m connection.\n")

        if 'y' != input("Are you sure you want to run this query? (y/n) "):
            die("Query execution aborted")

    return {
        'output': args.output or defaults.get('output', 'default'),
        'command': ['psql', connection['url'], '-c', query],
        'interactive': (
            args.interactive if args.interactive is not None
            else defaults.get('interactive')
        ),
    }


def print_output(data, interactive):
    if interactive:
        fh = mktmp(data)
        run(['cateract', fh.name], stdin=sys.stdin)
    else:
        print("Results:\n")
        print(data)
        input("Press enter to exit.")


if __name__ == '__main__':
    try:
        main(**get_opts(parser.parse_args()))
    except Exception as exc:
        traceback.print_exc()
        input('')
