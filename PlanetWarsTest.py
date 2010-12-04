#!/usr/bin/env python
import unittest
import math
from PlanetWars import PlanetWars, Planet, Fleet

class PlanetWarsTestCase (unittest.TestCase):
    def testDistancePlanets(self):
        gameState = "\n".join(["P 0.5 0.5 0 0 0", "P 1.0 1.0 0 0 0", "P 1.1 1.1 0 0 0"])
        pw = PlanetWars()
        pw.Update(gameState)
        planets = pw.Planets()
        self.assertEqual(pw.Distance(planets[0], planets[1]), 1)
        self.assertEqual(pw.Distance(planets[1], planets[2]), 0)

    def testDistanceTo(self):
        gameState = "\n".join(["P 0.5 0.5 0 0 0", "P 1.0 1.0 0 0 0", "P 1.1 1.1 0 0 0"])
        pw = PlanetWars()
        pw.Update(gameState)
        planets = pw.Planets()
        self.assertEqual(planets[0].DistanceTo(planets[1]), 1)
        self.assertEqual(planets[1].DistanceTo(planets[2]), 0)

    def testLocalGroup(self):
        gameState = "\n".join(["P 0.5 0.5 0 0 0", "P 1.0 1.0 0 0 0", "P 1.1 1.1 0 0 0", "P 5.35 5.35 0 0 100"])
        pw = PlanetWars()
        pw.Update(gameState)
        planets = pw.Planets()
        lgrp = pw.GetLocalGroup(planets[0], 2)
        self.assertEqual(len(lgrp), 2)
        assert planets[1] in lgrp
        assert planets[2] in lgrp
        assert planets[0] not in lgrp
        assert planets[3] not in lgrp


class PlanetWarsTestSuite (unittest.TestSuite):
    def __init__(self):
        unittest.TestSuite.__init__(self,map(PlanetWarsTestCase,
                                ("testDistancePlanets",)))

if __name__ == '__main__':
    unittest.main()

