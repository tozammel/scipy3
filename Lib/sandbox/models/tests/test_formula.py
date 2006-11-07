import unittest, csv, os
import numpy as N
import numpy.random as R
import numpy.linalg as L
import scipy, string
from numpy.testing import *

from scipy.sandbox.models import utils, formula, contrast

class test_term(unittest.TestCase):

    def test_init(self):
        t1 = formula.term("trivial")
        sqr = lambda x: x*x

        t2 = formula.term("not_so_trivial", sqr, "sqr")

        self.assertRaises(ValueError, formula.term, "name", termname=0)

    def test_str(self):
        t = formula.term("name")
        s = str(t)

    def test_add(self):
        t1 = formula.term("t1")
        t2 = formula.term("t2")
        f = t1 + t2
        self.assert_(isinstance(f, formula.formula))
        self.assert_(f.hasterm(t1))
        self.assert_(f.hasterm(t2))

    def test_mul(self):
        t1 = formula.term("t1")
        t2 = formula.term("t2")
        f = t1 * t2
        self.assert_(isinstance(f, formula.formula))

        intercept = formula.term("intercept")
        f = t1 * intercept
        self.assertEqual(str(f), str(formula.formula(t1)))

        f = intercept * t1
        self.assertEqual(str(f), str(formula.formula(t1)))

class test_formula(ScipyTestCase):

    def setUp(self):
        self.X = R.standard_normal((40,10))
        self.namespace = {}
        self.terms = []
        for i in range(10):
            name = '%s' % string.uppercase[i]
            self.namespace[name] = self.X[:,i]
            self.terms.append(formula.term(name))

        self.formula = self.terms[0]
        for i in range(1, 10):
            self.formula += self.terms[i]

    def test_str(self):
        s = str(self.formula)

    def test_call(self):
        x = self.formula(namespace=self.namespace)
        self.assertEquals(N.array(x).shape, (10, 40))

    def test_design(self):
        x = self.formula.design(namespace=self.namespace)
        self.assertEquals(x.shape, (40, 10))

    def test_product(self):
        prod = self.terms[0] * self.terms[2]
        self.formula += prod
        x = self.formula.design(namespace=self.namespace)
        col = self.formula.termcolumns(prod, dict=False)
        assert_almost_equal(N.squeeze(x[:,col]), self.X[:,0] * self.X[:,2])

    def test_contrast1(self):
        term = self.terms[0] + self.terms[2]
        c = contrast.Contrast(term, self.formula)
        c.getmatrix(namespace=self.namespace)
        col1 = self.formula.termcolumns(self.terms[0], dict=False)
        col2 = self.formula.termcolumns(self.terms[1], dict=False)
        test = [[1] + [0]*9, [0]*2 + [1] + [0]*7]
        assert_almost_equal(c.matrix, test)

    def test_contrast2(self):
    
        dummy = formula.term('zero')
        self.namespace['zero'] = N.zeros((40,), N.float64)
        term = dummy + self.terms[2]
        c = contrast.Contrast(term, self.formula)
        c.getmatrix(namespace=self.namespace)
        test = [0]*2 + [1] + [0]*7
        assert_almost_equal(c.matrix, test)

    def test_contrast3(self):
    
        X = self.formula.design(namespace=self.namespace)
        P = N.dot(X, L.pinv(X))
        
        dummy = formula.term('noise')
        resid = N.identity(40) - P
        self.namespace['noise'] = N.transpose(N.dot(resid, R.standard_normal((40,5))))
        term = dummy + self.terms[2]
        c = contrast.Contrast(term, self.formula)
        y = term(namespace=self.namespace)
        c.getmatrix(namespace=self.namespace)
        self.assertEquals(c.matrix.shape, (10,))

    def test_contrast4(self):
    
        f = self.formula + self.terms[5] + self.terms[5] 

        estimable = False

        c = contrast.Contrast(self.terms[5], f)
        c.getmatrix(namespace=self.namespace)
        
        self.assertEquals(estimable, False)

def suite():
    suite = unittest.makeSuite(formulaTest)
    return suite


if __name__ == '__main__':
    unittest.main()
