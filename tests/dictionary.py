import unittest
from string import ascii_lowercase

'''
Since these tests rely on randomness, they have a non-zero chance
of failing even if the code is working as intended. However, their 
bounds have been chosen to make failure extremely unlikely.
'''

class TestDict(unittest.TestCase):
    
    def permCounts(self, d, iterations):
        result = {}
        for i in range(iterations):
            dstr = ''
            for k in d:
                dstr += k
            if dstr in result:
                result[dstr] += 1
            else:
                result[dstr] = 1
        return result

    def test_keys_small(self):
        d = {}
        counts = self.permCounts(d, 1000)
        self.assertTrue(counts[''] == 1000)
        self.assertTrue(len(counts) == 1)

        d = {'a':1}
        counts = self.permCounts(d, 1000)
        self.assertTrue(counts['a'] == 1000)
        self.assertTrue(len(counts) == 1)

        d = {'a':1, 'b':2}
        counts = self.permCounts(d, 20000)
        self.assertTrue(len(counts) == 2)
        for k, v in counts.iteritems():
            self.assertTrue(len(set(k)) == len(k)) 
            self.assertTrue(v > 8000)
            self.assertTrue(v < 12000)

        d = {'a':1, 'b':2, 'c':3}
        counts = self.permCounts(d, 60000)
        self.assertTrue(len(counts) == 6)
        for k, v in counts.iteritems():
            self.assertTrue(len(set(k)) == len(k)) 
            self.assertTrue(v > 8000)
            self.assertTrue(v < 12000)
    
    def test_keys_large(self):
        d = {}
        i = 0
        for c in ascii_lowercase:
            d[c] = i
            i += 1
        counts = self.permCounts(d, 5000)
        self.assertTrue(len(counts) > 4998)
        for k, v in counts.iteritems():
            self.assertTrue(len(set(k)) == len(k)) 
            self.assertTrue(v < 3)

if __name__ == '__main__':
    unittest.main()
