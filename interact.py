import sys, os, tty, termios
from subprocess import run

tty.setcbreak(sys.stdin.fileno())

with open(sys.argv[1]) as f:
    input = f.read()
    output = input

max_w = max([len(l) for l in input.split('\n')])

def h():
    return os.get_terminal_size().lines


def w():
    return os.get_terminal_size().columns


def process_char(c, ctx):
    global output

    #  print(ctx['is_control_char'], ctx['is_arrow_key'], ord(c))
    #  continue

    if ctx['is_arrow_key']:
        if c == chr(65):
            ctx['h_offset'] = max(0, ctx['h_offset'] - 3)
        elif c == chr(66):
            ctx['h_offset'] = max(0, min(len(output) - (h() - 2), ctx['h_offset'] + 3))
        elif c == chr(68):
            ctx['w_offset'] = max(0, ctx['w_offset'] - 10)
        elif c == chr(67):
            ctx['w_offset'] = max(0, min(max_w - w(), ctx['w_offset'] + 10))

    if ctx['is_control_char']:
        if c == chr(91):
            ctx['is_arrow_key'] = True
            return

    if c == chr(27):
        ctx['is_control_char'] = True

        return
    else:
        ctx['is_control_char'] = False

    if c == chr(127):
        ctx['command'] = ctx['command'][:-1]
    elif not ctx['is_arrow_key'] and c != "\n":
        ctx['command'] += c

    command = ctx['command'].split(' ') if ctx['command'] else 'cat'

    try:
        proc = run(command,
                   capture_output=True,
                   input=input.encode('utf-8'))
        output = proc.stdout or proc.stderr
        output = output.decode('utf-8').split('\n')
    except FileNotFoundError:
       pass

    os.system('clear')

    for i in range(0, h() - 2):
        try:
            line = output[i + ctx['h_offset']][ctx['w_offset']:w() + ctx['w_offset']]
        except IndexError:
            line = ""

        print(line)

    sys.stdout.write('-' * w())
    sys.stdout.write("\n> " + ctx['command'])
    sys.stdout.flush()


ctx = {
    'command': '',
    'is_control_char': False,
    'is_arrow_key': False,
    'w_offset': 0,
    'h_offset': 0,
}

process_char('', ctx)

while True:
    try:
        process_char(sys.stdin.read(1), ctx)
    except KeyboardInterrupt as exc:
        sys.exit(0)
