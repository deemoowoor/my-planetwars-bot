#!/usr/bin/env python
#

## TODO: refactor it! Extract frequently-used methods to respective classes,
## cache frequently used processed lists (such as distance-sorted planet lists)
## TODO: use the trick with distance-to-my-sorted enemy planets to find the planets
## that have to be accounted for in terms of defensive forces to be left
## on the planet
##

from PlanetWars import PlanetWars, Fleet
import sys
import time
debuglog = None
gameturn = 0
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

def debugStatus(pw):
    if '-d' not in sys.argv[1:]:
        return
        
    debug("\n\n##################################################");
    debug("Turn", gameturn)
    debug("My planets:")
    mplanets = pw.MyPlanets()
    eplanets = pw.EnemyPlanets()
    for mp in mplanets:
        closest_ep = mp
        if len(eplanets) > 0:
            closest_ep = min(eplanets, key=lambda p: p.DistanceTo(mp))
        debug(mp, " +", mp.GrowthRate(), " ^", mp.NumShips(), 'Closest ep:', closest_ep.ID(), '@', closest_ep.DistanceTo(mp), ' ^', closest_ep.NumShips())

    mfleets = pw.MyFleets()    
    debug("My fleets:", len(mfleets))
    mfleets.sort(lambda f,s: cmp(f.Source(), s.Source()))
    for mf in mfleets:
        dest_ships = pw.GetPlanet(mf.Destination()).NumShips()
        debug(">> ", mf.Source(), '>>', mf.Destination(), " ^", mf.NumShips(), 'vs', dest_ships, " <>", mf.TurnsRemaining())
    
    debug("Enemy planets:")
    for ep in eplanets:
        closest_mp = ep
        if len(mplanets) > 0:
            closest_mp = min(mplanets, key=lambda p: p.DistanceTo(mp))
        debug(ep, " +", ep.GrowthRate(), " ^", ep.NumShips(), 'Closest mp:', closest_mp.ID(), '@', closest_mp.DistanceTo(ep), ' ^', closest_mp.NumShips())
    
    efleets = pw.EnemyFleets()
    debug("Enemy fleets:", len(efleets))
    efleets.sort(lambda f,s: cmp(f.Source(), s.Source()))
    for ef in efleets:
        dest_ships = pw.GetPlanet(ef.Destination()).NumShips()
        debug("<< ", ef.Source(), '>>', ef.Destination(),  ' ^', ef.NumShips(), 'vs', dest_ships, " <>", ef.TurnsRemaining())

def debugTime(begintime):
    global maxtime, maxtimeTurn, gameturn
    endtime = time.clock()
    if maxtime < (endtime - begintime):
        maxtime = (endtime - begintime)
        maxtimeTurn = gameturn
    debug("Clock: ", (endtime - begintime), 's Max:', maxtime, 's @', maxtimeTurn)
        
def DoTurn(pw):
    global gameturn
    
    debugStatus(pw)
    
    debug("REINFORCEMENTS AND DEFENCE #######################");
    defendOwnPlanets(pw)
    debug("RECAPTURE-----------------------------------------");
    recapturePlanets(pw)
    debug("ATTACK--------------------------------------------");
    attackEnemy(pw)
    debug("REINFORCEMENTS -----------------------------------");
    reinforceOwn(pw)

    gameturn += 1

def mapFleetsToTurns(fleets):
    fleets.sort(lambda f,s: cmp(f.TurnsRemaining(), s.TurnsRemaining()))
    curturn = min([ef.TurnsRemaining() for ef in fleets])
    curturn_fleets = []
    turn_list = [(curturn, curturn_fleets)]
    
    for ef in fleets:
        turn = ef.TurnsRemaining()
        if curturn != turn:
            curturn = turn
            curturn_fleets = []
            turn_list.append((curturn, curturn_fleets))
        curturn_fleets.append(ef)
    
    turn_list.sort(lambda f,s: cmp(f[0], s[0]))
    return turn_list

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

def defendOwnPlanets(pw):
    """ Manage defence of own planets:  """
    fleets = pw.Fleets()
    mfleets = pw.MyFleets()
    splanets = pw.MyPlanets()
    dplanets = []
    dplanets += pw.MyPlanets()
    eplanets = pw.EnemyPlanets()
    
    mfleets_to_neutrals = filter(lambda mf: pw.GetPlanet(mf.Destination()).Owner() == 0, mfleets)
    dplanets += [pw.GetPlanet(mf.Destination()) for mf in mfleets_to_neutrals]
    
    splanets.sort(lambda f,s: -cmp(f.NumShips(), s.NumShips));
    dplanetid = [dp.ID() for dp in dplanets]
    
    efleets = filter(lambda ef: ef.Destination() in dplanetid, pw.EnemyFleets())
    
    planetRatingL = lambda f: planetRating(f, eplanets, splanets, fleets)
    dplanets.sort(lambda f,s: -cmp(planetRatingL(f), planetRatingL(s)))
    
    if len(efleets) == 0:
        return
    
    # map fleets to planets:
    dpfleets = mapFleetsToDestinations(efleets)
    
    for dpid, defleets in dpfleets:
        sent = 0
        
        dp = pw.GetPlanet(dpid)
        
        # STEP 0: see, if the planet needs rescue
        uncertainty_limit = dp.ClosestEnemy().DistanceTo(dp) if len(eplanets) > 0 else sys.maxint
        
        dpds,dpowner = estimatedPlanetDefenceStrength(dp, fleets, uncertainty_limit=uncertainty_limit)
        
        debug("RESCUE FOR: ||", dp.ID(), 'visibility:', uncertainty_limit, 'dpds:', dpds, 'owner:', dpowner)
        
        if dpowner == 1 or len(defleets) == 0:
            continue
        
        rescuePlan = createRescuePlan(dp, fleets, defleets, 0, uncertainty_limit)
        rescuePlanets = findResourcesForRescue(dp, splanets, eplanets, fleets, rescuePlan)
        executeRescuePlan(pw, dp, rescuePlanets, splanets)

def recapturePlanets(pw):
    """ Opportunistic weak enemy recapture """
    fleets = pw.Fleets()
    mfleets = pw.MyFleets()
    splanets = pw.MyPlanets()
    dplanets = pw.NotMyPlanets()
    eplanets = pw.EnemyPlanets()
    
    dplanetid = [dp.ID() for dp in dplanets]
    
    efleets = filter(lambda ef: ef.Destination() in dplanetid, pw.EnemyFleets())
    
    splanets.sort(lambda f,s: -cmp(f.NumShips(), s.NumShips));
    
    planetRatingL = lambda f: planetRating(f, eplanets, splanets, fleets)
    dplanets.sort(lambda f,s: -cmp(planetRatingL(f), planetRatingL(s)))
    
    if len(efleets) == 0:
        return
    
    # map fleets to planets:
    dpfleets = mapFleetsToDestinations(efleets)
    
    for dpid, defleets in dpfleets:
        dp = pw.GetPlanet(dpid)
        
        # STEP 0: see, if the planet needs rescue
        uncertainty_limit = dp.ClosestEnemy().DistanceTo(dp) 
        dpds,dpowner = estimatedPlanetDefenceStrength(dp, fleets, uncertainty_limit=uncertainty_limit)
        
        debug("Recapture opportunity: >>", dp.ID(), 'visibility:', uncertainty_limit, 'dpds:', dpds, 'owner:', dpowner)
        
        if dpowner == 1 or len(defleets) == 0:
            continue
        
        rescuePlan = createRescuePlan(dp, fleets, defleets, 1, uncertainty_limit)
        rescuePlanets = findResourcesForRescue(dp, splanets, eplanets, fleets, rescuePlan)
        executeRescuePlan(pw, dp, rescuePlanets, splanets)

def createRescuePlan(dp, fleets, defleets, turndelta, uncertainty_limit):
    # STEP 1: map enemy fleets to turns in which they will come to the dp
    # map fleets to destination maps, filtering out only those coming to ours
    defleets_turns = mapFleetsToTurns(defleets)
    
    # STEP 2: get amount of needed ships in each turn and concoct a rescue plan
    fanthom_fleets = []
    for turn, tdefleets in defleets_turns:
        dpds_turn,dpowner_turn = estimatedPlanetDefenceStrength(dp, fleets, 
            fanthom_fleets = fanthom_fleets, 
            uncertainty_limit=min(uncertainty_limit, turn))
            
        debug("  @turn:", turn, "^", dpds_turn, 'own:', dpowner_turn)

        if dpowner_turn != 1:
            ff = Fleet(dp.Owner(), dpds_turn + turndelta * dp.GrowthRate(), 1, dp.ID(), 0, turn + turndelta)
            debug("     Adding:", dpds_turn + turndelta * dp.GrowthRate(), '@', turn + turndelta)
            fanthom_fleets.append(ff)
    
    rescuePlan = [(ff.TurnsRemaining(), ff.NumShips()) for ff in fanthom_fleets]
    debug("  Rescue plan:", rescuePlan)
    return rescuePlan

def findResourcesForRescue(dp, splanets, eplanets, fleets, rescuePlan):
    # STEP 3: find resources for the rescue plan
    rescuePlanets = []
    safeLimits = dict()
    
    uncertainty_limit = 0
    if len(eplanets) > 0:
        uncertainty_limit = dp.ClosestEnemy().DistanceTo(dp) 
        
    splanetsnodp = filter(lambda sp: sp.ID() != dp.ID(), splanets)
    
    for sp in splanetsnodp:
        safeLimits[sp.ID()] = safeDispatchLimit(sp, dp, splanets, eplanets, fleets)
        
    for turn, nships in rescuePlan:
        nships_left = nships
        curRP = []
        for sp in splanetsnodp:
            if turn < sp.DistanceTo(dp): # too close to destination, can't save
                continue
            
            futureGrowth = sp.GrowthRate() * min(turn - sp.DistanceTo(dp), uncertainty_limit)
            safeLimit = safeLimits[sp.ID()] + futureGrowth
            
            if safeLimit <= 0:
                continue
            
            dispatch = min(nships_left, safeLimit)
            nships_left -= dispatch
            debug('  ', sp.ID(), '>>', dp.ID(), 'dispatch:', dispatch, 'safelimit:', safeLimit, 'left:', nships_left, \
                'need:', nships, 'slPure:', safeLimits[sp.ID()], 'futureGrowth', futureGrowth)
            curRP.append([sp, dispatch])
            if nships_left <= 0:
                break
                
        if nships_left > 0:
            debug("  CAN'T FULFILL THE PLAN @", turn, " Left:", nships_left, 'needed:', nships, 'on turn', turn)
            for i in range(len(curRP)):
                if dp.GrowthRate() - curRP[i][0].GrowthRate() > 1:
                    debug("  Risking the smaller planets to gain bigger:", sp.ID(), '>>', sp.NumShips() - 1)
                    sp = curRP[i][0]
                    curRP[i][1] = sp.NumShips() - 1
        
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
                
            fs = min(dispatch, sp.NumShips() - 1)
            nships_left -= fs
            distance = sp.DistanceTo(dp)
            if distance == turn and fs > 0:
                debug(">>>>>>>>> EXECUTING:", sp, '>', dp, 'dispatch:', dispatch, 'of', sp.NumShips(), 'sending:', fs)
                pw.IssueOrder(sp.ID(), dp.ID(), fs)
                sp.RemoveShips(fs)
            elif distance < turn and fs > 0:
                bestProxy = findBestProxy(sp, dp, mplanets)
                if bestProxy.ID() != dp.ID() and (sp.DistanceTo(bestProxy) + dp.DistanceTo(bestProxy)) <= turn:
                    pw.IssueOrder(sp.ID(), bestProxy.ID(), fs)
                    debug("Sending ships to best proxy", sp, '>', dp, " @", distance, 'eta', turn-distance, ' fleet:', fs)
                debug("Reserving", sp, '>', dp, " @", distance, 'eta', turn-distance, ' fleet:', fs)
                sp.RemoveShips(fs)
 
def regroupPlanetRating(planet, eplanets, mplanets):
    edist = 0
    if len(eplanets) > 0:
        edist = planetDistanceBlob(planet, eplanets)
    
    mdist = 0
    if len(mplanets) > 0:
        mdist = planetDistanceBlob(planet, mplanets)
        
    growth_factor = planet.GrowthRate()
    rating = int(mdist-edist)
    return rating

def findBestProxy(sp, dp, mplanets):
    bestProxy = min(mplanets, key=lambda p: sp.DistanceTo(p)**2 + dp.DistanceTo(p)**2)
    if (sp.DistanceTo(bestProxy)**2 + dp.DistanceTo(bestProxy)**2) < sp.DistanceTo(dp)**2:
        return bestProxy
    return dp
    
def reinforceOwn(pw):
    """ find the weakest and most remote of own planets and enslave them to feed the bigger ones """
    mplanets = pw.MyPlanets()
    eplanets = pw.EnemyPlanets()
    fleets = pw.Fleets()
    
    if len(eplanets) <= 0 or len(mplanets) <= 0:
        return
    
    # TODO: regroup to where the enemy is closest. Find the friendly planets, which are the closest
    # to the enemy and direct regrouping flows there
    
    frontlinePlanets = []
    frontlinePlanets.append(min(mplanets, key=lambda p: p.ClosestEnemy().DistanceTo(p)))
    frontlinePlanets += filter(lambda p: p.ClosestEnemy().DistanceTo(p) < p.ClosestFriendly().DistanceTo(p), mplanets)
    frontlinePlanets.sort(lambda f,s: cmp(f.ClosestEnemy().DistanceTo(f), s.ClosestEnemy().DistanceTo(s)))

    rearPlanets = filter(lambda p: p.ClosestEnemy().DistanceTo(p) >= p.ClosestFriendly().DistanceTo(p) and p not in frontlinePlanets, mplanets)
    rearPlanets.sort(lambda f,s: cmp(f.ClosestFriendly().DistanceTo(f), s.ClosestFriendly().DistanceTo(s)))
    
    if len(frontlinePlanets) == 0 or len(rearPlanets) == 0:
        debug(len(frontlinePlanets), len(rearPlanets))
        return
    
    for sp in rearPlanets:
        
        dp = min(frontlinePlanets, key=lambda p: p.DistanceTo(sp))
        
        closest_enemy = sp.ClosestEnemy().DistanceTo(sp)
        closest_friendly = sp.ClosestFriendly().DistanceTo(sp)
        
        dp = findBestProxy(sp, dp, mplanets)
        
        if sp.DistanceTo(dp) > closest_enemy: # it's a singled out dp
            continue
        
        dispatch = safeDispatchLimit(sp, dp, mplanets, eplanets, fleets) 
        
        if closest_friendly >= closest_enemy:
            dispatch -= sp.GrowthRate() * closest_friendly
        
        if dispatch <= 0:
            continue
        
        debug(">>>> REINFORCING best planet:", sp.ID(), '>', dp.ID(), ' ^', dispatch, 'of', sp.NumShips()-1)
        pw.IssueOrder(sp.ID(), dp.ID(), dispatch)
        sp.RemoveShips(dispatch)


def attackEnemy(pw):
    """ Attack enemy, when possible """

    mplanets = pw.MyPlanets()
    eplanets = sanitizePlanets(pw.EnemyPlanets())
    nmplanets = sanitizePlanets(pw.NotMyPlanets())
    
    mfleets = pw.MyFleets()
    efleets = pw.EnemyFleets()
    fleets = pw.Fleets()
    
    mfleet_size = sum([mf.NumShips() for mf in mfleets])
    mplanets_size = sum([mp.NumShips() for mp in mplanets])
    
    eos = estimatedCharacterOffenceStrength(pw, eplanets, mplanets, efleets, mfleets)
    eds = estimatedCharacterDefenceStrength(eplanets, efleets)
    mos = estimatedCharacterOffenceStrength(pw, mplanets, eplanets, mfleets, efleets)
    mds = estimatedCharacterDefenceStrength(mplanets, mfleets)
    
    my_production = MyProduction(pw) 
    enemy_production = EnemyProduction(pw)
    
    enemy_threat = -(eos + mds)
    my_threat = (mos + eds)
    
    debug("# My total strength,    >>", mos, ' ||', mds, ' $', my_production, ' %>', my_threat, 'R:', my_threat, '>', enemy_threat)
    debug("# Enemy total strength, >>", -eos, ' ||', -eds, ' $', enemy_production, ' %>', enemy_threat)
    
    if my_production <= enemy_production:
        #TODO: be more aggressive, when production is less than opponent's, otherwise we loose anyway
        pass
    
    #if my_production > enemy_production and (enemy_threat > 0): 
    #    debug("#### Waiting to grow bigger! Staying defensive. enemy_threat:", enemy_threat)
    #    return
    #if my_production > enemy_production and (mos + eds) > -(mds + eos):
    #    debug("#### CHECKING WING ATTACK PLAN R")
    #    coordinatedAttack(pw, eplanets, mplanets, fleets, eds, mos)
    
    performCarefulOffence(pw, nmplanets, eplanets, mplanets, mfleets, fleets)
    #performCarefulOffence(pw, eplanets, eplanets, mplanets, mfleets, fleets)

def coordinatedAttack(pw, eplanets, mplanets, fleets, est_estrength, est_mstrength):
    """ In coordinated attack, all planets send their safe maximum to every enemy planet 
    to build waves of fleets that effectively overwhelm each planet """
    
    total_sent = 0
    attack_plan = []
    eplanets_strength = [(estimatedPlanetDefenceStrength(ep, fleets), ep) for ep in eplanets]
    #filter(lambda p: p[0] >= 0, [(estimatedPlanetDefenceStrength(ep, fleets), ep) for ep in eplanets])
    eplanets_strength.sort(lambda f,s: -cmp(f[0], s[0]))
    
    for dpdata, ep in eplanets_strength:
        dpds, dpowner = dpdata
        max_ships = 0
        sp_dist = 0
        sp = None
        max_ships = 0
        safelimit = 0
        
        for mp in mplanets:
            safelimit = safeDispatchLimit(mp, ep, mplanets, eplanets, fleets)
            debug("PLAN R: Checking ", mp.ID(), ">>", ep.ID(), "^", ships, "vs dpds", -dpds)    
            if ships <= 0:
                continue
            max_ships += ships
            distance = mp.DistanceTo(ep)
            if distance > sp_dist:
                continue
            sp_dist = distance
            sp = mp
        
        if not sp:
            continue
        
        debug("PLAN R: Appending plan from", sp.ID(), ">>", ep.ID(), "^", max_ships, "vs dpds", -dpds)
        attack_plan.append((ep, sp, max_ships, safelimit, dpds))
    
    for ep, sp, max_ships, safelimit, dpds in attack_plan:
        if max_ships + dpds <= 0:
            debug("PLAN R: Not enough ships for PLAN R to planet >>", ep.ID(), ' total^', max_ships, 'vs dpds', -dpds)
            continue
            
        for mp in mplanets:
            num_ships = safeDispatchLimit(mp, ep, eplanets, fleets)
            # risking or sacrificing smaller planets for bigger ones
            if num_ships <= 0 and ep.GrowthRate() - mp.GrowthRate() > 1:
                num_ships = mp.NumShips() - 1
            if num_ships <= 0 or total_sent >= max_ships:
                continue
            pw.IssueOrder(mp.ID(), ep.ID(), num_ships)
            total_sent += num_ships
            mp.RemoveShips(num_ships)
            debug("WING ATTACK PLAN R", mp.ID(), '>>', ep.ID(), 'sent ^', num_ships, 'vs', -dpds, 'total', total_sent)
            
def safeDispatchLimit(sp, dp, mplanets, eplanets, fleets):
    if len(eplanets) == 0:
        return 0
    
    distance = sp.DistanceTo(dp)
    
    closestFriendlyDistanceToSP = sys.maxint
    if len(mplanets) > 0:
        closestFriendlyDistanceToSP = sp.ClosestFriendly().DistanceTo(sp)
    
    closestEnemyDistanceToSP = sp.ClosestEnemy().DistanceTo(sp)
    efleets = filter(lambda f: f.Owner() > 1, fleets)
    
    # NOTE: defence strength takes only enemy fleets into account!
    spds,spowner = estimatedPlanetDefenceStrength(sp, efleets, uncertainty_limit=closestEnemyDistanceToSP)
    if spowner != 1:
        return 0
    
    # TODO: take incoming fleets into account and never dispatch too much, when there is an
    # inbound enemy fleet
    # incomingFleets = sp.IncomingFleets()
    # if len(incomingFleets) > 0:
       # # Analyze incoming fleets to see, if there are any threats
       # spefleets_turns = mapFleetsToTurns(incomingFleets)
       
       # for turn, tsefleets in spefleets_turns:
           # spds_turn,spowner_turn = estimatedPlanetDefenceStrength(dp, fleets, 
               # uncertainty_limit=min(closestEnemyDistanceToSP, turn))
           # if spowner_turn != 1:
               # return 0
    
    if dp.Owner() == 1:
        allowed = min(sp.NumShips() - 1, spds)
        sp.RemoveShips(allowed)
        spds,spowner = estimatedPlanetDefenceStrength(sp, fleets, uncertainty_limit=closestEnemyDistanceToSP)
        sp.AddShips(allowed)

        if spowner != 1:
            return 0

        debug("Reinforcements:", sp.ID(), '>', dp.ID(), '(own)   spds', spds, \
            ' safeline:', spds, ' allowed final:', allowed)
 
        return allowed
    
    calcOffencePotentialVsSP = lambda ep: estimatedPlanetOffencePotential(ep, sp, fleets)
    
    ep = min(eplanets, key=calcOffencePotentialVsSP)
    epos = min(calcOffencePotentialVsSP(ep), 0)
    
    eplanetsnodp = filter(lambda ep: ep.ID() != dp.ID(), eplanets)
    
    # enemies closer than any of the friendlies must be counted as one cumulative threat
    closestEnemiesToSP = filter(lambda ep: ep.DistanceTo(sp) <= closestFriendlyDistanceToSP, eplanetsnodp)
    epgos = min(sum([calcOffencePotentialVsSP(ep) for ep in closestEnemiesToSP]), 0)
    
    max_eos = min(epos, epgos)
    
    # simple case shortcut for single-planet enemy
    if dp.Owner() > 1 and len(eplanets) == 1: # if target is the enemy bot
        allowed = min(spds + max_eos, sp.NumShips() - 1)
        if allowed > 0:
            debug("Attack dispatch single planet: ", allowed, 'of', sp.NumShips())
            return allowed
        else:
            return 0
    
    dpds,dpowner = estimatedPlanetDefenceStrength(dp, fleets, uncertainty_limit=dp.ClosestEnemy().DistanceTo(dp))
    
    # defensive analysis: compare projected planet strength of our 
    # planet to offence potential of the enemy planet
    # we're safe and sound for spds + max_eos > 0
    # we're good to attack the enemy, while spds + epos + dpds > 0
    limit = min(spds + max_eos, sp.NumShips() - 1)
    
    #if limit >= 0:
    #    debug("        ", sp.ID(), '>', dp.ID(), '<>', sp.DistanceTo(dp), \
    #     ' spds', spds, ' max eos', -max_eos, ' safeline:', spds + max_eos, ' allowed final:', limit)
    #    pass
    
    if spds + max_eos > 0 and dpowner != 1:
        #debug("        * Allowing attack limit: ", limit, 'of', sp.NumShips())
        return limit
        
    return 0 # restrict attacks

def getDispatchFeasibility(sp, dp, closestEPToSP, closestEnemyDistanceToSP, closestEPToDP, closestEnemyDistanceToDP):
    feasibility = 0

    feasibility = sp.GrowthRate() * closestEnemyDistanceToSP - closestEPToDP.GrowthRate() * sp.DistanceTo(dp)
    if dp.Owner() == 1:
        feasibility -= closestEPToDP.GrowthRate() * closestEnemyDistanceToDP
    elif dp.Owner() > 1:
        feasibility += dp.GrowthRate() * closestEnemyDistanceToDP
    
    return feasibility
    
def performCarefulOffence(pw, dplanets, eplanets, mplanets, mfleets, fleets):
    dplanets_ratings = [(dp, planetRating(dp, eplanets, mplanets, fleets)) for dp in dplanets]
    dplanets_ratings.sort(lambda f,s: -cmp(f[1], s[1]))
    
    if len(eplanets) == 0 or len(dplanets) == 0:
        return
    
    for dp,dprating in dplanets_ratings:
        
        eplanetsnodp = filter(lambda ep: ep.ID() != dp.ID(), eplanets)
        closestEnemyDistanceToDP = 0
        
        if len(eplanetsnodp) > 0:
            closestEnemyDistanceToDP = min([dp.DistanceTo(ep) for ep in eplanetsnodp])
        
        dpds, dpowner = estimatedPlanetDefenceStrength(dp, fleets, uncertainty_limit=closestEnemyDistanceToDP)
        
        debug( "# DP: >", dp.ID(), "own:", dp.Owner(), 'Proj.owner:', dpowner, " +", dp.GrowthRate(), " ^", dp.NumShips(), " R", dprating)
        
        if dpowner == 1: # already successfully attacked by me
            continue 
        
        dispatch_plan = []
        avg_dpdp = 0
        
        # closest first
        for sp in mplanets:
            attacklimit = safeDispatchLimit(sp, dp, mplanets, eplanets, fleets)
            dpdp = estimatedPlanetDefencePotential(sp, dp, dpowner, dpds, fleets)
            dispatch_plan.append((attacklimit, dpdp, sp))
        
        dispatch_plan.sort(lambda f,s: cmp(f[1], s[1]))
        
        calcOffencePotentialVsDP = lambda ep: estimatedPlanetOffencePotential(ep, dp, fleets)
        
        min_dpdp_source = None
        
        for limit, dpdp, sp in dispatch_plan:
        
            if limit < dpdp + 1:
                continue
            
            closestEnemyToSP = sp.ClosestEnemy()
            
            # enemies closer than any of the friendlies must be counted as one cumulative threat
            calcOffencePotentialVsSP = lambda ep: estimatedPlanetOffencePotential(ep, sp, fleets)
            
            ff = [Fleet(sp.Owner(), limit, 1, dp.ID(), 0, sp.DistanceTo(dp))]
            
            dpds_after,dpowner_after = estimatedPlanetDefenceStrength(dp, fleets, 
                fanthom_fleets = ff, uncertainty_limit=closestEnemyDistanceToDP)
            
            calcOffencePotentialVsDP_After = lambda p: calcOffencePotentialVsDP(p) + \
                (ep.DistanceTo(dp) - sp.DistanceTo(dp)) * ep.GrowthRate()
            
            eposdp = 0
            
            if len(eplanetsnodp):
                epdp = max(eplanetsnodp, key=lambda p: calcOffencePotentialVsDP_After(p))
                eposdp = min(calcOffencePotentialVsDP_After(epdp), 0)
            
            enemiesCloserToDP = filter(lambda ep: ep.DistanceTo(dp) <= sp.DistanceTo(dp), eplanetsnodp)
            epgosdp = min(sum([calcOffencePotentialVsDP_After(ep) for ep in enemiesCloserToDP]), 0)
            
            max_eosdp = min(eposdp, epgosdp)
            
            #debug('dpds_after', dpds_after, 'owner after', dpowner_after, 'max_eosdp', -max_eosdp, 'from', -eposdp, -epgosdp)
            
            need = dpdp + 1 - dpds_after - max_eosdp if dpds_after < -max_eosdp else dpdp + 1
            
            debug(">>", dp.ID(), "after capture:", 'limit', limit, 'dpdp', dpdp, 'dpds_after', dpds_after, \
            'max eposdp', -max_eosdp, 'need', need)
            
            # risking or sacrificing smaller planets for bigger planets
            if limit < need and dp.GrowthRate() - sp.GrowthRate() > 1:
                limit = sp.NumShips() - 1
            
            if limit < need and (sp.DistanceTo(dp) * 2 < closestEnemyDistanceToDP):
                debug('ATTACKING with MINIMAL FORCE of ', dpdp + 1, 'limit:', limit)
                min_dpdp_source = (limit, dpdp + 1, sp)
                continue
            
            min_dpdp_source = (limit, need, sp)
            
        if not min_dpdp_source:
            continue
        
        attacklimit, dispatch, sp = min_dpdp_source
        dp = findBestProxy(sp, dp, mplanets)
        
        if dpowner != 1 and dispatch <= attacklimit:
            debug(">>>>>>>> ATTACKING:", sp, ">", dp.ID(), '<>', sp.DistanceTo(dp), "need:", need, "have:", sp.NumShips(), '>>', dispatch, 'vs', dp.NumShips())
            pw.IssueOrder(sp.ID(), dp.ID(), dispatch)
            sp.RemoveShips(dispatch)

    
def planetDistanceBlob(planet, planets):
    if len(planets) <= 0:
        return sys.maxint
    return float(sum([planet.DistanceTo(p) for p in planets])) / float(len(planets))

def planetDistanceAndGrowthBlob(planet, planets):
    if len(planets) <= 0:
        return sys.maxint
    return float(sum([planet.DistanceTo(p) * p.GrowthRate() for p in planets])) / float(len(planets))

def planetRating(planet, eplanets, mplanets, fleets):
    edist = 0
    if len(eplanets) > 0:
        edist = planetDistanceBlob(planet, eplanets)
    
    mdist = 0
    if len(mplanets) > 0:
        mdist = planetDistanceBlob(planet, mplanets)
    
    growth_factor = float(planet.GrowthRate())+1e-28
    rating = int(float(edist) - float(mdist)) * growth_factor - planet.NumShips() / growth_factor
    return rating
    
def estimatedCharacterDefenceStrength(planets, fleets):
    return sum([-pds if pdowner != 1 else pds for pds,pdowner in [estimatedPlanetDefenceStrength(p, fleets) for p in planets]])

def estimatedCharacterOffenceStrength(pw, splanets, dplanets, sfleets, dfleets):
    """ """
    if len(splanets) == 0 or len(dplanets) == 0:
        return 0
    
    planetStrength = sum([
        sum([ estimatedPlanetCarefulOffencePotential(sp, dp, dfleets, 
            uncertainty_limit = sp.ClosestEnemy().DistanceTo(sp)) 
            for sp in splanets ]) / float(len(dplanets))
                for dp in dplanets])
    
    return int(planetStrength)

def effectiveFleetStrength(pw, fleet):
    dp = pw.GetPlanet(fleet.Destination())
    dpgrowth = 0
    if dp.Owner() != 0 and dp.Owner() != fleet.Owner():
        dpgrowth = fleet.TurnsRemaining() * dp.GrowthRate()
    
    return fleet.NumShips() - dpgrowth
    
def estimatedPlanetDefenceStrength(planet, fleets, fanthom_fleets = [], uncertainty_limit = 0):
    """ Estimate planet defensive strength, i.e. how much it can hold up by itself """
    gr = planet.GrowthRate()
    
    powner = planet.Owner()
    pstrength = planet.NumShips()
    
    lfleets = filter(lambda f: f.Destination() == planet.ID(), fleets) + fanthom_fleets
    
    if uncertainty_limit > 0:
        lfleets = filter(lambda f: f.TurnsRemaining() <= uncertainty_limit, lfleets)
    
    if (len(lfleets)) == 0:
       #debug("pds for:", planet.ID(), '@', uncertainty_limit, (pstrength, powner))
       return (pstrength, powner)
    
    turn_list = mapFleetsToTurns(lfleets)
    
    curturn = 0
    #debug("pds for:", planet.ID(), '@', uncertainty_limit);
    for turn,turn_fleets in turn_list:
        
        turns_interval = (turn - curturn)
        curturn = turn
        my_force = sum([f.NumShips() if f.Owner() == 1 else 0 for f in turn_fleets])
        e_force = sum([f.NumShips() if f.Owner() > 1 else 0 for f in turn_fleets])
        #debug("   o", planet.ID(), '#', turn, '<>', turns_interval, 'owner:', powner, '>< p', pstrength, 'm', my_force, 'e', e_force, 'gr', turns_interval * gr)
        if powner == 0:
            # neutral planets always have their ships decimated with no growth
            # If two enemies meet on a neutral planet, the two strongest will fight with each other
            sides = [[0, pstrength], 
                [1, my_force], 
                [2, e_force]]

            while sides:
                smallest  = min(sides, key=lambda x: x[1])
                sides_max = []
                for s in sides:
                    if s[0] == smallest[0]:
                        continue
                    s[1] -= smallest[1]
                    sides_max.append(s)
                sides = sides_max
            
            pstrength = smallest[1]
            powner = smallest[0]
        elif powner == 1:
            pstrength += my_force
            pstrength -= e_force
            pstrength += turns_interval * gr

            if pstrength < 0:
                powner = 2
                pstrength = -pstrength
                
        elif powner == 2:
            pstrength -= my_force
            pstrength += e_force
            pstrength += turns_interval * gr

            if pstrength < 0:
                powner = 1
                pstrength = -pstrength
    
    #debug("   final:", pstrength, powner);
    return (pstrength, powner)

def estimatedPlanetDefencePotential(sp, dp, dpowner, dpds, fleets):
    """ Calculate the potential of a planet to defend against any attack. Number represents exactly, 
    how many ships must be sent to the planet to capture it. """
    if dpowner == 0: # neutral planets don't grow
        return dpds
    else:
        distance = sp.DistanceTo(dp)
        growthrate = dp.GrowthRate()
        return dpds + growthrate * distance

def estimatedPlanetOffencePotential(sp, dp, fleets, noGrowth = False):
    """ Calculate the potential of a source planet (sp) to build a successful 
    'all-out' attack on another, dp. Result number represents exactly how many
    ships will be left after the attack.
    """
    distance = sp.DistanceTo(dp)
    
    if sp.Owner() == 0 or dp.Owner() == sp.Owner():
        return 0
    
    growth = dp.GrowthRate()
    
    if dp.Owner() == 0 or noGrowth:
        growth = 0
    
    pstrength = 0
    #debug("#### planet offence potential", sp.ID(), '>', dp.ID(), ' <>', distance)
    if sp.Owner() != 1: # enemy
        pstrength = -sp.NumShips()
        pstrength += growth * distance
    elif sp.Owner() == 1: # me
        pstrength = sp.NumShips()
        pstrength -= growth * distance
    #debug("#### planet offence potential", sp.ID(), '>', dp.ID(), ' <>', distance, pstrength)
    return pstrength

def estimatedPlanetCarefulOffencePotential(sp, dp, fleets, fanthom_fleets = [], uncertainty_limit = -1, noGrowth = False):
    """ Calculate the potential of a planet to build a successful 'careful' attack on another,
    i.e. the one, which would not compromize its own defences. The number is the amount of ships
    available for an offensive dispatch """
    
    sp_off_potential = estimatedPlanetOffencePotential(sp, dp, fleets, noGrowth = noGrowth)
    #dp_off_potential = estimatedPlanetOffencePotential(sp, dp, fleets, noGrowth = True)
    #sp_def_strength, spowner = estimatedPlanetDefenceStrength(sp, fleets, fanthom_fleets = fanthom_fleets, uncertainty_limit = uncertainty_limit)

    #debug("- careful offence potential", sp.ID(), '>', dp.ID(), ' <>', sp.DistanceTo(dp), sp_def_strength, \
    #'-', sp_off_potential, '=', sp_def_strength - sp_off_potential)
    
    return sp_off_potential# - dp_off_potential
    
def sanitizePlanets(planets):
    """ Filter out wholly undesirable planets """
    rplanets = []
    for p in planets:
        if p.GrowthRate() > 0:
            rplanets.append(p)
    return rplanets

def MyProduction(pw):
    planets = pw.MyPlanets();
    production = 0
    for p in planets:
        production += p.GrowthRate()
    return production

def EnemyProduction(pw):
        planets = pw.EnemyPlanets();

        production = 0
        for p in planets:
            production += p.GrowthRate()
        return production

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
        
