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
        return "<F(%d) #%d %s -> %s ETA %d>" % (self._owner, self._num_ships, self._source_planet, self._destination_planet, self._turns_remaining)
        

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
        
    def ID(self):
        return self._planet_id

    def Owner(self, new_owner=None):
        if new_owner == None:
            return self._owner
        self._owner = new_owner

    def NumShipsDispatch(self):
        return max(self._num_ships - self._reserve, 0)
        
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
        dx = self._x - destination.X()
        dy = self._y - destination.Y()
        dist = sqrt(dx * dx + dy * dy)
        # TODO: is this distance calc valid?
        if modf(dist)[1] >= 0.5:
            return int(ceil(dist))
        else:
            return int(floor(dist))
    
    def ClosestEnemy(self, exclude=[]):
        if not getattr(self, '_eplanets', None):
            self._eplanets = self._pw.EnemyPlanets()
        if len(self._eplanets) == 0:
                self._closest_enemy = self
        if not getattr(self, '_closest_enemy', None):
            self._closest_enemy = min(self._eplanets, key=lambda p: \
                                      self.DistanceTo(p) if p.ID() != self.ID() and p not in exclude else sys.maxint)
        return self._closest_enemy
        
    def ClosestFriendly(self, exclude=[]):
        if not getattr(self, '_mplanets', None):
            self._mplanets = self._pw.MyPlanets()

        if len(self._mplanets) == 0:
            self._closest_friend = self
            
        if not getattr(self, '_closest_friend', None):
            self._closest_friend = min(self._mplanets, key=lambda p: \
                                       self.DistanceTo(p) if p.ID() != self.ID() and p not in exclude else sys.maxint)
        return self._closest_friend
    
    def IncomingFleets(self):
        if not getattr(self, '_incomingfleets', None):
            self._incomingfleets = filter(lambda f: f.Destination() == self.ID(), self._pw.Fleets())
            self._incomingfleets.sort(cmp, key=lambda f: f.TurnsRemaining())
        return self._incomingfleets
    
    
    def CombineIncomingFleets(self, ff=[], turnlimit=sys.maxint, haveDebug=False):
        """ Estimate planet defensive strength, i.e. how much it can hold up by itself """
        if not ff and getattr(self, '_incomingfleetscombined', None):
            if turnlimit not in self._incomingfleetscombined:
                closest = max(filter(lambda t: t < turnlimit, self._incomingfleetscombined.keys()))
                closeststr, owner = self._incomingfleetscombined[closest]
                gr = self._growth_rate if owner != 0 else 0
                strength = closeststr + gr * (turnlimit - closest)
                self._incomingfleetscombined[turnlimit] = (strength, owner)
            return self._incomingfleetscombined[turnlimit]
            
        powner = self._owner
        gr = self._growth_rate if powner != 0 else 0
        pstrength = 0
        pstrength += self._num_ships
        
        if not ff and not getattr(self, '_incomingfleetscombined', None):
            self._incomingfleetscombined = { 0 : (pstrength, powner) }
        
        fleets = self.IncomingFleets() + ff
        
        if haveDebug:
            debug(fleets)
        
        if not ff:
            self._incomingfleetscombined[sys.maxint] = (pstrength, powner)
        
        turnList = mapFleetsToTurns(fleets)
        
        curturn = turnList[0][0] if len(turnList) > 0 else 0
        
        if haveDebug:
            debug("Combining fleets for:", self.ID(), '@', turnlimit, turnList)
            
        for turn,mforce,eforce in turnList:
            turns_interval = (turn - curturn)
            gr = self._growth_rate if powner != 0 else 0
            
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
            #debug("   >", self.ID(), '@', turn, '<>', turns_interval, 'owner:', powner, '>< p', pstrength, 'm', mforce, 'e', eforce, 'gr', turns_interval * gr)
            
        if ff:
            return (pstrength, powner)
        
        self._incomingfleetscombined[curturn] = (pstrength, powner)
        
        if turnlimit < sys.maxint:
            for t in xrange(curturn, turnlimit+1):
                if haveDebug:
                    debug("adding: @", t, pstrength + (t - curturn) * gr, gr, powner)
                self._incomingfleetscombined[t] = (pstrength + (t-curturn) * gr, powner)
        
        if turnlimit == sys.maxint or sys.maxint not in self._incomingfleetscombined:
            self._incomingfleetscombined[sys.maxint] = (pstrength, powner)
            
        if haveDebug:
            debug("   final for:", self.ID(), pstrength, powner, "@", turnlimit, ":", self._incomingfleetscombined);
            
        if turnlimit not in self._incomingfleetscombined:
            closest = max(filter(lambda t: t < turnlimit, self._incomingfleetscombined.keys()))
            closeststr, owner = self._incomingfleetscombined[closest]
            gr = self._growth_rate if owner != 0 else 0
            strength = closeststr + gr * (turnlimit - closest)
            self._incomingfleetscombined[turnlimit] = (strength, owner)
        
        return self._incomingfleetscombined[turnlimit]
    
    def SetRescued(self, rescued):
        self._rescued = rescued
    
    def IsRescued(self):
        if not getattr(self, '_rescued', None):
            self._rescued = False
        return self._rescued
    
    def __str__(self):
        return "%d" % (self._planet_id)
    
    def __rep__(self):
        return "%d(%d) ^%d" % (self._planet_id, self._owner, self._num_ships)
    
    def __unicode__(self):
        return u"%d" % (self._planet_id)

class PlanetWars:
    def __init__(self, gameState):
        self._planets = []
        self._fleets = []
        self.ParseGameState(gameState)

    def NumPlanets(self):
        return len(self._planets)

    def GetPlanet(self, planet_id):
        return self._planets[planet_id]

    def NumFleets(self):
        return len(self._fleets)

    def GetFleet(self, fleet_id):
        return self._fleets[fleet_id]

    def Planets(self):
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

    def Distance(self, source_planet, destination_planet):
        source = self._planets[source_planet]
        destination = self._planets[destination_planet]
        dx = source.X() - destination.X()
        dy = source.Y() - destination.Y()
        dist = sqrt(dx * dx + dy * dy)
        # TODO: is this distance calc valid?
        if modf(dist)[1] >= 0.5:
            return int(ceil(dist))
        else:
            return int(floor(dist))

    def IssueOrder(self, source_planet, destination_planet, num_ships):
        stdout.write("%s %s %d\n" % \
         (source_planet, destination_planet, num_ships))
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
                p = Planet(self, planet_id, # The ID of this planet
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
