import sys
import time

debuglog = None
maxtime = 0.0
maxtimeTurn = 0

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

def debugTime(begintime, gameturn):
    global maxtime, maxtimeTurn
    endtime = time.clock()
    if maxtime < (endtime - begintime):
        maxtime = (endtime - begintime)
        maxtimeTurn = gameturn
    #debug("Clock: ", (endtime - begintime), 's Max:', maxtime, 's @', maxtimeTurn)
    s = ' '.join(["Clock: %ss" % (endtime - begintime), "Max: %ss @%s" % (maxtime, maxtimeTurn)]) + '\n'
    sys.stderr.write(s)
    #sys.stderr.flush()
    

