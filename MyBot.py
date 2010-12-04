#!/usr/bin/env python
#
# TODO: implement predictive reinforcements, which follow enemy's major
# movements on the frontline

# TODO: Make cooperative assault work! Gets stuck on the farthest planet's
# sendout.  Gotta make sure that if a decision is made, it gets executed in
# full

# TODO: Implement a new entity: "PlanetGroup" -- to be used to plan defence and
# attacks in a cooperative manner, without compromising defence (i.e. when safe
# dispatch limit is calculated for a group of e.g. two +5 planets, they shuould
# not dispatch their ships both, naively (and fatally) depending on each other
# for subsequent defence. Instead, a shared safe dispatch limit must be applied
# to that group, i.e. when both are attacking, their maximum dispatch must not
# be more than that.  Possible way to implement it is to probably just
# calculate single and cumulative dispatch limits separately.

# TODO: add a "celebration" feature ;)

from PlanetWars import PlanetWars, Fleet, mapFleetsToTurns
from debug import debug, debugTime
import sys, time, math

gameturn = 0

def debugStatus(pw):
    if '-d' not in sys.argv[1:] and '-dl' not in sys.argv[1:]:
        return
     
    debug("\n\n##################################################");
    debug("Turn", gameturn)
    mplanets = pw.MyPlanets()
    eplanets = pw.EnemyPlanets()
    mfleets = pw.MyFleets()
    mfleets_size = sum([mf.NumShips() for mf in mfleets])
    mplanets_size = sum([mp.NumShips() for mp in mplanets])
    
    debug("My planets:", len(mplanets), ' Planets size:', mplanets_size, 'Total size:', mplanets_size + mfleets_size)

    for mp in mplanets:
        ep,epdist = mp.ClosestEnemy()
        debug(mp.ID(), " +", mp.GrowthRate(), " ^", mp.NumShips(), 'Closest e:', ep.ID(), '@', epdist, ' ^', ep.NumShips())
    
    mrfleets = filter(lambda f:  pw.GetPlanet(f.Destination()).Owner() == 1, mfleets)
    debug("My fleets (reinforcements):", len(mrfleets), 'Total size:', mfleets_size)
    mrfleets.sort(lambda f,s: cmp(f.Destination(), s.Destination()) or cmp(f.Source(), s.Source()))
    for mf in mrfleets:
        debug(">> ", mf.Source(), '>>', mf.Destination(), " +", mf.NumShips(), " @", mf.TurnsRemaining())
    
    mafleets = filter(lambda f: pw.GetPlanet(f.Destination()).Owner() != 1, mfleets)
    debug("My fleets (attacks):", len(mafleets))
    mafleets.sort(lambda f,s: cmp(f.Destination(), s.Destination()) or cmp(f.Source(), s.Source()))
    for mf in mafleets:
        sp = pw.GetPlanet(mf.Source())
        dp = pw.GetPlanet(mf.Destination())
        dest_ships = pw.GetPlanet(mf.Destination()).NumShips()
        debug(">> ", mf.Source(), '>>', mf.Destination(), " ^", mf.NumShips(), 'vs', dest_ships, " @", mf.TurnsRemaining())

    efleets = pw.EnemyFleets()
    efleets_size = sum([ef.NumShips() for ef in efleets])
    
    eplanets_size = sum([ep.NumShips() for ep in eplanets])
    debug("Enemy planets:", len(eplanets), ' Planets size:', eplanets_size, 'Total size:', eplanets_size + efleets_size)
    for ep in eplanets:
        mp,mpdist = ep.ClosestFriend()
        debug(ep.ID(), " +", ep.GrowthRate(), " ^", ep.NumShips(), 'Closest mp:', mp.ID(), '@', mpdist, ' ^', mp.NumShips())
    
    erfleets = filter(lambda f: pw.GetPlanet(f.Destination()).Owner() == 2, efleets)
    debug("Enemy fleets (reinforcements):", len(erfleets), 'Total size:', efleets_size)
    erfleets.sort(lambda f,s: cmp(f.Destination(), s.Destination() or cmp(f.Source(), s.Source())))
    for ef in erfleets:
        debug("<< ", ef.Source(), '>>', ef.Destination(),  ' +', ef.NumShips(), " @", ef.TurnsRemaining())
    
    eafleets = filter(lambda f: pw.GetPlanet(f.Destination()).Owner() != 2, efleets)
    debug("Enemy fleets (attacks):", len(eafleets), 'Total size:', efleets_size)
    eafleets.sort(lambda f,s: cmp(f.Destination(), s.Destination() or cmp(f.Source(), s.Source())))
    for ef in eafleets:
        dest_ships = pw.GetPlanet(ef.Destination()).NumShips()
        debug("<< ", ef.Source(), '>>', ef.Destination(),  ' ^', ef.NumShips(), 'vs', dest_ships, " @", ef.TurnsRemaining())
    
    fleets = pw.Fleets()
    eos = estimatedCharacterOffenceStrength(pw, 2, eplanets, mplanets, efleets, mfleets)
    eds = estimatedCharacterDefenceStrength(eplanets, fleets)
    mos = estimatedCharacterOffenceStrength(pw, 1, mplanets, eplanets, mfleets, efleets)
    mds = estimatedCharacterDefenceStrength(mplanets, fleets)
    
    my_production = pw.MyProduction() 
    enemy_production = pw.EnemyProduction()
    
    enemy_threat = -eos - mds
    my_threat = mos + eds
    
    proddiff = float(my_production - enemy_production)

    debug("# My total strength,    >>", mos, ' ||', mds, ' $', my_production, \
        ' %>', my_threat, ' etd:', my_threat / proddiff if proddiff != 0 else 'never')
    debug("# Enemy total strength, >>", -eos, ' ||', -eds, ' $', enemy_production, \
        ' %>', enemy_threat, ' etd:', enemy_threat / -proddiff if proddiff != 0 else 'never')
    
def DoTurn(pw):
    global gameturn
    if len(pw.MyPlanets()) == 0:
        return
    debugStatus(pw)
    debug("REINFORCEMENTS AND DEFENCE #######################");
    reserveOwnPlanetsDefence(pw)
    defendOwnPlanets(pw)
    
    #debug("RECAPTURE-----------------------------------------");
    #recapturePlanets(pw)
    
    debug("ATTACK--------------------------------------------");
    attackEnemy(pw)
    
    debug("REINFORCEMENTS -----------------------------------");
    reinforceOwn(pw)
    gameturn += 1

def getFleetTurns(fleets):
    return set(map(lambda f: f.TurnsRemaining(), fleets))

def mapFleetsToDestinations(fleets):
    fleets.sort(lambda f,s: cmp(f.Destination(), s.Destination()))
    curdp = min([ef.Destination() for ef in fleets])
    
    curdp_fleets = []
    dp_list = [(curdp, curdp_fleets)]
    
    for ef in fleets:
        dp = ef.Destination()
        if curdp != dp:
            curdp = dp
            curdp_fleets = []
            dp_list.append((curdp, curdp_fleets))
        curdp_fleets.append(ef)
    
    dp_list.sort(lambda f,s: cmp(f[0], s[0]))
    return dp_list

def reserveOwnPlanetsDefence(pw):
    dplanets = pw.MyPlanets()
    eplanets = pw.EnemyPlanets()
    fleets = pw.Fleets()
    
    for dp in dplanets:
        incomingFleets = dp.IncomingFleets()
        if len(incomingFleets) == 0:
            continue
        
        closestEnemyDistance = dp.ClosestEnemyDistance() if len(eplanets) > 0 else sys.maxint
        spds,spowner = dp.CombineIncomingFleets(turnlimit=0)
	
	spds = dp.FindMinimumStrength()

        reserve = max(dp.NumShips() - spds, 0)
        if reserve <= 0:
            continue
        
        debug(">>> RESERVING FOR DEFENCE in", dp.ID(), ":", reserve, 'now:', dp.NumShips(), 'then:', spds)
        dp.ReserveShips(reserve)

def defendOwnPlanets(pw):
    """ Manage defence of own planets """
    fleets = pw.Fleets()
    mfleets = pw.MyFleets()
    splanets = pw.MyPlanets()
    dplanets = set(pw.MyPlanets())
    eplanets = pw.EnemyPlanets()
    
    mfleetsOffensive = filter(lambda mf: pw.GetPlanet(mf.Destination()).Owner() != 1, mfleets)
    dplanets |= set(map(lambda mf: pw.GetPlanet(mf.Destination()), mfleetsOffensive))
    dplanetid = map(lambda p: p.ID(), dplanets)
    efleets = filter(lambda ef: ef.Destination() in dplanetid, pw.EnemyFleets())
    
    if len(efleets) == 0:
        return
    
    # map fleets to planets:
    dpfleets = mapFleetsToDestinations(efleets)
    splanets.sort(lambda f,s: -cmp(f.NumShips(), s.NumShips()))
    
    for dpid, defleets in dpfleets:
        sent = 0
        dp = pw.GetPlanet(dpid)
        farfleetdist = max(map(lambda f: f.TurnsRemaining(), defleets))
        dpds,dpowner = dp.CombineIncomingFleets(turnlimit=farfleetdist)
        debug("RESCUE FOR:", dp.ID(), 'dpds:', dpds, 'owner:', dpowner)
        
        if dpowner == 1 or len(defleets) == 0:
            #debug("NONE. dpowner:", dpowner, "defleets:", defleets)
            continue
        
        rescuePlanets = createRescuePlan(dp, fleets, defleets, 0, farfleetdist, splanets, eplanets)
        executeRescuePlan(pw, dp, rescuePlanets, splanets)

def recapturePlanets(pw):
    """ Opportunistic weak enemy recapture """
    fleets = pw.Fleets()
    mfleets = pw.MyFleets()
    splanets = pw.MyPlanets()
    dplanets = set(pw.NeutralPlanets() + filter(lambda p: not p.IsRescued(), pw.MyPlanets()))
    eplanets = pw.EnemyPlanets()
    
    dplanetid = map(lambda dp: dp.ID(), dplanets)
    efleets = filter(lambda ef: ef.Destination() in dplanetid, pw.EnemyFleets())
    
    if len(efleets) == 0:
        return
    
    # map fleets to planets:
    dpfleets = mapFleetsToDestinations(efleets)
    splanets.sort(lambda f,s: -cmp(f.NumShips(), s.NumShips()));
    
    for dpid, defleets in dpfleets:
        dp = pw.GetPlanet(dpid)
        turnlimit = dp.ClosestEnemyDistance() if len(eplanets) > 0 else 0
        dpds,dpowner = dp.CombineIncomingFleets(turnlimit=turnlimit)
        debug("Recapture opportunity: >>", dp.ID(), 'dpds:', dpds, 'owner:', dpowner, '@', turnlimit)
        if dpowner == 1 or dpowner == 0 or len(defleets) == 0:
            continue
        rescuePlanets = createRescuePlan(dp, fleets, defleets, 1, turnlimit, splanets, eplanets)
        executeRescuePlan(pw, dp, rescuePlanets, splanets)

def createRescuePlan(dp, fleets, defleets, turndelta, turnlimit, splanets, eplanets):
    # STEP 1: map enemy fleets to turns in which they will come to the dp
    # map fleets to destination maps, filtering out only those coming to ours
    defleets_turns = getFleetTurns(defleets)
    
    rescuePlanets = []
    safeLimits = dict()
    #debug('         splanets:', map(lambda p: p.ID(), splanets))
    splanetsnodp = filter(lambda p: p.ID() != dp.ID(), splanets)
    eplanetsnodp = filter(lambda p: p.ID() != dp.ID(), eplanets)
    for sp in splanetsnodp:
        safeLimits[sp.ID()] = sp.SafeDispatchLimit()
    
    # STEP 2: get amount of needed ships in each turn and concoct a rescue plan
    fanthom_fleets = []
    for turn in defleets_turns:
        if turn > turnlimit:
            break
        dpds,dpowner = dp.CombineIncomingFleets(ff=fanthom_fleets, turnlimit=turn+turndelta)
        debug("  @turn:", turn, '+', turndelta, "^", dpds, 'own:', dpowner, 'turnlimit:', turnlimit+turndelta)
        if dpowner != 1:
            numships = dpds + turndelta
            dispatch, curRP = findResourcesToBuildRescueFleet(dp, turn+turndelta, numships, splanetsnodp, safeLimits, turnlimit)
            if dispatch <= 0:
                continue
            debug("     Adding:", dispatch, 'vs needed:', numships, '@', turn + turndelta)
            ff = Fleet(1, dispatch, 1, dp.ID(), turn + turndelta, turn + turndelta)
            fanthom_fleets.append(ff)
            rescuePlanets.append((turn + turndelta, dispatch, curRP))
    debug("  Rescue planets:", rescuePlanets)
    return rescuePlanets
    
def findResourcesToBuildRescueFleet(dp, turn, nships, splanetsnodp, safeLimits, turnlimit):
    nships_left = nships
    available = 0
    curRP = []
    for sp in splanetsnodp:
        distance = sp.DistanceTo(dp)
        if distance > turn: # too far from destination, can't save
            #debug(sp.ID(), "is too far from", dp.ID(), " @", distance, "vs", turn)
            continue
        growth = sp.GrowthRate() * min(turn - distance, turnlimit)
        if turn < distance:
            growth = dp.GrowthRate() * (turn - distance) # will be negative
        safeLimit = min(safeLimits[sp.ID()], sp.NumShipsDispatch())
        if safeLimit <= 0 or safeLimit < -min(growth, 0):
            continue
        dispatch = min(nships_left - min(growth, 0), safeLimit + max(growth, 0))
        nships_left -= dispatch + min(growth, 0)
        #debug('  ', sp.ID(), '>>', dp.ID(), 'dispatch:', dispatch, \
        #    'safelimitPure:', safeLimits[sp.ID()],\
        #    'safelimit:', safeLimit, 'left:', nships_left, \
        #    'need:', nships, 'growth', growth)
        curRP.append([sp, dispatch])
        available += dispatch
        if nships_left <= 0:
            break
	 
    if nships_left > 0:
        #debug("  Plan not met @", turn, " leftneeded:", nships_left, 'needed:', nships, 'on turn', turn)
        for i in range(len(curRP)):
            if dp.GrowthRate() - curRP[i][0].GrowthRate() > 1:
                #debug("  Risking the smaller planets to gain bigger:", sp.ID(), '>>', dp.ID(), " ^", sp.NumShipsDispatch())
                sp = curRP[i][0]
                oldvalue = curRP[i][1]
                curRP[i][1] = sp.NumShipsDispatch() 
                nships_left -= sp.NumShipsDispatch() - oldvalue
    
    if nships_left > 0:
        debug("  Plan aborted. @", turn, " leftneeded:", nships_left, 'needed:', nships, 'on turn', turn)
        curRP = []
        available = 0
    
    return (available, curRP)

def executeRescuePlan(pw, dp, rescuePlanets, mplanets):
    for turn, nships, curRP in rescuePlanets:
        nships_left = nships
        for sp, dispatch in curRP:
            if nships_left < 0:
                break
            fs = min(dispatch, sp.NumShipsDispatch())
            nships_left -= fs
            distance = sp.DistanceTo(dp)
            debug(distance, 'vs', turn)
            if distance == turn and fs > 0:
                debug(">>>>>>>>> EXECUTING:", sp, '>', dp, 'dispatch:', dispatch, 
                        'of', sp.NumShipsDispatch(), 'sending:', fs)
                sp.IssueOrder(dp, fs)
            elif distance < turn and fs > 0:
                proxy = findBestProxyAttack(sp, dp, mplanets)
                if proxy.ID() != dp.ID() and (sp.DistanceTo(proxy) + dp.DistanceTo(proxy)) < turn:
                    sp.IssueOrder(proxy, fs)
                    debug("Sending ships to best proxy", sp, 'via', proxy.ID(), '>', dp, 
                            " @", distance, 'eta', turn-distance, ' fleet:', fs)
                else:
                    debug("Reserving", sp, '>', dp, " @", distance, 'eta', turn-distance, ' fleets strength:', fs)
                    sp.ReserveShips(fs)
                
        if nships_left <= 0:
            dp.SetRescued(True)

def reinforceOwn(pw):
    """ find the weakest and most remote of own planets and enslave them to feed the bigger ones """
    planets = pw.Planets()
    mplanets = pw.MyPlanets()
    fleets = pw.Fleets()
    
    spearhead = min(mplanets, key=lambda p: p.ClosestEnemyDistance())
    
    frontlinePlanets = set()
    frontlinePlanets.add(spearhead)
    frontlinePlanets |= set(filter(lambda p: p.ClosestEnemyDistance() > 0 and 
        p.ClosestFriendDistance() > 0 and
        p.ClosestEnemyDistance() <= p.ClosestFriendDistance() and
        p.CombineIncomingFleets(turnlimit=p.ClosestFriendDistance() + 1)[1] == 1, planets))
    rearPlanets = filter(lambda p: p not in frontlinePlanets, mplanets)
    rearPlanets.sort(cmp, key=lambda p: p.ClosestFriendDistance())
    
    debug("Frontline:", frontlinePlanets, "  Rear:", rearPlanets)
    if len(frontlinePlanets) == 0 or len(rearPlanets) == 0:
        return
    
    for sp in rearPlanets:
        dp = min(frontlinePlanets, key=lambda p: p.DistanceTo(sp))
        proxy = findBestProxy(sp, dp, mplanets)
        closestEnemyToSPDist = sp.ClosestEnemyDistance()
        closestFriendlyToSPDist = sp.ClosestFriendDistance()
        dispatch = sp.SafeDispatchLimit()
        if closestFriendlyToSPDist >= closestEnemyToSPDist:
            dispatch -= sp.GrowthRate() * closestFriendlyToSPDist
        if dispatch <= 0:
            debug("     ", sp.ID(), '>>', proxy.ID(), '>>', dp.ID(), "safe dispatch limit is 0")
            continue
        debug(">>>> REINFORCEMENTS:", sp.ID(), '>>', proxy.ID(), '>>', 
            dp.ID(), ' ^', dispatch, 'of', sp.NumShipsDispatch())
        sp.IssueOrder(proxy, dispatch)

def findBestProxy(sp, dp, splanets):
    if len(splanets) == 0:
        return dp
    splanetsnodp = filter(lambda p: p.ID() != dp.ID(), splanets)
    proxies = []
    for pp in splanetsnodp:
        firstStep = sp.DistanceTo(pp)
        secondStep = dp.DistanceTo(pp)
        straight = sp.DistanceTo(dp)
        if (firstStep**2 + secondStep**2) < straight**2 * 0.9 and firstStep > secondStep:
            proxies.append(pp)
    if len(proxies) > 0:
        return min(proxies, key=lambda p: sp.DistanceTo(p) + dp.DistanceTo(p))
    return dp
    
def findBestProxyAttack(sp, dp, splanets):
    if len(splanets) == 0:
        return dp
    splanetsnospdp = filter(lambda p: sp.ID() != p.ID() and p.ID() != dp.ID(), splanets)
    proxies = []
    for pp in splanetsnospdp:
        firstStep = sp.DistanceTo(pp)
        secondStep = dp.DistanceTo(pp)
        straight = sp.DistanceTo(dp)
        #debug("proxy:", sp.ID(), '>', pp.ID(), '>', dp.ID(), firstStep, "+", secondStep, "~", straight)
        if (firstStep**2 + secondStep**2) < (straight**2 * 0.75) and firstStep > secondStep:
            proxies.append(pp)
    if len(proxies) > 0:
        #debug(proxies)
        return min(proxies, key=lambda p: sp.DistanceTo(p) + dp.DistanceTo(p))
    return dp
    
def getFleetsCaptureSoon(pw, fowner, fleets):
    capturedSoon = []
    for f in fleets:
        fdp = pw.GetPlanet(f.Destination())
        dpds, dpowner = fdp.CombineIncomingFleets(turnlimit=f.TurnsRemaining()+1)
        if dpowner == fowner and fdp.Owner() != dpowner:
            capturedSoon.append((fdp, f.TurnsRemaining()))
    
    return capturedSoon
    
def getDispatchSources(mplanets, fleets):
    sources = dict()
    for sp in mplanets:
        attacklimit = sp.SafeDispatchLimit(haveDebug=True)
        sources[sp.ID()] = (sp, attacklimit)
    return sources

def attackEnemy(pw):
    dplanets = list(pw.Planets())
    eplanets = pw.EnemyPlanets()
    mplanets = pw.MyPlanets()
    mfleets = pw.MyFleets()
    fleets = pw.Fleets()
    
    dplanets.sort(lambda f,s: -cmp(f.Rating(), s.Rating()) or -cmp(f.GrowthRate(), s.GrowthRate()))
    ## Include my soon-to-be-captured destinations into the proxy list
    
    if len(eplanets) == 0 or len(dplanets) == 0:
        return
        
    dispatchPlans = []
    sources = getDispatchSources(mplanets, fleets)

    # TODO: XXX: IMPLEMENT A ROBUST PLANET ATTACK SCHEME, TAKING ALL POSSIBLE SITUATIONS INTO ACCOUNT!!
    # For each destination find best attack sources
    for dp in dplanets:
        dprating = dp.Rating()
        #eplanetsnodp = filter(lambda ep: ep.ID() != dp.ID(), eplanets)
        #mplanetsnodp = filter(lambda mp: mp.ID() != dp.ID(), mplanets)
        #closestEnemyDistanceToDP = min(map(lambda ep: dp.DistanceTo(ep), eplanetsnodp)) if len(eplanetsnodp) > 0 else sys.maxint
        closestFriendDistanceToDP = dp.ClosestFriendDistance() if len(mplanets) > 0 else sys.maxint
        dpds, dpowner = dp.CombineIncomingFleets(turnlimit=closestFriendDistanceToDP)

        #if dpowner == 1: # already successfully attacked
        #    continue
        dpgds = dp.GetLocalGroupDefenceStrength(closestFriendDistanceToDP) + dpds
        maxsos = 0
        closestEnemyToDP, closestEnemyDistanceToDP = dp.ClosestEnemy()
        #debug(dp, map(lambda p: (p.ID(), dp.DistanceTo(p)), eplanetsnodp))
        
        if closestEnemyToDP.ID() != dp.ID():
            sposSource = map(lambda p: (p, p.GetOffensiveThreat(closestEnemyToDP)), mplanets)
            spmax, spos = max(sposSource, key=lambda p: p[1])
            spgos = closestEnemyToDP.GetLocalThreatStrength(closestEnemyDistanceToDP)
            maxsos = max(spos, spgos, 0)
            dpgds -= maxsos
        
        debug()
        debug("DP: >", dp.ID(), "now:", dp.Owner()," ^", dp.NumShips(), 
        'next:', dpowner, " ^", dpds, " +", dp.GrowthRate(),  " R %.2f" % dprating, \
        " dpgds", dpgds, 'maxsos', maxsos, \
        '@', closestFriendDistanceToDP, 'vs', closestEnemyDistanceToDP)
                   
        dispatchplan = []
        avg_dpdp = 0
        
        sourcesList = map(lambda item: [item[1][0], item[1][1]], sources.items())
        sourcesList.sort(cmp, key=lambda item: item[1])
        for sp, attacklimit in sourcesList:
            distance = sp.DistanceTo(dp)
            cdpds, cdpowner = dp.CombineIncomingFleets(turnlimit=distance)
            cdpgds = dp.GetLocalGroupDefenceStrength(distance) + cdpds
            if cdpowner == 1: # skip those, which will not improve the state
                debug("skipping dispatch from", sp.ID(), "since", dp.ID(), "is captured before that.")
                continue
            cdpgds -= maxsos
            dstrength = max(cdpgds, cdpds)
            debug(sp.ID(), ">", dp.ID(), "g:", cdpgds, 's:', cdpds, '@', distance)
            proxy = dp
            if sp.DistanceTo(dp) * 2 >= closestEnemyDistanceToDP:
                proxy = findBestProxyAttack(sp, dp, mplanets)
            dispatchplan.append((sp, attacklimit, dstrength + 1, proxy))

        dispatchplan.sort(lambda f,s: cmp(f[1], s[1]))
        
        for sp, limit, minneed, proxy in dispatchplan:
            distance = sp.DistanceTo(dp)
            closestEnemyToSP = sp.ClosestEnemyDistance()
            
            if dpowner == 2 and dp.GrowthRate() > sp.GrowthRate() and distance <= closestEnemyToSP:
                limit = max(0, limit + dpds)
            
            turnDelta = 0 if dpowner != 2 else 1
            ffleets = [Fleet(sp.Owner(), minneed, sp.ID(), dp.ID(), distance, distance)]
            dpdsAfter,dpownerAfter = dp.CombineIncomingFleets(ff=ffleets, turnlimit=distance)
            need = minneed
            # TODO: fix counter-save against enemy
            dpgdsAfter = dpdsAfter + dp.GetLocalGroupDefenceStrength(closestEnemyDistanceToDP, ff=ffleets)
            maxmdsdp = max(dpgdsAfter, dpdsAfter)
            threatDist = max(0, distance - closestEnemyDistanceToDP + turnDelta)
            # TODO: this lambda has awful performance: optimize!
            # Disabled, because it's not critical here. Re-enable, if sure it's needed. Then optimize.
            eposdpAfter = 0#min(map(lambda p: p.GetOffensiveThreat(dp, turnlimit=threatDist), eplanetsnodp) + [0]) \
            #    if len(eplanetsnodp) > 0 else 0
            epgosdpAfter = dp.GetLocalThreatStrength(threatDist, ff=ffleets)
            maxeosdp = max(eposdpAfter, epgosdpAfter) - maxsos
            safeOffence = minneed - maxmdsdp + maxeosdp 
            need = max(safeOffence, minneed) if maxmdsdp < maxeosdp else minneed
            
            #threatDist = min(closestEnemyDistanceToDP, closestFutureEnemyDistanceToDP)
            #if distance < threatDist:
            #    need = minneed

            debug("SP:", " ", sp.ID(), "<>", distance, "limit:", limit, "need:", need, 
                   'minneed:', minneed, 'dpownerAfter', dpownerAfter)
            debug("     counter-recap:", minneed, '-', maxmdsdp, '+', maxeosdp, '+', 
                turnDelta * dp.GrowthRate(), '=', safeOffence, 'epos:', 
                eposdpAfter, epgosdpAfter, maxsos, '@', threatDist)
            
            # compensate for the additional turns it will take to route the attack through the proxy
            compensation = 0
             
            if dpowner == 2 and proxy.ID() != dp.ID():
                compensation = (sp.DistanceTo(proxy) + proxy.DistanceTo(dp) - sp.DistanceTo(dp)) * dp.GrowthRate()
                if need + compensation > min(limit, sp.NumShipsDispatch()):
                    compensation = max(0, need - min(limit, sp.NumShipsDispatch()))
                    proxy = dp
                    
            dispatchPlans.append([dp, sp, limit, need+compensation, proxy, dprating])
            
    dispatchPlans.sort(lambda f,s: -cmp(f[5], s[5]) or -cmp(f[0].GrowthRate(), s[0].GrowthRate()))
    
    sourcesUsedShips = dict(map(lambda spid: (spid, 0), sources))
    sourcesWaiting = []
    attackPlans = []
    
    planAttackVectors(dispatchPlans, sourcesUsedShips, sourcesWaiting, attackPlans, eplanets, haveDebug=True)
    sendAttacks(pw, attackPlans)
    sendAttackReinforcements(pw, sourcesWaiting, sources, sourcesUsedShips, mplanets)

def planAttackVectors(dispatchPlans, sourcesUsedShips, sourcesWaiting, attackPlans, eplanets, haveDebug=False):
    #debug("ATTACK PLANNING STEP #2: SEARCHING FOR BEST ATTACK DESTINATIONS")
    # Find moment's best attack destinations
    spReserveDict = dict()
    attackDestinations = []
    #dispatchPlans.sort(cmp, key=lambda plan: plan[0].DistanceTo(plan[4]) + plan[1].DistanceTo(plan[4]))
    
    for dp, sp, attacklimit, dispatch, proxy, dprating in dispatchPlans:
        if dp.ID() in attackDestinations:
            continue
        used = sourcesUsedShips[sp.ID()]
        available = min(attacklimit - used, sp.NumShipsDispatch() - used)
        
        if sp.ID() not in spReserveDict:
            spReserveDict[sp.ID()] = [sp, 0]
            
        if available <= 0:
            continue

        needmore = float(dispatch - available)
        
        distance = sp.DistanceTo(dp)
        turnswait = sp.getTurnsWait(dp, distance*2, dispatch, available, used, eplanets)
        
        dpROI = dprating - turnswait
        spROI = -turnswait - distance
        
        if haveDebug:
            debug()
            debug("     ", sp.ID(), ">", dp.ID(), "Available:", available, "Dispatch:", \
            dispatch, "available", available, "limit:", attacklimit, \
            "rating: %.1f ROI: %.1f spROI: %.1f" % (dprating, dpROI, spROI), )
        
        foundBetter = False # currently better alternative with lower rating found
        for odp, osp, oattacklimit, odispatch, oproxy, odprating in dispatchPlans:
            if odprating < dprating or sp.ID() != osp.ID() or dp.ID() == odp.ID():
                continue
            if odp.ID() in attackDestinations:
                continue
            oused = sourcesUsedShips[osp.ID()]
            oavailable = min(oattacklimit, osp.NumShipsDispatch()) - oused
            odistance = odp.DistanceTo(osp)
            oturnswait = osp.getTurnsWait(odp, odistance*2, odispatch, oavailable, oused, eplanets)
            
            odpROI = odprating - oturnswait
            if odpROI - dpROI > 0:
                debug("     ====", sp.ID(), ">", dp.ID(), "better attack destination:", 
                    odp.ID(), odpROI, '>', dpROI, 'avail:', oavailable)
                foundBetter = True
                break
        
        if foundBetter:
            continue
        
        for odp, osp, oattacklimit, odispatch, oproxy, odprating in dispatchPlans:
            if dp.ID() != odp.ID() or sp.ID() == osp.ID():
                continue
            oused = sourcesUsedShips[osp.ID()]
            oavailable = min(oattacklimit, osp.NumShipsDispatch()) - oused
            odistance = odp.DistanceTo(osp)
            oturnswait = osp.getTurnsWait(odp, odistance*2, odispatch, oavailable, oused, eplanets)
            
            ospROI = -oturnswait - odistance
            
            if ospROI - spROI > 0 or (turnswait > 200.0  and oturnswait > 200.0 and odistance < distance):
                debug("     ++++", sp.ID(), ">", dp.ID(), "better attack source:", osp.ID(), ospROI, '>', spROI)
                foundBetter = True
                break
            
        if foundBetter:
            continue
        
        if needmore <= 0:
            if haveDebug:
                debug("   >>>>>>", sp.ID(), ">", dp.ID(), "Attacking with", 
                    dispatch, "ships", available - dispatch, "will be left")
            attackPlans.append((dp, sp, attacklimit, dispatch, proxy))
            attackDestinations.append(dp.ID())
            sourcesUsedShips[sp.ID()] = used + dispatch
            continue
        
        coopAttack = makeCooperativeAttackPlans(sp, dp, attacklimit, available, 
            proxy, dispatch, dispatchPlans, sourcesUsedShips, spReserveDict, attackPlans)
            
        if coopAttack:
            attackDestinations.append(coopAttack.ID())
            continue
        # reserve ships for a future attack
        if turnswait < 50.0: #distance * 2:
            reserve = min(dispatch, available)
            debug("      Reserving for", sp.ID(), ">", dp.ID(), ":", reserve, "of", available, 
            "needmore:", needmore, 'needtotal:', dispatch, "steps to grow:", turnswait,
            'rating: %.2f' % dprating, 'ROI: %.2f' % dpROI)
            sourcesUsedShips[sp.ID()] += reserve
            spReserveDict[sp.ID()][1] += reserve
            sourcesWaiting.append((sp, dp, needmore, dispatch))
        else:
            debug("      NOT reserving for", sp.ID(), ">", dp.ID(), 'avail:', available, 
                "needmore:", needmore, 'needtotal:', dispatch, 'steps to grow:', turnswait, 
                'distance*2:', sp.DistanceTo(dp) * 2, 
                'rating: %.2f' % dprating, 'ROI: %.2f' % dpROI)
            
    for spid, (sp, reserve) in spReserveDict.items():
        if reserve > 0:
            debug("Reserving for ", spid, ":", reserve, sp.NumShips(), sp.NumShipsDispatch())
            sp.ReserveShips(reserve)

def makeCooperativeAttackPlans(sp, dp, attacklimit, available, proxy, dispatch, 
                                dispatchPlans, sourcesUsedShips, spReserveDict, attackPlans):
    totalAvailable = available
    totalNeed = dispatch
    cooperativeAttackPlan = [(dp, sp, attacklimit, available, proxy)]
    cooperativeDispatchPrePlan = filter(lambda item: item[0].ID() == dp.ID() and item[1].ID() != sp.ID(), dispatchPlans)
    cooperativeDispatchPrePlan.sort(cmp, key=lambda plan: -plan[2])
    
    for odp, osp, oattacklimit, odispatch, oproxy, odprating in cooperativeDispatchPrePlan:
        #debug("      ", dp.ID(), ' checking:', osp.ID(), '>', odp.ID(), 'limit:', oattacklimit, \
        #    'needtotal:', odispatch)
        #if dp.ID() != odp.ID() or sp.ID() == osp.ID():
        #    continue
        oused = sourcesUsedShips[osp.ID()]
        oavailable = min(oattacklimit, osp.NumShipsDispatch()) - oused
        #oneedmore = float(odispatch - oavailable)
        if  (oavailable + dispatch - odispatch) > 0 and oavailable > 0:
            coopDispatch = min(oavailable, max(totalNeed - totalAvailable, 0))
            if coopDispatch <= 0:
                continue
            totalAvailable += coopDispatch
            totalNeed = max(totalNeed, odispatch)
            cooperativeAttackPlan.append((odp, osp, oattacklimit, coopDispatch, oproxy))
            
        debug("      ", osp.ID(), '>', odp.ID(), 'avail:', oavailable,
            'dispatch:', odispatch, 'totalavail:', totalAvailable, 
            'left:', totalNeed - totalAvailable)
        
        if totalNeed - totalAvailable <= 0:
            break
    
    if totalNeed - totalAvailable <= 0:
        debug("      Cooperative attack to", dp.ID(), "TOTAL:", totalAvailable, 'TOTAL NEED:', totalNeed)
        # start with the farthest
        cooperativeAttackPlan.sort(cmp, key=lambda plan: -(plan[0].DistanceTo(plan[4]) + plan[1].DistanceTo(plan[4])))
        fardp, farsp, farlimit, fardisp, farproxy = cooperativeAttackPlan[0]
        fardist = fardp.DistanceTo(farproxy) + farsp.DistanceTo(farproxy)
        
        for plan in cooperativeAttackPlan:
            _dp, _sp, _limit, _disp, _proxy = plan
            _eta = _sp.DistanceTo(_proxy) + _proxy.DistanceTo(_dp)
            # TODO: fix simultaneous cooperative assault
            if _eta < fardist:
                # reserve for future coop dispatch
                debug("      >>>>>>>> coop attack reserve:", _sp.ID(), '^', _disp, 
                        'of', _sp.NumShipsDispatch(), 'ETA:', _eta, fardist)
                sourcesUsedShips[_sp.ID()] += _disp
                if _sp.ID() not in spReserveDict:
                    spReserveDict[_sp.ID()] = [_sp, 0]
                spReserveDict[_sp.ID()][1] += _disp
                continue
            
            attackPlans.append(plan)
            debug("      >>>>>>>> coop attack:", _sp.ID(), '^', _disp, 
                    'of', _sp.NumShipsDispatch(), 'ETA:', _eta, fardist)
            sourcesUsedShips[_sp.ID()] += _disp
        return dp
    return None

def sendAttackReinforcements(pw, sourcesWaiting, sources, sourcesUsedShips, mplanets):
    #debug("ATTACK PLANNING STEP #3: SENDING ATTACK REINFORCEMENTS")
    sourcesWaiting.sort(cmp, key=lambda p: p[2] / (p[0].GrowthRate() + 1e-300))
    
    for rdp, rddp, rdpneed, dispatch in sourcesWaiting:
        totalleft = 0
        for rspid, (rsp, attacklimit) in sources.items():
            # skip those which we cannot help
            #if rspid not in sourcesWaitingID:
            #    continue
            if rsp.ID() == rdp.ID():# or rsp.DistanceTo(rdp) > rdpneed / (rdp.GrowthRate() + 1e-300):
                continue
            distance = rsp.DistanceTo(rdp)
            rdps,rdpowner = rdp.CombineIncomingFleets(turnlimit=distance)
            if rdpowner != 1 or rdps >= dispatch:
                continue
            used = sourcesUsedShips[rsp.ID()]
            leftover = min(attacklimit, rsp.NumShipsDispatch()) - used
            totalleft += leftover
            if leftover > 0:
                proxy = findBestProxyAttack(rsp, rdp, mplanets)
                tripdistance = rsp.DistanceTo(proxy)+rdp.DistanceTo(proxy)
                debug(">>>>>>>>> ATTACK REINFORCEMENTS:", \
                    rsp.ID(), ">>", proxy.ID(), ">>", rdp.ID(), ">>", rddp.ID(), \
                    '<>', rsp.DistanceTo(proxy), "+", rdp.DistanceTo(proxy), \
                    "=", tripdistance)
                debug("           ---->                 need:", rdpneed, "used:", used, 
                    "have:", rsp.NumShipsDispatch(), '>>', leftover, 'vs', rdp.NumShips(), \
                    'limit:', attacklimit, 'dispatchavailable:', rsp.NumShipsDispatch())
                dispatch = leftover - rdpneed if leftover > rdpneed else leftover
                rsp.IssueOrder(proxy, dispatch)
                sourcesUsedShips[rsp.ID()] += dispatch
                rdpneed -= dispatch
            if rdpneed <= 0:
                break
        if totalleft == 0:
            break

def sendAttacks(pw, attackPlans):
    #debug("ATTACK PLANNING STEP #4: EXECUTION")
    for dp, sp, attacklimit, dispatch, proxy in attackPlans:
        tripdistance = sp.DistanceTo(proxy)+dp.DistanceTo(proxy)
        debug(">>>>>>>> ATTACKING:", sp.ID(), ">>", proxy.ID(), ">>", dp.ID(),
            '<>', sp.DistanceTo(proxy), "+", dp.DistanceTo(proxy), "=",
            tripdistance , "have:", sp.NumShipsDispatch(), 'limit:', attacklimit,
            '>>', dispatch, 'vs', dp.NumShips())
            
        sp.IssueOrder(proxy, dispatch)
    
def dominate(pw, mplanets, eplanets, fleets):
    if len(eplanets) == 0 or len(mplanets) == 0:
        return
    
    if pw.MyProduction() <= pw.EnemyProduction():
        return
    
    spearhead = min(mplanets, key=lambda p: p.ClosestEnemyDistance())
    target = spearhead.ClosestEnemy()
    distance = spearhead.DistanceTo(target)

    myCapturedSoon = getFleetsCaptureSoon(pw, 1, fleets)
    enemyCapturedSoon = getFleetsCaptureSoon(pw, 2, fleets)
    
    myFutureProduction = sum(map(lambda item: item[0].GrowthRate(), 
        filter(lambda item: item[1] <= distance, myCapturedSoon)))
    enemyFutureProduction = sum(map(lambda item: item[0].GrowthRate(), 
        filter(lambda item: item[1] <= distance, enemyCapturedSoon)))

    if myFutureProduction < enemyFutureProduction:
        return
    
    efleets = pw.EnemyFleets()
    mfleets = pw.MyFleets()
    
    eos = estimatedCharacterOffenceStrength(pw, 2, eplanets, mplanets, efleets, mfleets)
    eds = estimatedCharacterDefenceStrength(eplanets, fleets)
    mos = estimatedCharacterOffenceStrength(pw, 1, mplanets, eplanets, mfleets, efleets)
    mds = estimatedCharacterDefenceStrength(mplanets, fleets)

    enemy_threat = -eos - mds
    my_threat = mos + eds
    
    if enemy_threat >= my_threat:
        return
    
    eplanetsnodp = filter(lambda p: p.ID() != target.ID(), eplanets)
    closestFP = spearhead.ClosestFriend()
    closestEP = spearhead.ClosestEnemy(exclude=[target])
    attacklimit = spearhead.SafeDispatchLimit()
    
    if attacklimit <= 0 or (target.GrowthRate() * distance >= attacklimit and target.GrowthRate() >= spearhead.GrowthRate()):
        return
    
    debug("DOMINATION MODE!! ALL YOUR BASE ARE BELONG TO US! ACHTUNG!!!", spearhead.ID(), ">>>", target.ID(), "*", attacklimit)
    spearhead.IssueOrder(target, attacklimit)
    
def estimatedCharacterDefenceStrength(planets, fleets):
    return sum(map(lambda i: -i[0] if i[1] != 1 else i[0],
        map(lambda p: p.CombineIncomingFleets(), planets)))

def estimatedCharacterOffenceStrength(pw, player, splanets, dplanets, sfleets, dfleets):
    if len(splanets) == 0 or len(dplanets) == 0:
        return 0
    
    planetStrength = sum(
        map(lambda sp: 
            max(map(lambda dp: sp.GetOffensiveThreat(dp), dplanets)) \
            if player == 1 \
            else min(map(lambda dp: sp.GetOffensiveThreat(dp), dplanets)), splanets))
    
    return int(planetStrength)

def main():
    map_data = ''
    pw = PlanetWars()
    while(True):
        current_line = raw_input()
        if len(current_line) >= 2 and current_line.startswith("go"):
            begintime = time.clock()
            pw.Update(map_data)
            try:
                DoTurn(pw)
            except:
                raise
                #pass
            pw.FinishTurn()
            map_data = ''
            global gameturn
            debugTime(begintime, gameturn)
        else:
            map_data += current_line + '\n'

if __name__ == '__main__':
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass
        
    try:
        if '-p' in sys.argv[1:]:
            import cProfile
            sys.stderr.write('============================= PROFILING... =============================\n')
            sys.stderr.flush()
            cProfile.run('main()', 'profile.log')
        else:
            main()
    except KeyboardInterrupt:
        sys.stderr.write('ctrl-c, leaving ...')
        sys.stderr.flush()
