#!/usr/bin/env python
#

from math import modf, floor, ceil, sqrt
from sys import stdout
import sys
from debug import debug

class Fleet:
    def __init__(self, owner, num_ships, source_planet, destination_planet, \
     total_trip_length, turns_remaining):
        self._owner = owner
        self._num_ships = num_ships
        self._source_planet = source_planet
        self._destination_planet = destination_planet
        self._total_trip_length = total_trip_length
        self._turns_remaining = turns_remaining

    def Owner(self):
        return self._owner

    def NumShips(self):
        return self._num_ships

    def Source(self):
        return self._source_planet

    def Destination(self):
        return self._destination_planet

    def TotalTripLength(self):
        return self._total_trip_length

    def TurnsRemaining(self):
        return self._turns_remaining

    def __repr__(self):
        return "F(%d) #%d %s >> %s ETA %d" % (self._owner, self._num_ships, self._source_planet, self._destination_planet, self._turns_remaining)
        

def mapFleetsToTurns(fleets):
    if len(fleets) == 0:
        return []
    fleets.sort(cmp, key=lambda f: f.TurnsRemaining())
    first = fleets[0]
    turnDict = {first.TurnsRemaining() : [first.NumShips() if first.Owner() == 1 else 0, first.NumShips() if first.Owner() != 1 else 0]}
    #debug("mapFleetsToTurnsStart:", turnDict, fleets)
    curturn = 0

    for f in fleets[1:]:
        turn = f.TurnsRemaining()
        if curturn == 0:
            curturn = turn
        #debug("mapFleetsToTurnsStart: @", turn, curturn, turnDict)
        if curturn != turn:
            curturn = turn
            
        if turn not in turnDict:
            turnDict[turn] = [0,0]
            
        if f.Owner() == 1:
            turnDict[turn][0] += f.NumShips()
        else:
            turnDict[turn][1] += f.NumShips()
    
    #debug("MapFleetsToTurns", turnDict)
    turnList = map(lambda item: (item[0], item[1][0], item[1][1]), turnDict.items())
    turnList.sort(cmp, key=lambda f: f[0])
    return turnList

class Planet:
    def __init__(self, pw, planet_id, owner, num_ships, growth_rate, x, y):
        self._pw = pw
        self._planet_id = planet_id
        self._owner = owner
        self._num_ships = num_ships
        self._growth_rate = growth_rate
        self._x = x
        self._y = y
        self._reserve = 0
        
    def __repr__(self):
        return "P%d(%d) ^%d(%d) +%d" % (self._planet_id, self._owner, self._num_ships, self._reserve, self._growth_rate)
        
    def ID(self):
        return self._planet_id

    def Owner(self, new_owner=None):
        if new_owner == None:
            return self._owner
        self._owner = new_owner

    def NumShipsDispatch(self):
        return max(self._num_ships - self._reserve, 0)
    
    def NumShipsReserve(self):
        return self._reserve
 
    def NumShips(self, new_num_ships=None):
        if new_num_ships == None:
            return self._num_ships
        self._num_ships = new_num_ships

    def GrowthRate(self):
        return self._growth_rate

    def X(self):
        return self._x

    def Y(self):
        return self._y

    def AddShips(self, amount):
        self._num_ships += amount

    def RemoveShips(self, amount):
        self._num_ships -= amount

    def ReserveShips(self, amount):
        self._reserve += amount
        
    def DistanceTo(self, destination):
        if getattr(self, '_distanceTo', None) == None:
            self._distanceTo = dict()
        destId = destination.ID()
        if destId not in self._distanceTo:
            self._distanceTo[destId] = self._pw.Distance(self, destination)
        return self._distanceTo[destId]
    
    def ClosestEnemy(self, exclude=[], haveDebug=False): # TODO: implement exclude
        if len(self._pw.EnemyPlanets()) == 0:
            self._closestEnemy = self
	    self._closestEnemyDistance = 0
            return (self._closestEnemy, self._closestEnemyDistance)
        if getattr(self, '_closestEnemy', None) == None:
            self._closestEnemy = self._pw.Planets()[0]
            eplanets = filter(lambda p: p.ID() != self.ID() and p.ID() not in exclude, self._pw.EnemyPlanets())
            if len(eplanets) > 0:
                self._closestEnemy = min(eplanets, key=lambda p: p.DistanceTo(self))
            
            self._closestEnemyDistance = self._closestEnemy.DistanceTo(self)
            closer = filter(lambda p: p.ID() != self.ID() and
				p.ID() not in exclude and 
                p.DistanceTo(self) < self._closestEnemyDistance, self._pw.NotEnemyPlanets())
            
            for p in closer:
                pstrength, powner = p.CombineIncomingFleets(turnlimit=self._closestEnemyDistance)
                if powner == 2:
                    myturn = self._closestEnemyDistance
                    distance = p.DistanceTo(self)
                    for turn, mstr, estr in p.GetIncomingFleetTurns():
                        if turn + distance >= self._closestEnemyDistance:
                            continue
                        pstrength, powner = p.CombineIncomingFleets(turnlimit=self._closestEnemyDistance)
                        if powner == 2:
                            myturn = turn
                            break
                    if myturn + distance < self._closestEnemyDistance:
                        self._closestEnemy = p
                        self._closestEnemyDistance = p.DistanceTo(self) + myturn
        
        return (self._closestEnemy, self._closestEnemyDistance)
        
    def ClosestEnemyDistance(self, exclude=[], haveDebug=False): # TODO: implement exclude
        if getattr(self, '_closestEnemyDistance', None) == None:
            self.ClosestEnemy(exclude=exclude, haveDebug=haveDebug)
        return self._closestEnemyDistance
        
    def ClosestFriend(self, exclude=[], haveDebug=False): # TODO: implement exclude
        """ Returns and saves the closest planet owned by the bot """
        if len(self._pw.MyPlanets()) == 0:
            self._closestFriend = self
            return self._closestFriend
        if getattr(self, '_closestFriend', None) == None:
            self._closestFriend = self
            mplanets = filter(lambda p: p.ID() != self.ID() and p.ID() not in exclude, self._pw.MyPlanets())
            if len(mplanets) > 0:
                self._closestFriend = min(mplanets, key=lambda p: p.DistanceTo(self))
            self._closestFriendDistance = self._closestFriend.DistanceTo(self)
            closer = filter(lambda p: p.ID() != self.ID() and 
                p.DistanceTo(self) < self._closestFriendDistance and
				p.ID() not in exclude, self._pw.NotMyPlanets())
            
            for p in closer:
                pstrength, powner = p.CombineIncomingFleets(turnlimit=self._closestFriendDistance)
                distance = p.DistanceTo(self)
                if powner == 1:
                    myturn = self._closestFriendDistance
                    for turn, mstr, estr in p.GetIncomingFleetTurns():
                        if turn + distance >= self._closestFriendDistance:
                            break
                        pstrength, powner = p.CombineIncomingFleets(turnlimit=turn)
                        if powner == 1:
                            myturn = turn
                            break
                    if myturn + distance < self._closestFriendDistance:
                        self._closestFriend = p
                        self._closestFriendDistance = p.DistanceTo(self) + myturn
                        
        return (self._closestFriend, self._closestFriendDistance)
    
    def ClosestFriendDistance(self, exclude=[], haveDebug=False): # TODO: implement exclude
        if getattr(self, '_closestFriendDistance', None) == None:
            self.ClosestFriend(exclude=exclude, haveDebug=haveDebug)
        return self._closestFriendDistance
        
    def IncomingFleets(self):
        if getattr(self, '_incomingfleets', None) == None:
            self._incomingfleets = filter(lambda f: f.Destination() == self.ID(), self._pw.Fleets())
            self._incomingfleets.sort(cmp, key=lambda f: f.TurnsRemaining())
        return self._incomingfleets
    
    def CombineIncomingFleets(self, ff=[], turnlimit=sys.maxint, haveDebug=False):
        """ Estimate planet defensive strength, i.e. how much it can hold up by itself """
        if not ff and getattr(self, '_incomingfleetscombined', None) != None:
            if turnlimit not in self._incomingfleetscombined:
                closest = max(filter(lambda t: t < turnlimit, self._incomingfleetscombined.keys()))
                closeststr, cowner = self._incomingfleetscombined[closest]
                gr = self._growth_rate if cowner != 0 else 0
                strength = closeststr + gr * (turnlimit - closest)
                if haveDebug:
                    debug('turnlimit', turnlimit,'not in combined fleets for ', self.ID(), 'adding:', strength, cowner)
                self._incomingfleetscombined[turnlimit] = (strength, cowner)
            if haveDebug:
                debug(self.ID(), '@', turnlimit, self._incomingfleetscombined[turnlimit])
            return self._incomingfleetscombined[turnlimit]
            
        powner = self._owner
        gr = self._growth_rate if powner != 0 else 0
        pstrength = 0
        pstrength += self._num_ships
        
        if not ff and not getattr(self, '_incomingfleetscombined', None):
            self._incomingfleetscombined = { 0 : (pstrength, powner) }
        
        if not ff:
            self._incomingfleetscombined[sys.maxint] = (pstrength, powner)
        
        turnList = self.GetIncomingFleetTurns(ff=ff)
        curturn = turnList[0][0] if len(turnList) > 0 else 0
        
        if haveDebug:
            debug("Combining fleets for:", self.ID(), '@', turnlimit, turnList)
            
        for turn,mforce,eforce in turnList:
            turns_interval = (turn - curturn)
            gr = self._growth_rate if powner != 0 else 0
            
            if ff and turn > turnlimit:
                return (pstrength, powner)
            
            if not ff:
                for t in xrange(curturn, turn):
                    if haveDebug:
                        debug("adding: @", t, pstrength + (t - curturn) * gr)
                    self._incomingfleetscombined[t] = (pstrength + (t-curturn) * gr, powner)
                    
            curturn = turn
            if haveDebug:
                debug("   >>>", self.ID(), '@', turn, '<>', turns_interval, 'owner:', powner, \
                    '>< p', pstrength, 'm', mforce, 'e', eforce, 'gr', turns_interval * gr)
            
            pstrength += turns_interval * gr
            
            if powner == 0:
                # neutral planets always have their ships decimated with no growth
                # If two enemies meet on a neutral planet, the two strongest will fight with each other
                sides = [[0, pstrength], [1, mforce], [2, eforce]]
                while sides:
                    smallest = min(sides, key=lambda x: x[1])
                    sides_max = []
                    for s in sides:
                        if s[0] == smallest[0]:
                            continue
                        s[1] -= smallest[1]
                        sides_max.append(s)
                    sides = sides_max
                if smallest[1] > 0:
                    powner = smallest[0]
                pstrength = smallest[1]
            elif powner == 1:
                pstrength += mforce
                pstrength -= eforce
                if pstrength < 0:
                    powner = 2
                    pstrength = -pstrength
            elif powner == 2:
                pstrength -= mforce
                pstrength += eforce
                if pstrength < 0:
                    powner = 1
                    pstrength = -pstrength
            #debug("   >", self.ID(), '@', turn, '<>', turns_interval, 'owner:', powner, '>< p', \
            #pstrength, 'm', mforce, 'e', eforce, 'gr', turns_interval * gr)
        if ff:
            return (pstrength, powner)
        
        if not ff:
            self._incomingfleetscombined[curturn] = (pstrength, powner)
        
        gr = self._growth_rate if powner != 0 else 0
        
        if turnlimit < sys.maxint:
            for t in xrange(curturn, turnlimit+1):
                if haveDebug:
                    debug("adding: @", t, pstrength + (t - curturn) * gr, gr, powner, curturn)
                self._incomingfleetscombined[t] = (pstrength + (t-curturn) * gr, powner)
        
        if turnlimit == sys.maxint or sys.maxint not in self._incomingfleetscombined:
            self._incomingfleetscombined[sys.maxint] = (pstrength, powner)
            
        if turnlimit not in self._incomingfleetscombined:
            closest = max(filter(lambda t: t < turnlimit, self._incomingfleetscombined.keys()))
            closeststr, owner = self._incomingfleetscombined[closest]
            gr = self._growth_rate if owner != 0 else 0
            strength = closeststr + gr * (turnlimit - closest)
            self._incomingfleetscombined[turnlimit] = (strength, owner)
        
        if haveDebug:
            debug("   final for:", self.ID(), pstrength, powner, "@", turnlimit, 
                ":", self._incomingfleetscombined[turnlimit]);
            
        return self._incomingfleetscombined[turnlimit]
     
    def FindMinimumStrength(self): 
        incomingFleetTurns = self.GetIncomingFleetTurns()
	    #debug("     ", dp.ID(), "There are incoming fleets:", len(incomingFleets))
        pds,powner = self.CombineIncomingFleets(turnlimit=0)

        for turn,es,ms in incomingFleetTurns:
            _pds, _powner = self.CombineIncomingFleets(turnlimit=turn)
            #debug("     planet:", dp.ID(), "fleets @", turn, 'spds:', _spds, 'owner:', _spowner)
            if _powner != self.Owner():
                pds = 0
            elif pds > _pds:
                pds = _pds
        return pds
    
    def GetIncomingFleetTurns(self, ff=[]):
        if not ff and getattr(self, '_turnList', None) != None:
            return self._turnList
            
        fleets = list(self.IncomingFleets() + ff)
        if len(fleets) == 0:
            self._turnList = []
            return self._turnList
        
        fleets.sort(cmp, key=lambda f: f.TurnsRemaining())
        first = fleets[0]
        turnDict = {first.TurnsRemaining() : 
            [first.NumShips() if first.Owner() == 1 else 0, 
                first.NumShips() if first.Owner() != 1 else 0]}
        #debug("mapFleetsToTurnsStart:", turnDict, fleets)
        curturn = 0

        for f in fleets[1:]:
            turn = f.TurnsRemaining()
            if curturn == 0:
                curturn = turn
            
            if curturn != turn:
                curturn = turn
                
            if turn not in turnDict:
                turnDict[turn] = [0,0]
                
            if f.Owner() == 1:
                turnDict[turn][0] += f.NumShips()
            else:
                turnDict[turn][1] += f.NumShips()
        
        #debug("MapFleetsToTurns", turnDict)
        turnList = map(lambda item: (item[0], item[1][0], item[1][1]), turnDict.items())
        turnList.sort(cmp, key=lambda f: f[0]) # TODO: optimize: is this needed?
        
        if ff:
            return turnList
            
        self._turnList = turnList
        return self._turnList
    
    def SetRescued(self, rescued):
        self._rescued = rescued
    
    def IsRescued(self):
        if getattr(self, '_rescued', None) == None:
            self._rescued = False
        return self._rescued
    
    def GetLocalGroup(self, threatDist):
        return self._pw.GetLocalGroup(self, threatDist)
    
    def GetLocalGroupDefenceStrength(self, threatDist, ff=[], haveDebug=False):
        if getattr(self, '_localGroupDefenceStrength', None) == None:
            self._localGroupDefenceStrength = dict()
        
        if not ff and threatDist in self._localGroupDefenceStrength:
            return self._localGroupDefenceStrength[threatDist]
        
        pgds = 0
        localGroup = self.GetLocalGroup(threatDist)
        
        if haveDebug:
            debug("     pgds for", self.ID(), "localGroup:", localGroup)
            
        powner = self._owner
        for p in localGroup:
            safeDistance = max(0, threatDist - p.DistanceTo(self))
            pds, gpowner = p.CombineIncomingFleets(ff=ff, turnlimit=safeDistance)
            if gpowner != powner or gpowner == 0:
                continue
            pgds += pds
            
        if ff:
            return pgds
    
        if haveDebug:
            debug("     pgds for", self.ID(), "@", threatDist, ":", pgds)
        self._localGroupDefenceStrength[threatDist] = pgds
        return self._localGroupDefenceStrength[threatDist]
        
    def GetLocalThreatStrength(self, threatDist, ff=[]):
        if getattr(self, '_localGroupOffenceStrength', None) == None:
            self._localGroupOffenceStrength = dict()
        
        spds, spowner = self.CombineIncomingFleets(turnlimit=threatDist, ff=ff)
        #debug(spds, spowner, '@', threatDist, ff)
        
        if not ff and threatDist in self._localGroupOffenceStrength:
            return self._localGroupOffenceStrength[threatDist]
        
        localEnemyGroup = filter(lambda p: 
            p.CombineIncomingFleets(turnlimit=threatDist)[1] not in [spowner, 0],
            self.GetLocalGroup(threatDist))
            
        threatstrength = 0
        for p in localEnemyGroup:
            offThreat = p.GetOffensiveThreat(self, turnlimit=threatDist)
            threatstrength += max(offThreat, 0)
        
        #if len(localEnemyGroup) > 0:
        #    debug('    localThreatStrength:', self.ID(), len(localEnemyGroup), threatstrength)
        
        if ff:
            return threatstrength
            
        self._localGroupOffenceStrength[threatDist] = threatstrength
        return self._localGroupOffenceStrength[threatDist]
    
    def GetOffensiveThreat(self, dp, turnlimit=sys.maxint, haveDebug=False):
        """ Calculate the potential of a source planet (self) to build a successful 
        'all-out' attack on another, dp. Result number represents exactly how many
        ships will be left after the attack.
        """
        if getattr(self, '_offensiveThreat', None) == None:
            self._offensiveThreat = dict()
        
        dpid = dp.ID()

        if dpid == self.ID():
            return -self.NumShipsDispatch()

        if dpid in self._offensiveThreat:
            if turnlimit in self._offensiveThreat[dpid]:
                return self._offensiveThreat[dpid][turnlimit]
        else:
            self._offensiveThreat[dpid] = dict()
        
        distance = self.DistanceTo(dp)
        
        limit = min(distance, turnlimit) 
        dpstrength, dpowner = dp.CombineIncomingFleets(turnlimit=0)
        maxstrength, maxstrengthowner = self.CombineIncomingFleets(turnlimit=0)
        if maxstrengthowner == 0:
            maxstrength = 0
        elif maxstrengthowner == dpowner:
            maxstrength = -maxstrength
        maxstrengthturn = 0
        dgrowth = dp.GrowthRate() if maxstrengthowner != 0 and maxstrengthowner != dpowner else 0
        maxstrength -= dgrowth * distance
        turnsOfInterest = filter(lambda t: t[0] < limit+1, self.GetIncomingFleetTurns())
        turnsOfInterest.sort(cmp, key=lambda i: i[0])
        
        if len(turnsOfInterest) > 0:
            turnsOfInterest += [(limit, 0, 0)]
        elif maxstrengthowner != 0:
            turnsOfInterest += [(limit, 0, 0)]
        
        for turn, ms, es in turnsOfInterest:
            spstrength, spowner = self.CombineIncomingFleets(turnlimit=turn)
            dpstrength, dpowner = dp.CombineIncomingFleets(turnlimit=turn)
            
            if spowner == 0 or spowner == dpowner:
                continue
            
            dgrowth = dp.GrowthRate() if dpowner != 0 and dpowner != spowner else 0
            spstrength -= dgrowth * (distance + turn)
            if spowner != dpowner and maxstrength < spstrength:
                maxstrength = spstrength
                maxstrengthturn = turn
                maxstrengthowner = spowner
        
        if haveDebug:
            debug("      pOffThreat:", self.ID(), ">", dp.ID(), maxstrength, \
                        '@', maxstrengthturn, '@limit:', limit)
        
        if maxstrengthowner == 0:
            self._offensiveThreat[dpid][turnlimit] = 0
        else:
            self._offensiveThreat[dpid][turnlimit] = maxstrength
            
        return self._offensiveThreat[dpid][turnlimit]
    
    def SafeDispatchLimit(self, haveDebug=False):
        if getattr(self, '_safeDispatchLimit', None) != None:
            return min(self.NumShipsDispatch(), max(0, self._safeDispatchLimit - self._reserve))
            
        spds,spowner = self.CombineIncomingFleets(turnlimit=0)
        
        if spowner != self.Owner():
            return 0
        
        incomingFleetTurns = set(map(lambda f: f.TurnsRemaining(), self.IncomingFleets()))
        minspdsTurn = 0
        minspds = spds
        
        minspds = self.FindMinimumStrength()
 
        if minspds <= 0:
            return 0
        
        closestFriendlyDistanceToSP = self.ClosestFriendDistance()
       
        planets = filter(lambda p: p.ID() != self.ID(), self._pw.Planets())
        
        ep, epos = max(map(lambda ep: (ep, ep.GetOffensiveThreat(self,
                haveDebug=True,
                turnlimit=max(0, closestFriendlyDistanceToSP - ep.DistanceTo(self)))), planets), 
                key=lambda epi: epi[1])
        
        epgos = self.GetLocalThreatStrength(closestFriendlyDistanceToSP)
        
        # find the closest threat
        for turn in xrange(closestFriendlyDistanceToSP + 1, ep.DistanceTo(self) + 1):
            epgos = self.GetLocalThreatStrength(turn)
            distanceEnemyToSP = turn
            if epgos > epos: # NB! comparing absolute values!
                break
        
        maxeos = max(epgos, epos)
        # NB! comparing absolute values of epos & epgos!
        closestEnemyDistanceToSP = self.ClosestEnemyDistance()
        distanceEnemyToSP = closestEnemyDistanceToSP if epos < epgos else ep.DistanceTo(self)
        spgds = minspds + self.GetLocalGroupDefenceStrength(distanceEnemyToSP - 1)
        
        if haveDebug:
            debug("     SAFE DISPATCH LIMIT:", self.ID(), "spds:", spds, "spgds:", spgds,
            "epos:", epos, "(%d @%d @@%d)" % (ep.ID(), ep.DistanceTo(self), max(0, closestFriendlyDistanceToSP - ep.DistanceTo(self))),
            "epgos:", epgos, "Final:", spgds, maxeos, '=', spgds - maxeos,
            " of self", self.NumShipsDispatch())
            debug("      >>  closestFriendly@", closestFriendlyDistanceToSP, "enemy@", distanceEnemyToSP)
            
        # defensive analysis: compare strength of our planet 
        # to offence potential of the enemy planet
        # we're safe and sound for spds + max_eos > 0
        # we're good to attack the enemy, while spds + epos + dpds > 0
        #debug('Left before attack: ', self.NumShips(), '? >', max_mds + max_eos, self, self.ID())
        self._safeDispatchLimit = max(spgds - maxeos - self._reserve, 0)
        return min(self.NumShipsDispatch(), self._safeDispatchLimit)
        
    def getTurnsWait(self, dp, maxturns, needed, available, used, eplanets):
        if getattr(self, '_turnsWait', None) == None:
            self._turnsWait = dict()
        
        dpid = dp.ID()
        
        if dpid in self._turnsWait:
            return self._turnsWait[dpid]
        
        if needed <= available:
            return 0
        
        turnswait = maxturns
        needmore = float(needed - available)
        distance = self.DistanceTo(dp)
        
        # Minimize the amount of iterations, by pre-calculating the minimum possible
        # turn, where it could reach the desired value (by using the older approach
        # of getting the closest incoming fleet and calculating using growth
        self.RemoveShips(used) # for the next calculation
        
        growth = self.GrowthRate() + 1e-300
        
        turnswaitInit = needmore / growth
        closestFleet = min(self.GetIncomingFleetTurns() + [(sys.maxint, 0, 0)], key=lambda p: p[0])
        
        if closestFleet >= turnswaitInit:
            self._turnsWait[dpid] = turnswaitInit
            self.AddShips(used) # for the next calculation
            return self._turnsWait[dpid]
        
        for turn in xrange(closestFleet, maxturns+1):
            sps, spowner = self.CombineIncomingFleets(turnlimit=turn)
            if spowner == 1 and sps >= needed:
                turnswait = turn
                break
        
        self.AddShips(used) # return ships back
        
        enemiesCloserToDP = filter(lambda ep: ep.DistanceTo(dp) <= distance, eplanets)
        enemyGrowthTotal = sum(map(lambda p: p.GrowthRate(), enemiesCloserToDP))
        
        debug("getTurnsWait:", len(enemiesCloserToDP), enemyGrowthTotal) 

        if self.GrowthRate() > enemyGrowthTotal:
            turnswait += needmore / (growth - enemyGrowthTotal)
        else:
            turnswait = 1e300
        
        self._turnsWait[dpid] = turnswait
        return turnswait

    def IssueOrder(self, dp, strength):
        debug("DISPATCH ORDER:", self, ">", dp, "^", strength, "of", self.NumShipsDispatch())
        if strength < 0 or strength > self.NumShipsDispatch() or strength > self.NumShips():
            raise Exception("Invalid dispatch order!")
        self._pw.IssueOrder(self.ID(), dp.ID(), strength)
        distance = self.DistanceTo(dp)
        newfleet = Fleet(self.Owner(), strength, self.ID(), dp.ID(), distance, distance)
        dp.IncomingFleets().append(newfleet)
        self._pw.Fleets().append(newfleet)
        if self.Owner() == 1:
            self._pw.MyFleets().append(newfleet)
        else:
            self._pw.EnemyFleets().append(newfleet)
        self.RemoveShips(strength)
        dp._incomingfleetscombined = None

    def Rating(self):
        if getattr(self, '_rating', None) != None:
            return self._rating
        
        edist = self.DistanceBlob(2) #+ 1e-300
        mdist = self.DistanceBlob(1) #+ 1e-300
        
        mindist = self.ClosestFriendDistance()
        pds, powner = self.CombineIncomingFleets(turnlimit=mindist)
        self._rating = -mdist + self.GrowthRate() * (edist - mdist) 
        if powner == 2:
            self._rating -= float(pds + 1) / (self.GrowthRate() + 1e-300)
        elif powner == 0:
            self._rating -= float(pds + 1) / (self.GrowthRate() + 1e-300)
        
        return self._rating

    def RatingDefence(self):
        if getattr(self, '_ratingDefence', None) != None:
            return self._ratingDefence
        eplanets = filter(lambda p: p.ID() != self.ID(), self._pw.EnemyPlanets())
        mplanets = filter(lambda p: p.ID() != self.ID(), self._pw.MyPlanets())
        edist = float(self.DistanceBlob(eplanets)) if len(eplanets) > 0 else 0.0
        mdist = float(self.DistanceBlob(mplanets)) + 1e-128 if len(mplanets) > 0 else 1e-128
        self._ratingDefence = (edist / mdist) * self.GrowthRate()
        return self._ratingDefence

    def DistanceBlob(self, owner):
        if getattr(self, '_distBlob', None) == None:
            self._distBlob = dict()
        
        if owner in self._distBlob:
            return self._distBlob[owner]
        
        totaldist = 0
        planets = filter(lambda p: p.ID() != self.ID(), self._pw.Planets())

        for p in planets:
            distance = self.DistanceTo(p)
            ps, powner = p.CombineIncomingFleets(turnlimit=distance)
            if powner == owner:
                totaldist += distance
        
        self._distBlob[owner] = float(totaldist) / (len(planets) + 1e-300)
        return self._distBlob[owner]

    def DistanceAndGrowthBlob(self, planets):
        id = self.ID()
        planetsnodp = filter(lambda p: p.ID() != id, planets)
        if len(planetsnodp) <= 0:
            return sys.maxint
        
        return sum(map(lambda p: float(p.GrowthRate()) / (planet.DistanceTo(p) + 1e-300), 
            planetsnodp)) / float(len(planetsnodp))

class PlanetWars:
    def __init__(self):
        self._planets = []
        self._fleets = []
        self._distances = dict()

    def Update(self, gameState):
        self._my_planets = None
        self._enemy_planets = None
        self._neutral_planets = None
        self._notneutral_planets = None
        self._notmy_planets = None
        
        self._my_fleets = None
        self._enemy_fleets = None
        self.ParseGameState(gameState)
        
    def NumPlanets(self):
        return len(self._planets)

    def GetPlanet(self, planet_id):
        return self._planets[planet_id]

    def NumFleets(self):
        return len(self._fleets)

    def GetFleet(self, fleet_id):
        return self._fleets[fleet_id]

    def Planets(self, owner=None):
        if owner == 0:
            return self.NeutralPlanets()
        if owner == 1:
            return self.MyPlanets()
        if owner == 2:
            return self.EnemyPlanets()
        #debug(self._planets, self)
        return self._planets
    
    def MyPlanets(self):
        if not getattr(self, '_my_planets', None):
            self._my_planets = []
            for p in self._planets:
                if p.Owner() != 1:
                    continue
                self._my_planets.append(p)
        return self._my_planets

    def NotMyPlanets(self):
        if not getattr(self, '_notmy_planets', None):
            self._notmy_planets = []
            for p in self._planets:
                if p.Owner() == 1:
                    continue
                self._notmy_planets.append(p)
        return self._notmy_planets
    
    def NeutralPlanets(self):
        if not getattr(self, '_neutral_planets', None):
            self._neutral_planets = []
            for p in self._planets:
                if p.Owner() != 0:
                    continue
                self._neutral_planets.append(p)
        return self._neutral_planets
        
    def NotNeutralPlanets(self):
        if not getattr(self, '_notneutral_planets', None):
            self._notneutral_planets = []
            for p in self._planets:
                if p.Owner() == 0:
                    continue
                self._notneutral_planets.append(p)
        return self._notneutral_planets
    
    def EnemyPlanets(self):
        if not getattr(self, '_enemy_planets', None):
            self._enemy_planets = []
            for p in self._planets:
                if p.Owner() <= 1:
                    continue
                self._enemy_planets.append(p)
        return self._enemy_planets
        
    def NotEnemyPlanets(self):
        if not getattr(self, '_notenemy_planets', None):
            self._notenemy_planets = []
            for p in self._planets:
                if p.Owner() <= 1:
                    continue
                self._notenemy_planets.append(p)
        return self._notenemy_planets
        
    def Fleets(self):
        return self._fleets

    def MyFleets(self):
        if not getattr(self, '_my_fleets', None):
            self._my_fleets = []
            for f in self._fleets:
                if f.Owner() != 1:
                    continue
                self._my_fleets.append(f)
        return self._my_fleets

    def EnemyFleets(self):
        if not getattr(self, '_enemy_fleets', None):
            self._enemy_fleets = []
            for f in self._fleets:
                if f.Owner() <= 1:
                    continue
                self._enemy_fleets.append(f)
        return self._enemy_fleets

    def MyProduction(self):
        return sum(map(lambda p: p.GrowthRate(), self.MyPlanets()))

    def EnemyProduction(self):
        return sum(map(lambda p: p.GrowthRate(), self.EnemyPlanets()))

    def ToString(self):
        s = ''
        for p in self._planets:
            s += "P %f %f %d %d %d\n" % \
             (p.X(), p.Y(), p.Owner(), p.NumShips(), p.GrowthRate())
        for f in self._fleets:
            s += "F %d %d %d %d %d %d\n" % \
             (f.Owner(), f.NumShips(), f.Source(), f.Destination(), \
                f.TotalTripLength(), f.TurnsRemaining())
        return s

    def Distance(self, sp, dp):
        spid = sp.ID()
        dpid = dp.ID()
        
        if spid == dpid:
            return 0
        
        firstId = min(spid, dpid)
        secondId = max(spid, dpid)
        
        if firstId not in self._distances:
            self._distances[firstId] = dict()
            
        if secondId not in self._distances[firstId]:
            dx = sp.X() - dp.X()
            dy = sp.Y() - dp.Y()
            dist = sqrt(dx * dx + dy * dy)
            dist = int(ceil(dist)) if modf(dist)[0] >= 0.5 else int(floor(dist))
            self._distances[firstId][secondId] = dist
        return self._distances[firstId][secondId]
        
    def GetLocalGroup(self, sp, threatDist):
        if getattr(self, '_localGroups', None) == None:
            self._localGroups = dict()
        spid = sp.ID()
        if spid not in self._localGroups:
            self._localGroups[spid] = dict()
        if threatDist not in self._localGroups[spid]:
            self._localGroups[spid][threatDist] = filter(lambda p: 
                sp.DistanceTo(p) < threatDist and p.ID() != spid, self.Planets())
        return self._localGroups[spid][threatDist]
        
    def IssueOrder(self, source, destination, num_ships):
        stdout.write("%s %s %d\n" % (source, destination, num_ships))
        stdout.flush()

    def IsAlive(self, player_id):
        for p in self._planets:
            if p.Owner() == player_id:
                return True
        for f in self._fleets:
            if f.Owner() == player_id:
                return True
        return False

    def ParseGameState(self, s):
        self._planets = []
        self._fleets = []
        lines = s.split("\n")
        planet_id = 0
        for line in lines:
            line = line.split("#")[0] # remove comments
            tokens = line.split(" ")
            if len(tokens) == 1:
                continue
            if tokens[0] == "P":
                if len(tokens) != 6:
                    return 0
                p = Planet(self, 
                             planet_id, # The ID of this planet
                             int(tokens[3]), # Owner
                             int(tokens[4]), # Num ships
                             int(tokens[5]), # Growth rate
                             float(tokens[1]), # X
                             float(tokens[2])) # Y
                planet_id += 1
                self._planets.append(p)
            elif tokens[0] == "F":
                if len(tokens) != 7:
                    return 0
                f = Fleet(int(tokens[1]), # Owner
                            int(tokens[2]), # Num ships
                            int(tokens[3]), # Source
                            int(tokens[4]), # Destination
                            int(tokens[5]), # Total trip length
                            int(tokens[6])) # Turns remaining
                self._fleets.append(f)
            else:
                return 0
        return 1

    def FinishTurn(self):
        stdout.write("go\n")
        stdout.flush()
