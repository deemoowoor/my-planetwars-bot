#!/usr/bin/env python
#

"""
The DoTurn function is where your code goes. The PlanetWars object contains
the state of the game, including information about all planets and fleets
that currently exist. Inside this function, you issue orders using the
pw.IssueOrder() function. For example, to send 10 ships from planet 3 to
planet 8, you would say pw.IssueOrder(3, 8, 10).

 There is already a basic strategy in place here. You can use it as a
starting point, or you can throw it out entirely and replace it with your
own. Check out the tutorials and articles on the contest website at
http://www.ai-contest.com/resources.
"""

from PlanetWars import PlanetWars
import sys

def debug(*args):
    sys.stderr.write(' '.join([str(a) for a in args]) + '\n')
    pass
    
def DoTurn(pw):
    # first, determine, if any of the enemy fleets are going to get any of new planets and try to
    # use that to our advantage, timing the re-capture so, that enemy doesn't only loses
    attackEnemy(pw)
 # recaptureEnemy(pw)
 # saveOwn(pw)

def attackEnemy(pw):
    # Find my strongest planet.
    source = -1
    source_score = -999999.0
    source, source_score = findSourcePlanet(pw)
    psrc = pw.GetPlanet(source)
    
    # Get all my fleets
    fleets = pw.MyFleets()

    # Find the best destination: best has biggest growth and least ships and is also located closest
    
    enemy_planets = sanitizePlanets(fleets, pw.EnemyPlanets())
    dest_e, dest_e_score = findBestDestination(enemy_planets, lambda p: (p.GrowthRate() / (pw.Distance(source, p.PlanetID()) + p.NumShips())))
    
    dest = dest_e
    
    #debug("source, dest", source, dest)
    # Send the ships from my strongest planet to the chosen destination
    # planet that I do not own.
    if source >= 0 and dest >= 0:
        pdest = pw.GetPlanet(dest)
        if pdest.NumShips() > psrc.NumShips() / 2:
            num_ships = psrc.NumShips() / 2 - psrc.GrowthRate() * 2;
        else:
            num_ships = psrc.NumShips();
            
        if num_ships <= 0:
            return
        pw.IssueOrder(source, dest, num_ships)
        psrc._num_ships -= num_ships

    
def sanitizePlanets(fleets, planets):
    rplanets = []
    fleetdest = []#f.DestinationPlanet() for f in fleets]

    for p in planets:
        if p.PlanetID() not in fleetdest and p.GrowthRate() > 0:
            rplanets.append(p)
    return rplanets

def regroupOwn(pw):
    # find the weakest and most remote of own planets 
    my_planets = pw.MyPlanets()
    e_planets = pw.NotMyPlanets()
    i = 0
    strongest = []
    weakest = []
    
    most_desired_enemies = []
    
    my_planets.sort(lambda x, y: x.GrowthRate() < y.GrowthRate())
    
    for p in my_planets:
        ++i
        if i < 3:
            strongest.append(p)
        else:
            weakest.append(p)
    
    for s in strongest:
        for w in weakest:
            num_ships = max(w.GrowthRate(), w.NumShips() / 2)
            #print "#regrouping on strongest planet!"
            pw.IssueOrder(w.PlanetID(), s.PlanetID(), num_ships)
            w._num_ships -= num_ships
            
def recaptureEnemy(pw):
    efleets = pw.EnemyFleets()
    mfleets = pw.MyFleets()
    mplanets = pw.MyPlanets()
    
    for ef in efleets:
        dp = pw.GetPlanet(ef.DestinationPlanet())
        if dp.Owner() != ef.Owner():
            for mp in mplanets:
                distance = pw.Distance(mp.PlanetID(), dp.PlanetID())
                eships_remaining = (ef.NumShips() - dp.NumShips())
                
                if ef.TurnsRemaining() < distance and eships_remaining > 0 and \
                     eships_remaining < (4 * mp.NumShips() / 5.0 + 1) and \
                     -eships_remaining < (4 * mp.NumShips() / 5.0 + 1):
                    num_ships = min(max(eships_remaining, -eships_remaining) + 1, 4.0*mp.NumShips()/5.0 + 1)
                    #print "#recapturing enemy planet!", mp.PlanetID(), dp.PlanetID(), num_ships, mp.NumShips()
                    pw.IssueOrder(mp.PlanetID(), dp.PlanetID(), num_ships)
                    mp._num_ships -= num_ships

def saveOwn(pw):
    pass

def findBestDestination(planetlist, score_lambda):
    dest = -1
    dest_score = -1.0
    for p in planetlist:
        score = score_lambda(p)
        #debug("#planet score:", p.PlanetID(), p.GrowthRate(), score)
        if score > dest_score:
            dest_score = score
            dest = p.PlanetID()
    return (dest, dest_score)

def findSourcePlanet(pw):
    my_planets = pw.MyPlanets()
    source = -1
    source_score = -999999.0
    
    for p in my_planets:
        score = float(p.NumShips())
        if score > source_score:
            source_score = score
            source = p.PlanetID()
            source_num_ships = p.NumShips()
            
    return (source, source_score)
    

def main():
    map_data = ''
    while(True):
        current_line = raw_input()
        if len(current_line) >= 2 and current_line.startswith("go"):
            pw = PlanetWars(map_data)
            DoTurn(pw)
            pw.FinishTurn()
            map_data = ''
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
