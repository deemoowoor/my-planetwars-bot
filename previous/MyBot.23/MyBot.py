#!/usr/bin/env python
#

from PlanetWars import PlanetWars, Fleet, mapFleetsToTurns
from debug import debug, debugTime, gameturn
import sys
import time

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
        ep = mp.ClosestEnemy()
        debug(mp, " +", mp.GrowthRate(), " ^", mp.NumShips(), 'Closest e:', ep.ID(), '@', ep.DistanceTo(mp), ' ^', ep.NumShips())

    debug("My fleets:", len(mfleets), 'Total size:', mfleets_size)
    mfleets.sort(lambda f,s: cmp(f.Source(), s.Source()))
    for mf in mfleets:
        dest_ships = pw.GetPlanet(mf.Destination()).NumShips()
        debug(">> ", mf.Source(), '>>', mf.Destination(), " ^", mf.NumShips(), 'vs', dest_ships, " <>", mf.TurnsRemaining())
    
    efleets = pw.EnemyFleets()
    efleets_size = sum([ef.NumShips() for ef in efleets])
    
    eplanets_size = sum([ep.NumShips() for ep in eplanets])
    debug("Enemy planets:", len(eplanets), ' Planets size:', eplanets_size, 'Total size:', eplanets_size + efleets_size)
    for ep in eplanets:
        mp = ep.ClosestFriendly()
        debug(ep, " +", ep.GrowthRate(), " ^", ep.NumShips(), 'Closest mp:', mp.ID(), '@', mp.DistanceTo(ep), ' ^', mp.NumShips())
    
    debug("Enemy fleets:", len(efleets), 'Total size:', efleets_size)
    efleets.sort(lambda f,s: cmp(f.Source(), s.Source()))
    for ef in efleets:
        dest_ships = pw.GetPlanet(ef.Destination()).NumShips()
        debug("<< ", ef.Source(), '>>', ef.Destination(),  ' ^', ef.NumShips(), 'vs', dest_ships, " <>", ef.TurnsRemaining())
    
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
    debug("RECAPTURE-----------------------------------------");
    recapturePlanets(pw)
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
    
    #debug("########## RESERVING FLEETS FOR DEFENCE")
    
    for dp in dplanets:
        incomingFleets = dp.IncomingFleets()
        
        if len(incomingFleets) == 0:
            continue
        
        #for inf in incomingFleets:
        #    debug('         Fleet to: ', inf.Destination(), '<>', inf.TurnsRemaining(), '^', inf.NumShips(), 'own:', inf.Owner())
        closestEnemyDistance = dp.ClosestEnemy().DistanceTo(dp) if len(eplanets) > 0 else sys.maxint
        spds,spowner = dp.CombineIncomingFleets(turnlimit=0)
        
        #debug("     ", dp.ID(), "There are incoming fleets:", len(incomingFleets))
        for turn in getFleetTurns(incomingFleets):
            _spds, _spowner = dp.CombineIncomingFleets(turnlimit=min(turn, closestEnemyDistance))
            #debug("     planet:", dp.ID(), "fleets @", min(turn, closestEnemyDistance), 'spds:', _spds, 'owner:', _spowner)
            if _spowner != dp.Owner():
                spds = 0
            elif spds > _spds:
                spds = _spds
        
        reserve = max(dp.NumShips() - spds, 0)
        if reserve <= 0:
            continue
            
        debug(">>> RESERVING FOR DEFENCE in", dp.ID(), ":", reserve, 'now:', dp.NumShips(), 'then:', spds)
        dp.ReserveShips(reserve)

def defendOwnPlanets(pw):
    """ Manage defence of own planets:  """
    fleets = pw.Fleets()
    mfleets = pw.MyFleets()
    splanets = pw.MyPlanets()
    dplanets = []
    dplanets += pw.MyPlanets()
    eplanets = pw.EnemyPlanets()
    
    mfleetsOffensive = filter(lambda mf: pw.GetPlanet(mf.Destination()).Owner() != 1, mfleets)
    dplanets += [pw.GetPlanet(mf.Destination()) for mf in mfleetsOffensive]
    
    splanets.sort(lambda f,s: -cmp(f.NumShips(), s.NumShips()));
    dplanetid = map(lambda p: p.ID(), dplanets)
    
    efleets = filter(lambda ef: ef.Destination() in dplanetid, pw.EnemyFleets())
    
    planetRatingL = lambda f: planetRatingDefence(f, eplanets, splanets)
    dplanets.sort(lambda f,s: -cmp(planetRatingL(f), planetRatingL(s)))
    
    #for dp in dplanets:
    #    debug("P-RATING:", dp.ID(), "R: %.2f" % planetRatingL(dp), " +:", dp.GrowthRate(), "^", dp.NumShips())
    
    if len(efleets) == 0:
        return
    
    # map fleets to planets:
    dpfleets = mapFleetsToDestinations(efleets)
    
    for dpid, defleets in dpfleets:
        sent = 0
        dp = pw.GetPlanet(dpid)
        farfleetdist = max(map(lambda f: f.TurnsRemaining(), defleets))
        dpds,dpowner = dp.CombineIncomingFleets(turnlimit=farfleetdist)
        debug("RESCUE FOR: ||", dp.ID(), 'dpds:', dpds, 'owner:', dpowner)
        
        if dpowner == 1 or len(defleets) == 0:
            debug("NONE. dpowner:", dpowner, "defleets:", defleets)
            continue

        turnlimit = dp.ClosestEnemy().DistanceTo(dp) if len(eplanets) > 0 else 0
        rescuePlan = createRescuePlan(dp, fleets, defleets, 0, turnlimit)
        rescuePlanets = findResourcesForRescue(dp, splanets, eplanets, fleets, rescuePlan)
        executeRescuePlan(pw, dp, rescuePlanets, splanets)

def recapturePlanets(pw):
    """ Opportunistic weak enemy recapture """
    fleets = pw.Fleets()
    mfleets = pw.MyFleets()
    splanets = pw.MyPlanets()
    dplanets = pw.NeutralPlanets() + filter(lambda p: not p.IsRescued(), pw.MyPlanets())
    eplanets = pw.EnemyPlanets()
    
    dplanetid = [dp.ID() for dp in dplanets]
    efleets = filter(lambda ef: ef.Destination() in dplanetid, pw.EnemyFleets())
    
    splanets.sort(lambda f,s: -cmp(f.NumShips(), s.NumShips()));
    
    planetRatingL = lambda f: planetRatingDefence(f, eplanets, splanets)
    dplanets.sort(lambda f,s: -cmp(planetRatingL(f), planetRatingL(s)))
    
    #for dp in dplanets:
    #    debug("P-RATING:", dp.ID(), "R: %.2f" % planetRatingL(dp), " +:", dp.GrowthRate(), "^", dp.NumShips())
    
    if len(efleets) == 0:
        return
    
    # map fleets to planets:
    dpfleets = mapFleetsToDestinations(efleets)
    
    for dpid, defleets in dpfleets:
        dp = pw.GetPlanet(dpid)
        
        #farfleetdist = max(map(lambda f: f.TurnsRemaining(), defleets))
        turnlimit = dp.ClosestEnemy().DistanceTo(dp) if len(eplanets) > 0 else 0
        dpds,dpowner = dp.CombineIncomingFleets(turnlimit=turnlimit)
        
        debug("Recapture opportunity: >>", dp.ID(), 'dpds:', dpds, 'owner:', dpowner)
        
        if dpowner == 1 or dpowner == 0 or len(defleets) == 0:
            continue
        
        rescuePlan = createRescuePlan(dp, fleets, defleets, 1, turnlimit)
        rescuePlanets = findResourcesForRescue(dp, splanets, eplanets, fleets, rescuePlan)
        executeRescuePlan(pw, dp, rescuePlanets, splanets)

def createRescuePlan(dp, fleets, defleets, turndelta, turnlimit):
    # STEP 1: map enemy fleets to turns in which they will come to the dp
    # map fleets to destination maps, filtering out only those coming to ours
    defleets_turns = getFleetTurns(defleets)
    
    # STEP 2: get amount of needed ships in each turn and concoct a rescue plan
    fanthom_fleets = []
    for turn in defleets_turns:
        if turn > turnlimit:
            break
            
        dpds_turn,dpowner_turn = dp.CombineIncomingFleets(ff=fanthom_fleets, turnlimit=min(turnlimit, turn), haveDebug=True)
        
        debug("  @turn:", turn, "^", dpds_turn, 'own:', dpowner_turn)
        
        if dpowner_turn != 1:
            numships = dpds_turn + turndelta * (dp.GrowthRate() + 1)
            ff = Fleet(1, numships, 1, dp.ID(), turn + turndelta, turn + turndelta)
            debug("     Adding:", numships, '@', turn + turndelta)
            fanthom_fleets.append(ff)
    
    rescuePlan = [(ff.TurnsRemaining(), ff.NumShips()) for ff in fanthom_fleets]
    debug("  Rescue plan:", rescuePlan)
    return rescuePlan

def findResourcesForRescue(dp, splanets, eplanets, fleets, rescuePlan):
    # STEP 3: find resources for the rescue plan
    rescuePlanets = []
    safeLimits = dict()
    
    turnlimit = dp.ClosestEnemy().DistanceTo(dp)  if len(eplanets) > 0 else sys.maxint
    
    splanetsnodp = filter(lambda p: p.ID() != dp.ID(), splanets)
    eplanetsnodp = filter(lambda p: p.ID() != dp.ID(), eplanets)
    for sp in splanetsnodp:
        closestFP = sp.ClosestFriendly(exclude=[dp])
        closestEP = sp.ClosestEnemy(exclude=[dp])
        safeLimits[sp.ID()] = safeDispatchLimit(sp, closestFP, closestEP, splanetsnodp, eplanetsnodp, fleets, haveDebug=True)
        #if sp.DistanceTo(dp) < turnlimit:
        #    safeLimits[sp.ID()] = max(safeLimits[sp.ID()], sp.NumShipsDispatch())
        
    for turn, nships in rescuePlan:
        nships_left = nships
        curRP = []
        for sp in splanetsnodp:
            distance = sp.DistanceTo(dp)
            
            if turn < distance: # too close to destination, can't save
                debug(sp.ID(), "too close @", distance, "vs", turn)
                continue
                
            growth = sp.GrowthRate() * min(turn - distance, turnlimit)
            if turn < distance:
                growth = dp.GrowthRate() * (turn - distance) # will be negative
            
            safeLimit = min(safeLimits[sp.ID()], sp.NumShipsDispatch())
            
            if safeLimit <= 0 or safeLimit < -min(growth, 0):# or (distance - turn) > (distance / 3.0):
                continue
            
            dispatch = min(nships_left - min(growth, 0), safeLimit + max(growth, 0))
            
            debug('   >>>>', sp.ID(), '>>', dp.ID(), nships_left, '-=', dispatch, '-', abs(growth))
            nships_left -= dispatch + min(growth, 0)
            
            debug('  ', sp.ID(), '>>', dp.ID(), 'dispatch:', dispatch, \
            'safelimitPure:', safeLimits[sp.ID()], 'safelimit:', safeLimit, 'left:', nships_left, \
                'need:', nships, 'growth', growth)
            curRP.append([sp, dispatch])
            if nships_left <= 0:
                break
                
        if nships_left > 0:
            debug("  Initial plan not met @", turn, " leftneeded:", nships_left, 'needed:', nships, 'on turn', turn)
            for i in range(len(curRP)):
                if dp.GrowthRate() - curRP[i][0].GrowthRate() > 1:
                    debug("  Risking the smaller planets to gain bigger:", sp.ID(), '>>', dp.ID(), " ^", sp.NumShipsDispatch())
                    sp = curRP[i][0]
                    oldvalue = curRP[i][1]
                    curRP[i][1] = sp.NumShipsDispatch() 
                    nships_left -= sp.NumShipsDispatch() - oldvalue
        
        if nships_left > 0:
            debug("  ABORTING PLAN FOR", dp.ID(), " @", turn, " leftneeded:", nships_left, 'needed:', nships, 'on turn', turn)
            rescuePlanets = []
            break
        
        rescuePlanets.append((turn, nships, curRP))
        #    debug([(turn, [(sp, sl, sp.DistanceTo(dp)) for sp, sl in data]) for turn, data in rescuePlanets])
        #    rescuePlanets = []
        #    break
        
    return rescuePlanets

def executeRescuePlan(pw, dp, rescuePlanets, mplanets):
    for turn, nships, curRP in rescuePlanets:
        nships_left = nships
        for sp, dispatch in curRP:
            if nships_left < 0:
                break
                
            fs = min(dispatch, sp.NumShipsDispatch())
            nships_left -= fs
            distance = sp.DistanceTo(dp)
            if distance == turn and fs > 0:
                debug(">>>>>>>>> EXECUTING:", sp, '>', dp, 'dispatch:', dispatch, 'of', sp.NumShipsDispatch(), 'sending:', fs)
                pw.IssueOrder(sp.ID(), dp.ID(), fs)
                sp.ReserveShips(fs)
            elif distance < turn and fs > 0:
                proxy = findBestProxyAttack(sp, dp, mplanets)
                if proxy.ID() != dp.ID() and (sp.DistanceTo(proxy) + dp.DistanceTo(proxy)) < turn:
                    pw.IssueOrder(sp.ID(), proxy.ID(), fs)
                    debug("Sending ships to best proxy", sp, 'via', proxy.ID(), '>', dp, " @", distance, 'eta', turn-distance, ' fleet:', fs)
                debug("Reserving", sp, '>', dp, " @", distance, 'eta', turn-distance, ' fleets strength:', fs)
                sp.ReserveShips(fs)
                
        if nships_left <= 0:
            dp.SetRescued(True)

def reinforceOwn(pw):
    """ find the weakest and most remote of own planets and enslave them to feed the bigger ones """
    mplanets = pw.MyPlanets()
    eplanets = pw.EnemyPlanets()
    fleets = pw.Fleets()
    
    myCapturedSoon = getFleetsCaptureSoon(pw, 1, fleets)
    enemyCapturedSoon = getFleetsCaptureSoon(pw, 2, fleets)
    
    if (len(eplanets) == 0 and len(enemyCapturedSoon) == 0) or (len(mplanets) == 0 and len(myCapturedSoon) == 0):
        debug("No enemy or friendly planets. Nothing to reinforce.")
        return

    spearhead = min(mplanets, key=lambda p: p.ClosestEnemy().DistanceTo(p))
    
    frontlinePlanets = set()
    frontlinePlanets.add(spearhead)
    frontlinePlanets |= set(filter(lambda p: p.ClosestEnemy().DistanceTo(p) < p.ClosestFriendly().DistanceTo(p), mplanets))
    
    for mcsp, mturnsleft in myCapturedSoon:
        #debug("   captured soon:", mcsp.ID(), '@', mturnsleft)
        closestEnemy = mcsp.ClosestEnemy()
        for ecsp, eturnsleft in enemyCapturedSoon:
            if ecsp.DistanceTo(mcsp) + (eturnsleft - mturnsleft) < mcsp.DistanceTo(closestEnemy):
                closestEnemy = ecsp
        
        closestFriend = mcsp.ClosestFriendly()
        for mcsp_,mtl_ in myCapturedSoon:
            if mcsp_.ID() == mcsp.ID():
                continue
            if mcsp_.DistanceTo(mcsp) + (mtl_ - mturnsleft) < mcsp.DistanceTo(closestFriend):
                closestFriend = mcsp_
                
        #debug("   captured soon:", mcsp.ID(), '@', mturnsleft, \
        #'closestFriend:', closestFriend.ID(), '<>', closestFriend.DistanceTo(mcsp), \
        #'closestEnemy', closestEnemy.ID(), '<>', closestEnemy.DistanceTo(mcsp))
        
        if closestEnemy.DistanceTo(mcsp) < closestFriend.DistanceTo(mcsp):
            #debug("    captured soon:", mcsp.ID(), '@', mturnsleft, "adding to frontline planets")
            frontlinePlanets.add(mcsp)
        
        elif closestEnemy.DistanceTo(mcsp) < spearhead.ClosestEnemy().DistanceTo(spearhead):
            #debug("    captured soon:", mcsp.ID(), '@', mturnsleft, "adding as spearhead to frontline planets")
            frontlinePlanets.add(mcsp)
            if mcsp != spearhead:
                #debug("     removing", spearhead.ID(), "from frontline:", map(lambda p: p.ID(), frontlinePlanets))
                frontlinePlanets.remove(spearhead)
                spearhead = mcsp
    
    rearPlanets = filter(lambda p: p not in frontlinePlanets, mplanets)
    rearPlanets.sort(cmp, key=lambda p: p.ClosestFriendly().DistanceTo(p))
    
    #debug("Frontline:", frontlinePlanets, "  Rear:", rearPlanets)
    
    if len(frontlinePlanets) == 0 or len(rearPlanets) == 0:
        return
    
    for sp in rearPlanets:
        dp = min(frontlinePlanets, key=lambda p: p.DistanceTo(sp))
        eplanetsnodp = filter(lambda p: p.ID() != dp.ID(), eplanets)
        mplanetsnodp = filter(lambda p: p.ID() != dp.ID(), mplanets)
        
        proxy = findBestProxy(sp, dp, mplanets)
        
        closestEnemyToSP = sp.ClosestEnemy().DistanceTo(sp)
        closestFriendlyToSP = sp.ClosestFriendly().DistanceTo(sp)
        
        dispatch = safeDispatchLimit(sp, sp.ClosestFriendly(), sp.ClosestEnemy(), mplanetsnodp, eplanetsnodp, fleets, haveDebug=True) 
        
        if closestFriendlyToSP >= closestEnemyToSP:
            dispatch -= sp.GrowthRate() * closestFriendlyToSP
        
        if dispatch <= 0:
            debug("     ", sp.ID(), '>>', proxy.ID(), '>>', dp.ID(), "safe dispatch limit is 0")
            continue
        
        debug(">>>> REINFORCEMENTS:", sp.ID(), '>>', proxy.ID(), '>>', dp.ID(), ' ^', dispatch, 'of', sp.NumShipsDispatch())
        pw.IssueOrder(sp.ID(), proxy.ID(), dispatch)
        sp.ReserveShips(dispatch)

 
def findBestProxy(sp, dp, splanets):
    if len(splanets) == 0:
        return dp
    splanetsnodp = filter(lambda p: p.ID() != dp.ID(), splanets)
    proxies = []
    for pp in splanetsnodp:
        if (sp.DistanceTo(pp)**2 + dp.DistanceTo(pp)**2) < sp.DistanceTo(dp)**2:
            #debug("Found proxy for", sp.ID(), ">>", dp.ID(), ":", pp.ID(), "|>", sp.DistanceTo(pp), "<->", pp.DistanceTo(dp), "<| <>", sp.DistanceTo(dp))
            proxies.append(pp)
            
    if len(proxies) > 0:
        #debug("Best proxy for:", sp.ID(), ">>", dp.ID(), ":", pp.ID(), "|>", sp.DistanceTo(pp), "<.>", pp.DistanceTo(dp), "<| <>", sp.DistanceTo(dp))
        return min(proxies, key=lambda p: sp.DistanceTo(p) + dp.DistanceTo(p))
    return dp
    
def findBestProxyAttack(sp, dp, splanets):
    if len(splanets) == 0:
        return dp
    splanetsnodp = filter(lambda p: p.ID() != dp.ID(), splanets)
    proxies = []
    for pp in splanetsnodp:
        if (sp.DistanceTo(pp)**2 + dp.DistanceTo(pp)**2) < sp.DistanceTo(dp)**2:
            #debug("Found proxy for", sp.ID(), ">>", dp.ID(), ":", pp.ID(), "|>", sp.DistanceTo(pp), "<->", pp.DistanceTo(dp), "<| <>", sp.DistanceTo(dp))
            proxies.append(pp)
            
    if len(proxies) > 0:
        #debug("Best proxy for:", sp.ID(), ">>", dp.ID(), ":", pp.ID(), "|>", sp.DistanceTo(pp), "<.>", pp.DistanceTo(dp), "<| <>", sp.DistanceTo(dp))
        return min(proxies, key=lambda p: dp.DistanceTo(p))
    return dp
    
def attackEnemy(pw):
    """ Attack enemy, when possible """

    mplanets = pw.MyPlanets()
    eplanets = sanitizePlanets(pw.EnemyPlanets())
    nmplanets = sanitizePlanets(pw.NotMyPlanets())
    
    mfleets = pw.MyFleets()
    efleets = pw.EnemyFleets()
    fleets = pw.Fleets()
    
    #performCarefulOffence(pw, nmplanets, eplanets, mplanets, mfleets, fleets)
    performPlannedOffence(pw, nmplanets, eplanets, mplanets, mfleets, fleets)
    #dominate(pw, mplanets, eplanets, fleets)

def safeDispatchLimit(sp, closestfp, closestep, mplanets, eplanets, fleets, haveDebug=False):
    if len(eplanets) == 0:
        return 0
    
    closestEnemyDistanceToSP = closestep.DistanceTo(sp)
    
    spds,spowner = sp.CombineIncomingFleets(turnlimit=closestEnemyDistanceToSP)
    
    spds -= closestEnemyDistanceToSP * sp.GrowthRate()
    
    if spowner != sp.Owner():
        return 0
    
    incomingFleets = sp.IncomingFleets()
    #for inf in incomingFleets:
    #    debug('         Fleet to: ', inf.Destination(), '<>', inf.TurnsRemaining(), '^', inf.NumShipsDispatch(), 'own:', inf.Owner())
    
    for turn,mfleets,efleets in mapFleetsToTurns(incomingFleets):
        _spds, _spowner = sp.CombineIncomingFleets(turnlimit=min(turn, closestEnemyDistanceToSP))
        if _spowner != sp.Owner():
            spds = 0
        elif spds > _spds:
            spds = _spds

    if spds <= 0:
        return 0

    ep, epos = min(map(lambda ep: (ep, estimatePlanetOffensiveThreat(ep, sp, fleets)), eplanets), key=lambda epi: epi[1])
    
    closestFriendlyDistanceToSP = closestfp.DistanceTo(sp) if len(mplanets) > 0 else sys.maxint
    epgos = planetGroupOffenceStrength(sp, eplanets, fleets, closestFriendlyDistanceToSP)
    maxeos = min(epos, epgos)

    distanceEnemyToSP = closestEnemyDistanceToSP - 1 if epgos > epos else ep.DistanceTo(sp)
    
    for turn in xrange(closestFriendlyDistanceToSP + 1, ep.DistanceTo(sp)):
        epgos = planetGroupOffenceStrength(sp, eplanets, fleets, turn)
        if epos > epgos:
            distanceEnemyToSP = turn
            break
    
    maxeos = min(epgos, epgos)
    
    mplanetsnosp = filter(lambda p: p.ID() != sp.ID(), mplanets)
    spgds = planetGroupDefenceStrength(sp, mplanetsnosp, fleets, distanceEnemyToSP, haveDebug=haveDebug)
    spgds += spds
    
    if haveDebug:
        debug("     SAFE DISPATCH LIMIT:", sp.ID(), "spds:", spds, "spgds:", spgds, \
        "epos:", -epos, "(%d @%d)" % (ep.ID(), ep.DistanceTo(sp)), \
        "epgos:", -epgos, "Final:", spgds, maxeos, '=', spgds + maxeos, " of sp", sp.NumShipsDispatch())
    
    # defensive analysis: compare strength of our planet 
    # to offence potential of the enemy planet
    # we're safe and sound for spds + max_eos > 0
    # we're good to attack the enemy, while spds + epos + dpds > 0
    #debug('Left before attack: ', sp.NumShips(), '? >', max_mds + max_eos, sp, sp.ID())
    limit = min(max(spgds + maxeos, 0), sp.NumShipsDispatch())
    return limit
    
def getFleetsCaptureSoon(pw, fowner, fleets):
    capturedSoon = []

    for f in fleets:
        fdp = pw.GetPlanet(f.Destination())
        dpds, dpowner = fdp.CombineIncomingFleets()
        if dpowner == fowner and fdp.Owner() != dpowner:
            capturedSoon.append((fdp, f.TurnsRemaining()))
    
    return capturedSoon
    
def debugPlanetRatings(dplanets_ratings, dplanets):
    #for dp, rating in dplanets_ratings:
    #    debug("P-RATING:", dp.ID(), "R: %.2f" % rating, "<> %.2f" % planetDistanceBlob(dp, dplanets), " +:", \
    #    dp.GrowthRate(), "^", dp.NumShipsDispatch(), "ROI %.2f" % (dp.NumShipsDispatch() / (dp.GrowthRate() + 1e-128)))
    pass

def getDispatchSources(mplanets, eplanets, fleets, myCapturedSoon, enemyCapturedSoon):
    sources = dict()
    for sp in mplanets:
        fproxies = map(lambda p: p[0], filter(lambda item: item[1] < sp.DistanceTo(item[0]), myCapturedSoon))
        attacklimit = safeDispatchLimit(sp, sp.ClosestFriendly(), sp.ClosestEnemy(), mplanets, eplanets, fleets, haveDebug=True)
        sources[sp.ID()] = (sp, attacklimit, fproxies)
    return sources

def performPlannedOffence(pw, dplanets, eplanets, mplanets, mfleets, fleets):
    dplanets_ratings = [(dp, planetRating(dp, mplanets, eplanets)) for dp in dplanets]
    dplanets_ratings.sort(lambda f,s: -cmp(f[1], s[1]) or -cmp(f[0].GrowthRate(), s[0].GrowthRate()))
    
    ## Include my soon-to-be-captured destinations into the proxy list
    myCapturedSoon = getFleetsCaptureSoon(pw, 1, fleets)
    enemyCapturedSoon = getFleetsCaptureSoon(pw, 2, fleets)
    
    if len(eplanets) == 0 or len(dplanets) == 0:
        return
    
    #dpminneed = dict()
    dispatchPlans = []
    
    sources = getDispatchSources(mplanets, eplanets, fleets, myCapturedSoon, enemyCapturedSoon)
    
    # For each destination find best attack sources
    for dp,dprating in dplanets_ratings:
        eplanetsnodp = filter(lambda ep: ep.ID() != dp.ID(), eplanets)
        mplanetsnodp = filter(lambda mp: mp.ID() != dp.ID(), mplanets)
        
        closestEnemyDistanceToDP = min(map(lambda ep: dp.DistanceTo(ep), eplanetsnodp)) if len(eplanetsnodp) > 0 else sys.maxint
        closestFriendDistanceToDP = dp.ClosestFriendly().DistanceTo(dp) if len(mplanets) > 0 else sys.maxint
        
        dpds, dpowner = dp.CombineIncomingFleets(turnlimit=closestFriendDistanceToDP)
        
        if dpowner == 1: # already successfully attacked
            continue 
        
        closestEnemyToDP = min(eplanetsnodp, key=lambda p: dp.DistanceTo(p)) if len(eplanetsnodp) > 0 else None
        maxsos = 0
        
        dpgds = planetGroupDefenceStrength(dp, eplanetsnodp, fleets, closestFriendDistanceToDP) - dpds
        
        if dpowner != 2:
            calcOffencePotentialVsDP = lambda sp: max(estimatePlanetOffensiveThreat(sp, closestEnemyToDP, fleets), 0)
            spos = max(map(calcOffencePotentialVsDP, mplanets))
            spgos = planetGroupOffenceStrength(dp, mplanets, fleets, closestEnemyDistanceToDP)
            maxsos = max(spos, spgos)
            dpgds += maxsos
        
        debug( "DP: >", dp.ID(), "owner now:", dp.Owner(), 'next:', dpowner, \
        " +", dp.GrowthRate(), " ^", dp.NumShipsDispatch(), " R %.2f" % dprating, \
        " dpgds", -dpgds, "dpds", dpds, 'maxsos', maxsos, \
        '@', closestFriendDistanceToDP, 'vs', closestEnemyDistanceToDP)
        
        dispatchplan = []
        avg_dpdp = 0
        
        for spid, (sp, attacklimit, fproxies) in sources.items():
            distance = sp.DistanceTo(dp)
            cdpds, cdpowner = dp.CombineIncomingFleets(turnlimit=distance)
            cdpgds = planetGroupDefenceStrength(dp, eplanetsnodp, fleets, distance) - cdpds
            
            if cdpowner != 2:
                cdpgds += maxsos
            
            dstrength = max(-cdpgds, cdpds)
            
            proxy = dp
            if sp.DistanceTo(dp) * 2 >= closestEnemyDistanceToDP:
                proxy = findBestProxyAttack(sp, dp, mplanets + fproxies)
            dispatchplan.append((sp, attacklimit, dstrength, proxy))
            
        dispatchplan.sort(lambda f,s: cmp(f[1], s[1]))
        ratingDiff = map(lambda item: (item[0], item[1], dpowner), filter(lambda item: (item[1] - dprating) >= 0, dplanets_ratings))
        minNeed = None

        enemiesCloserToDP = filter(lambda ep: ep.DistanceTo(dp) <= closestFriendDistanceToDP, eplanetsnodp)
        
        # TODO: See, if the enemy is going to capture a planet close to DP sooner, than DP can be 
        # captured and take it also into account
        for sp, limit, dpdp, proxy in dispatchplan:
            distance = sp.DistanceTo(dp)
            
            closestEnemyToSP = sp.ClosestEnemy()
            #closestEnemyCapturedSoonToDP = min(enemyCapturedSoon, key=lambda item: item[0].DistanceTo(dp) + item[1]) \
            #    if len(enemyCapturedSoon) > 0 else None
            
            closestFutureEnemyDistanceToDP = min(map(lambda p: p[1] + p[0].DistanceTo(dp), enemyCapturedSoon)) \
                if len(enemyCapturedSoon) > 0 else sys.maxint
            
            ffleets = [Fleet(sp.Owner(), limit, sp.ID(), dp.ID(), distance, distance)]
            dpds_after,dpowner_after = dp.CombineIncomingFleets(ff=ffleets, \
                turnlimit=min(distance, closestEnemyDistanceToDP, closestFutureEnemyDistanceToDP))
            
            need = dpdp + 1
            
            if dpowner != 2:
                dpgds_after = dpds_after + planetGroupDefenceStrength(dp, mplanetsnodp, fleets, closestEnemyDistanceToDP, ff=ffleets)
                maxmdsdp = max(dpgds_after, dpds_after)
                
                eopVsDP_After = lambda p: estimatePlanetOffensiveThreat(p, dp, fleets) # - \
#                    (p.DistanceTo(dp) - sp.DistanceTo(dp)) * p.GrowthRate()
                
                eposdp_after = 0
                
                if len(eplanetsnodp):
                    epdp = min(eplanetsnodp, key=lambda p: min(eopVsDP_After(p), 0))
                    eposdp_after = min(eopVsDP_After(epdp), 0)
                
                # TODO: add planets captured by enemy before DP into account
                #enemyCapturedBeforeDP = map(lambda p: p[0], filter(lambda ep: sp.DistanceTo(dp) <= ep[1], enemyCapturedSoon))
                epgosdp_after = sum([min(eopVsDP_After(ep), 0) for ep in enemiesCloserToDP])
                maxeosdp = min(eposdp_after, epgosdp_after)
                need = dpdp + 1 - maxmdsdp - maxeosdp if maxmdsdp <= -maxeosdp else need
                
            debug("SP:", " ", sp.ID(), "<>", distance, "limit:", limit, "need:", need, 'minneed:', dpdp+1)
            
            if distance < min([closestEnemyDistanceToDP, closestFutureEnemyDistanceToDP]):
                need = dpdp + 1
                #debug("      Allowing minimal dispatch of ", need, '<>', distance, '<>', closestEnemyDistanceToDP, closestFutureEnemyDistanceToDP)
            
            # compensate for the additional turns it will take to route the attack through the proxy
            compensation = 0
            if dpowner == 2 and proxy.ID() != dp.ID():
                compensation = (sp.DistanceTo(proxy) + proxy.DistanceTo(dp) - sp.DistanceTo(dp)) * dp.GrowthRate()
                if need + compensation > min(limit, sp.NumShipsDispatch()):
                    compensation = max(0, need - min(limit, sp.NumShipsDispatch()))
                    proxy = dp
                    
            # if the previous chosen is already smaller, bypass the current one
            #if minNeed and minNeed[3] <= need + compensation:
            #    continue
            
            minNeed = [dp, sp, limit, need+compensation, proxy, dprating]
            
            #debug("APPENDING:", sp.ID(), '>', proxy.ID(), '>', dp.ID(), '>>>', need+compensation, '$', dprating)
            dispatchPlans.append(minNeed)

    dispatchPlans.sort(lambda f,s: -cmp(f[5], s[5]) or -cmp(f[0].GrowthRate(), s[0].GrowthRate()))
    
    sourcesUsedShips = dict(map(lambda spid: (spid, 0), sources))
    sourcesWaiting = []
    attackPlans = []
    
    planAttackVectors(dispatchPlans, sourcesUsedShips, sourcesWaiting, attackPlans, eplanets)
    sendAttacks(pw, attackPlans)
    sendAttackReinforcements(pw, sourcesWaiting, sources, sourcesUsedShips, mplanets)
    
def planAttackVectors(dispatchPlans, sourcesUsedShips, sourcesWaiting, attackPlans, eplanets):
    #debug("ATTACK PLANNING STEP #2: SEARCHING FOR BEST ATTACK DESTINATIONS")
    # Find moment's best attack destinations
    #dpReserveDict = dict()
    spReserveDict = dict()
    
    ## TODO: Check if there are better sources BEFORE SENDING AN ATTACK! 
    # Otherwise duplicate attacks are performed in a series.
    for dp, sp, attacklimit, dispatch, proxy, dprating in dispatchPlans:
        used = sourcesUsedShips[sp.ID()]
        available = min(attacklimit - used, sp.NumShipsDispatch() - used)
        debug("     ", sp.ID(), ">", dp.ID(), "Available:", available, "Dispatch:", \
        dispatch, "limit:", attacklimit, "rating: %.1f" % dprating)

        #if dp.ID() not in dpReserveDict:
        #    dpReserveDict[dp.ID()] = 0
            
        if sp.ID() not in spReserveDict:
            spReserveDict[sp.ID()] = [sp, 0]
            
        if available <= 0:
            continue
            
        needmore = float(dispatch - available)
        
        if needmore <= 0:
            debug("   >>>>>>", sp.ID(), ">", dp.ID(), "Attacking for best rating asap: ", dprating)
            attackPlans.append((dp, sp, attacklimit, dispatch, proxy))
            sourcesUsedShips[sp.ID()] = used + dispatch
            continue
            
        enemiesCloserToDP = filter(lambda ep: ep.DistanceTo(dp) <= sp.DistanceTo(dp), eplanets)
        enemyGrowthTotal = sum(map(lambda p: p.GrowthRate(), enemiesCloserToDP))
        
        if sp.GrowthRate() > enemyGrowthTotal:
            needmore += sp.GrowthRate() * needmore / (sp.GrowthRate() - enemyGrowthTotal)
        else:
            needmore = 1e300
        #needmore -= dpReserveDict[dp.ID()]
        
        dpROI = (dprating - needmore / sp.GrowthRate())
        
        foundBetter = False # currently better alternative with lower rating found
        
        for odp, osp, oattacklimit, odispatch, oproxy, odprating in dispatchPlans:
            if odprating < dprating or sp.ID() != osp.ID() or dp.ID() == odp.ID():
                continue
                
            oused = sourcesUsedShips[osp.ID()]
            oneedmore = float(odispatch - min(oattacklimit, osp.NumShipsDispatch()) - oused)
            
            enemiesCloserToODP = filter(lambda ep: ep.DistanceTo(odp) <= osp.DistanceTo(odp), eplanets)
            oenemyGrowthTotal = sum(map(lambda p: p.GrowthRate(), enemiesCloserToODP))
            if osp.GrowthRate() > oenemyGrowthTotal:
                oneedmore += osp.GrowthRate() * oneedmore / (osp.GrowthRate() - oenemyGrowthTotal)
            else:
                oneedmore = 1e300
            
            odpROI = (odprating - oneedmore / osp.GrowthRate())
            if odpROI - dpROI > 0:
                debug("     ====", sp.ID(), ">", dp.ID(), "better attack destination:", odp.ID(), odpROI, '>', dpROI, 'avail:', available)
                foundBetter = True
                break
        
        if foundBetter:
            continue
        
        for odp, osp, oattacklimit, odispatch, oproxy, odprating in dispatchPlans:
            if odispatch > dispatch or dp.ID() != odp.ID() or sp.ID() == osp.ID():
                continue
            
            oused = sourcesUsedShips[osp.ID()]
            oneedmore = float(odispatch - min(oattacklimit, osp.NumShipsDispatch()) - oused)
            enemiesCloserToODP = filter(lambda ep: ep.DistanceTo(odp) <= osp.DistanceTo(odp), eplanets)
            oenemyGrowthTotal = sum(map(lambda p: p.GrowthRate(), enemiesCloserToODP))
            if osp.GrowthRate() > oenemyGrowthTotal:
                oneedmore += osp.GrowthRate() * oneedmore / (osp.GrowthRate() - oenemyGrowthTotal)
            else:
                oneedmore = 1e300
            
            if odp.DistanceTo(osp) < dp.DistanceTo(sp):
                debug("     ++++", sp.ID(), ">", dp.ID(), "better attack source:", osp.ID(), odispatch, '<', dispatch, 'avail:', available)
                foundBetter = True
                #reserve = min(available, oneedmore)
                #sourcesUsedShips[sp.ID()] += reserve
                break
        
        if foundBetter:
            continue
        
        # reserve ships for a future attack
        if needmore / sp.GrowthRate() < 50.0:
            reserve = min(dispatch, available)
            debug("      Reserving for", sp.ID(), ">", dp.ID(), ":", reserve, "of", available, \
            "needmore:", needmore, 'needtotal:', dispatch, "steps to grow:", needmore / sp.GrowthRate(), \
            'rating: %.2f' % dprating, 'ROI: %.2f' % dpROI)
            sourcesUsedShips[sp.ID()] += reserve
            #dpReserveDict[dp.ID()] += reserve
            spReserveDict[sp.ID()][1] += reserve
            sourcesWaiting.append((sp, dp, needmore))
            
    for spid, (sp, reserve) in spReserveDict.items():
        sp.ReserveShips(reserve)

def sendAttackReinforcements(pw, sourcesWaiting, sources, sourcesUsedShips, mplanets):
    #debug("ATTACK PLANNING STEP #3: SENDING ATTACK REINFORCEMENTS")
    sourcesWaiting.sort(cmp, key=lambda p: p[2] / p[0].GrowthRate())
    #sourcesWaitingID = map(lambda p: p[0].ID(), sourcesWaiting)
    for rdp, rddp, rdpneed in sourcesWaiting:
        totalleft = 0
        
        for rspid, (rsp, attacklimit, fproxies) in sources.items():
            # skip those which we cannot help
            #if rspid not in sourcesWaitingID:
            #    continue
            
            if rsp.ID() == rdp.ID() or rsp.DistanceTo(rdp) > rdpneed / rdp.GrowthRate():
                continue
            
            used = sourcesUsedShips[rsp.ID()]
            leftover = min(attacklimit, rsp.NumShipsDispatch()) - used
            totalleft += leftover
            
            if leftover > 0:
                proxy = findBestProxyAttack(rsp, rdp, mplanets + fproxies)
                tripdistance = rsp.DistanceTo(proxy)+rdp.DistanceTo(proxy)
                debug(">>>>>>>>> ATTACK REINFORCEMENTS:", \
                    rsp.ID(), ">>", proxy.ID(), ">>", rdp.ID(), ">>", rddp.ID(), '<>', rsp.DistanceTo(proxy), \
                    "+", rdp.DistanceTo(proxy), "=", tripdistance)
                debug("           ---->                 need:", rdpneed, "used:", used, 
                    "have:", rsp.NumShipsDispatch(), '>>', leftover, 'vs', rdp.NumShips(), \
                    'limit:', attacklimit, 'dispatchavailable:', rsp.NumShipsDispatch())
                dispatch = leftover - rdpneed if leftover > rdpneed else leftover
                pw.IssueOrder(rsp.ID(), proxy.ID(), dispatch)
                rsp.ReserveShips(dispatch)
                rdpneed -= dispatch
                
            if rdpneed <= 0:
                break
        
        if totalleft == 0:
            break

def sendAttacks(pw, attackPlans):
    #debug("ATTACK PLANNING STEP #4: EXECUTION")
    for dp, sp, attacklimit, dispatch, proxy in attackPlans:
        tripdistance = sp.DistanceTo(proxy)+dp.DistanceTo(proxy)
        debug(">>>>>>>> ATTACKING:", sp.ID(), ">>", proxy.ID(), ">>", dp.ID(), \
            '<>', sp.DistanceTo(proxy), "+", dp.DistanceTo(proxy), "=", \
            tripdistance , "have:", sp.NumShipsDispatch(), 'limit:', attacklimit, \
            '>>', dispatch, 'vs', dp.NumShips())
            
        pw.IssueOrder(sp.ID(), proxy.ID(), dispatch)
        sp.ReserveShips(dispatch)
    
def dominate(pw, mplanets, eplanets, fleets):
    if len(eplanets) == 0 or len(mplanets) == 0:
        return
    
    if pw.MyProduction() <= pw.EnemyProduction():
        return
    
    spearhead = min(mplanets, key=lambda p: p.ClosestEnemy().DistanceTo(p))
    target = spearhead.ClosestEnemy()
    distance = spearhead.DistanceTo(target)

    myCapturedSoon = getFleetsCaptureSoon(pw, 1, fleets)
    enemyCapturedSoon = getFleetsCaptureSoon(pw, 2, fleets)
    
    myFutureProduction = sum(map(lambda item: item[0].GrowthRate(), filter(lambda item: item[1] <= distance, myCapturedSoon)))
    enemyFutureProduction = sum(map(lambda item: item[0].GrowthRate(), filter(lambda item: item[1] <= distance, enemyCapturedSoon)))

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
    closestFP = spearhead.ClosestFriendly()
    closestEP = spearhead.ClosestEnemy(exclude=[target])
    attacklimit = safeDispatchLimit(spearhead, closestFP, closestEP, mplanets, eplanetsnodp, fleets)
    
    if attacklimit <= 0 or (target.GrowthRate() * distance >= attacklimit and target.GrowthRate() >= spearhead.GrowthRate()):
        return
    
    debug("DOMINATION MODE!! ALL YOUR BASE ARE BELONG TO US! ACHTUNG!!!", spearhead.ID(), ">>>", target.ID(), "*", attacklimit)
    pw.IssueOrder(spearhead.ID(), target.ID(), attacklimit)
    spearhead.ReserveShips(attacklimit)
    
def getDispatchFeasibility(sp, dp, closestEPToSP, closestEnemyDistanceToSP, closestEPToDP, closestEnemyDistanceToDP):
    feasibility = 0

    feasibility = sp.GrowthRate() * closestEnemyDistanceToSP - closestEPToDP.GrowthRate() * sp.DistanceTo(dp)
    if dp.Owner() == 1:
        feasibility -= closestEPToDP.GrowthRate() * closestEnemyDistanceToDP
    elif dp.Owner() > 1:
        feasibility += dp.GrowthRate() * closestEnemyDistanceToDP
    
    return feasibility

def planetDistanceBlob(planet, planets):
    if len(planets) <= 0:
        return sys.maxint
    return float(sum(map(lambda p: planet.DistanceTo(p), planets))) / float(len(planets))

def planetDistanceAndGrowthBlob(planet, planets):
    planetsnodp = filter(lambda p: p.ID() != planet.ID(), planets)
    if len(planetsnodp) <= 0:
        return sys.maxint
    
    return sum(map(lambda p: float(p.GrowthRate()) / planet.DistanceTo(p), planetsnodp)) / float(len(planetsnodp))

def planetRating(planet, mplanets, eplanets):
    #edist = 1e-128
    #if len(eplanets) > 0:
    #    edist = float(planetDistanceBlob(planet, filter(lambda p: p.ID() != planet.ID(), eplanets))) + 1e-128
    
    mdist = 1e-128
    if len(mplanets) > 0:
        mdist = float(planetDistanceBlob(planet, filter(lambda p: p.ID() != planet.ID(), mplanets))) + 1e-128
    
    rating = 0.0
    if planet.Owner() == 2:
        rating = -mdist + planet.GrowthRate()
    else:
        rating = -(mdist + float(planet.NumShips()) / (float(planet.GrowthRate()) + 1e-128))
    
    return rating

def planetRatingDefence(planet, eplanets, mplanets):
    edist = 0.0
    if len(eplanets) > 0:
        edist = float(planetDistanceBlob(planet, eplanets))
    
    mdist = 1e-128
    if len(mplanets) > 0:
        mdist = float(planetDistanceBlob(planet, mplanets)) + 1e-128
    
    rating = (edist / mdist) * planet.GrowthRate()
    return rating

    
def estimatedCharacterDefenceStrength(planets, fleets):
    return sum(map(lambda i: -i[0] if i[1] != 1 else i[0],
        map(lambda p: p.CombineIncomingFleets(), planets)))

def estimatedCharacterOffenceStrength(pw, player, splanets, dplanets, sfleets, dfleets):
    if len(splanets) == 0 or len(dplanets) == 0:
        return 0
    
    planetStrength = sum(
        map(lambda sp: 
            max(map(lambda dp: estimatePlanetOffensiveThreat(sp, dp, dfleets), dplanets)) \
            if player == 1 \
            else min(map(lambda dp: estimatePlanetOffensiveThreat(sp, dp, dfleets), dplanets)), splanets))
    
    return int(planetStrength)

def planetGroupDefenceStrength(planet, planets, fleets, distLimit, ff=[], haveDebug=False):
    if len(planets) == 0:
        return 0
        
    pgds = 0
    localGroup = filter(lambda p: p.DistanceTo(planet) <= distLimit, planets)
    if haveDebug:
        debug("        pgds for", planet, "@", distLimit, ":", map(lambda p: p.ID(), localGroup))
    calcDefenceStrength = lambda p: p.CombineIncomingFleets(ff=ff, turnlimit=max(0, distLimit - p.DistanceTo(planet)))
    for p in localGroup:
        pds, powner = calcDefenceStrength(p)
        if haveDebug:
            debug("         + pds for", p.ID(), "@", p.DistanceTo(planet), ": ", pds, "owned:",\
            powner, "<>", p.DistanceTo(planet), 'limit:', distLimit - p.DistanceTo(planet))
        if powner == 1:
            pgds += pds
        else:
            pgds -= pds
    if haveDebug:
        debug("        final pgds:", pgds)
    return pgds
    
def planetGroupOffenceStrength(planet, planets, fleets, distLimit):
    calcOffencePotential = lambda ep: estimatePlanetOffensiveThreat(ep, planet, fleets)
    localGroup = filter(lambda p: p.DistanceTo(planet) <= distLimit, planets)
    pgos = sum([min(calcOffencePotential(p), 0) for p in localGroup])
    return pgos
    
def estimatedPlanetDefencePotential(sp, dp, dpowner, dpds, fleets):
    """ Calculate the potential of a planet to defend against any attack. Number represents exactly, 
    how many ships must be sent to the planet to capture it. """
    if dpowner == 0: # neutral planets don't grow
        return dpds
    else:
        distance = sp.DistanceTo(dp)
        growthrate = dp.GrowthRate()
        return dpds + growthrate * distance
    
def estimatePlanetOffensiveThreat(sp, dp, fleets, noGrowth=False, turnlimit=sys.maxint):
    """ Calculate the potential of a source planet (sp) to build a successful 
    'all-out' attack on another, dp. Result number represents exactly how many
    ships will be left after the attack.
    """
    if sp.Owner() == 0 or dp.Owner() == sp.Owner():
        return 0
    
    distance = sp.DistanceTo(dp)
    dgrowth = dp.GrowthRate()
    
    if dp.Owner() == 0 or noGrowth:
        growth = 0
    
    limit = min(distance, turnlimit) # set upper limit to double of the distance
    
    maxstrength, powner = sp.CombineIncomingFleets(turnlimit=0)
    maxstrengthturn = 0
    maxstrength -= dgrowth * (distance + maxstrengthturn)
    for turn in xrange(1, limit):
        pstrength, powner = sp.CombineIncomingFleets(turnlimit=turn)
        pstrength -= dgrowth * (distance + turn)
        
        if powner == sp.Owner() and maxstrength < pstrength:
            maxstrength = pstrength
            maxstrengthturn = turn
    
    #debug("      pOfThreat:", sp.ID(), ">", dp.ID(), maxstrength, '@', maxstrengthturn, '@limit:', limit)
    
    maxstrength = -maxstrength if sp.Owner() == 2 else maxstrength
    return maxstrength

def sanitizePlanets(planets):
    """ Filter out wholly undesirable planets """
    return filter(lambda p: p.GrowthRate() > 0, planets)

def main():
    map_data = ''
    while(True):
        current_line = raw_input()
        if len(current_line) >= 2 and current_line.startswith("go"):
            begintime = time.clock()
            pw = PlanetWars(map_data)
            try:
                DoTurn(pw)
            except Exception, ex:
                raise
            pw.FinishTurn()
            map_data = ''
            debugTime(begintime)
        else:
            map_data += current_line + '\n'

if __name__ == '__main__':
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass
        
    try:
        main()
    except KeyboardInterrupt:
        print 'ctrl-c, leaving ...'
        
