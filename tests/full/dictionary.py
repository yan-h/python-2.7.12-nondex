import unittest
from string import ascii_lowercase

'''
Since these tests rely on randomness, they have a non-zero chance
of failing even if the code is working as intended. However, their
bounds have been chosen to make failure extremely unlikely.
'''

class TestDict(unittest.TestCase):

    def perm_counts(self, d, iterations, iterFuncName):
        '''
        Helper function.
        Given a dictionary, iterates through it a given number of times and returns a dictionary
        mapping each iteration order (represented as a tuple) to its number of occurrences.
        Used to test whether all permutations of iterations are roughly equally likely.

        d - the input dictionary
        iterations - number of iterations
        iterFuncName - the name of the function to call on the dictionary to return an iterator.
                       For dictionaries, can be "iterkeys", "itervalues" or "iteritems"
        '''
        result = {}
        iterFunc = getattr(d, iterFuncName)
        for i in range(iterations):
            perm = []
            for k in iterFunc():
                perm.append(k)
            if tuple(perm) in result:
                result[tuple(perm)] += 1
            else:
                result[tuple(perm)] = 1
        return result

    def test_random(self):
        d = {}

        iterFuncNames = ["iterkeys", "itervalues", "iteritems"];

        for funcName in iterFuncNames:
            d = {}
            counts = self.perm_counts(d, 1000, funcName)
            self.assertTrue(len(counts) == 1)
            for k, v in counts.iteritems():
                self.assertTrue(len(set(k)) == len(k))
                self.assertTrue(v == 1000)

            d = {'a':1}
            counts = self.perm_counts(d, 1000, funcName)
            self.assertTrue(len(counts) == 1)
            for k, v in counts.iteritems():
                self.assertTrue(len(set(k)) == len(k))
                self.assertTrue(v == 1000)

            d = {'a':1, 'b':2}
            counts = self.perm_counts(d, 2000, funcName)
            self.assertTrue(len(counts) == 2)
            for k, v in counts.iteritems():
                self.assertTrue(len(set(k)) == len(k))
                self.assertTrue(v > 800)
                self.assertTrue(v < 1200)

            d = {'a':1, 'b':2, 'c':3}
            counts = self.perm_counts(d, 6000, funcName)
            self.assertTrue(len(counts) == 6)
            for k, v in counts.iteritems():
                self.assertTrue(len(set(k)) == len(k))
                self.assertTrue(v > 800)
                self.assertTrue(v < 1200)

            d = {}
            i = 0
            for c in ascii_lowercase:
                d[c] = i
                i += 1
            counts = self.perm_counts(d, 2000, funcName)
            self.assertTrue(len(counts) > 1998)
            for k, v in counts.iteritems():
                self.assertTrue(len(set(k)) == len(k))
                self.assertTrue(v < 3)

if __name__ == '__main__':
    unittest.main()
