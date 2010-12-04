import sys

debuglog = None

def debug(*args):
    if '-d' in sys.argv[1:]:
        s = ' '.join([str(a) for a in args]) + '\n'
        sys.stderr.write(s)
        sys.stderr.flush()
    if '-dl' in sys.argv[1:]:
        global debuglog
        if not debuglog:
            debuglog = file('debuglog.txt','w+')
        s = ' '.join([str(a) for a in args]) + '\n'
        sys.stderr.write(s)
        sys.stderr.flush()
        debuglog.write(s)
        debuglog.flush()
    pass

