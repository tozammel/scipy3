"""
  Matrix Market I/O in Python.

Author:
  Pearu Peterson <pearu@cens.ioc.ee>
References:
  http://math.nist.gov/MatrixMarket/reports/MMformat.ps
"""



from types import ListType, TupleType
from scipy_base import asarray, ArrayType, real,imag,conj,zeros

__all__ = ['mminfo','mmread','mmwrite']

def mminfo(source):
    """ Queries the contents of the Matrix Market file 'filename' to
    extract size and storage information.

    Inputs:

      source     - Matrix Market filename (extension .mtx) or open file object

    Outputs:

      rows,cols  - number of matrix rows and columns
      entries    - number of non-zero entries of a sparse matrix
                   or rows*cols for a dense matrix
      rep        - 'coordinate' | 'array'
      field      - 'real' | 'complex' | 'pattern' | 'integer'
      symm       - 'general' | 'symmetric' | 'skew-symmetric' | 'hermitian'
    """
    close_it = 0
    if type(source) is type(''):
        if source[-4:] != '.mtx':
            source = source + '.mtx'
        source = open(source,'r')
        close_it = 1
    line = source.readline().split()
    if not line[0].startswith('%%MatrixMarket'):
        raise ValueError,'source is not in Matrix Market format'

    assert len(line)==5,`line`

    assert line[1].strip().lower()=='matrix',`line`

    rep = line[2].strip().lower()
    if rep=='dense': rep='array'
    elif rep=='sparse': rep='coordinate'

    field = line[3].strip().lower()

    symm = line[4].strip().lower()

    while line:
        line = source.readline()
        if line.startswith('%'):
            continue
        line = line.split()
        if rep=='array':
            assert len(line)==2,`line`
            rows,cols = map(eval,line)
            entries = rows*cols
        else:
            assert len(line)==3,`line`
            rows,cols,entries = map(eval,line)
        break

    if close_it:
        source.close()
    return (rows,cols,entries,rep,field,symm)

def mmread(source):
    """ Reads the contents of the Matrix Market file 'filename' into the matrix 'A'.

    Inputs:

      source    - Matrix Market filename (extension .mtx) or open file object.

    Outputs:

      a         - sparse or full matrix
    """
    close_it = 0
    if type(source) is type(''):
        if source[-4:] != '.mtx':
            source = source + '.mtx'
        source = open(source,'r')
        close_it = 1

    rows,cols,entries,rep,field,symm = mminfo(source)

    if rep == 'array':
        if field=='integer':
            a = zeros((rows,cols),typecode='i')
        elif field=='real':
            a = zeros((rows,cols),typecode='d')
        elif field=='complex':
            a = zeros((rows,cols),typecode='D')
        else:
            raise ValueError,`field`
        line = 1
        i,j = 0,0
        while line:
            line = source.readline()
            if not line or line.startswith('%'):
                continue
            if field=='complex':
                aij = complex(*map(eval,line.strip().split()))
            else:
                aij = eval(line.strip())
            a[i,j] = aij
            if i!=j:
                if symm=='symmetric':
                    a[j,i] = aij
                elif symm=='skew-symmetric':
                    a[j,i] = -aij
                elif symm=='hermitian':
                    a[j,i] = conj(aij)
            if i<rows-1:
                i = i + 1
            else:
                j = j + 1
                if symm=='general':
                    i = 0
                else:
                    i = j
    else:
        raise NotImplementedError,`rep`

    if close_it:
        source.close()
    return [a,rows,cols,entries]

def mmwrite(target,a,comment='',field=None,precision=None):
    """ Writes the sparse or dense matrix A to a Matrix Market formatted file.

    Inputs:

      target    - Matrix Market filename (extension .mtx) or open file object
      a         - sparse or full matrix
      comment   - comments to be prepended to the Matrix Market file
      field     - 'real' | 'complex' | 'pattern' | 'integer'
      precision - Number of digits to display for real or complex values.
    """
    close_it = 0
    if type(target) is type(''):
        if target[-4:] != '.mtx':
            target = target + '.mtx'
        target = open(target,'w')
        close_it = 1

    if type(a) in [ListType,ArrayType,TupleType] or hasattr(a,'__array__'):
        rep = 'array'
        a = asarray(a)
        if len(a.shape) != 2:
            raise ValueError, 'expected matrix'
        rows,cols = a.shape
        entires = rows*cols        
        typecode = a.typecode()
        if field is not None:
            if field=='integer':
                a = a.astype('i')
            elif field=='real':
                if typecode not in 'fd':
                    a = a.astype('d')
            elif field=='complex':
                if typecode not in 'FD':
                    a = a.astype('D')
            elif field=='pattern':
                pass
            else:
                raise ValueError,'unknown field '+field
        typecode = a.typecode()
    else:
        rep = 'coordinate'
        from scipy.sparse import spmatrix
        if not isinstance(a,spmatrix):
            raise ValueError,'unknown matrix type ' + `type(a)`
        rows,cols = a.rowcol()
        entries = len(a)
        typecode = a.typecode()
        # XXX: transform a to coo_matrix

    if precision is None:
        if typecode in 'fF':
            precision = 8
        else:
            precision = 16
    if field is None:
        if typecode in 'li':
            field = 'integer'
        elif typecode in 'df':
            field = 'real'
        elif typecode in 'DF':
            field = 'complex'
        else:
            raise TypeError,'unexpected typecode '+typecode

    # a,rep,precision,field,rows,cols,entries,symm

    if rep == 'array':
        symm = _get_symmetry(a)
    else:
        raise NotImplementedError,`rep`

    target.write('%%%%MatrixMarket matrix %s %s %s\n' % (rep,field,symm))

    for line in comment.split('\n'):
        target.write('%%%s\n' % (line))

    target.write('%i %i\n' % (rows,cols))

    if rep == 'array':
        if field in ['real','integer']:
            if field=='real':
                format = '%%.%ie\n' % precision
            else:
                format = '%i\n'
            if symm=='general':
                for j in range(cols):
                    for i in range(rows):
                        target.write(format % a[i,j])
            else:
                for j in range(cols):
                    for i in range(j,rows):
                        target.write(format % a[i,j])
        elif field=='complex':
            format = '%%.%ie %%.%ie\n' % (precision,precision)
            if symm=='general':
                for j in range(cols):
                    for i in range(rows):
                        aij = a[i,j]
                        target.write(format % (real(aij),imag(aij)))
            else:
                for j in range(cols):
                    for i in range(j,rows):
                        aij = a[i,j]
                        target.write(format % (real(aij),imag(aij)))
        elif field=='pattern':
            raise ValueError,'Pattern type inconsisted with dense matrix'
        else:
            raise TypeError,'Unknown matrix type'
    else:
        raise NotImplementedError,`rep`

    if close_it:
        target.close()
    else:
        target.flush()
    return

def _get_symmetry(a):
    m,n = a.shape
    if m!=n:
        return 'general'
    issymm = 1
    isskew = 1
    isherm = a.typecode() in 'FD'
    for j in range(n):
        for i in range(j+1,n):
            aij,aji = a[i][j],a[j][i]
            if issymm and aij != aji:
                issymm = 0
            if isskew and aij != -aji:
                isskew = 0
            if isherm and aij != conj(aji):
                isherm = 0
            if not (issymm or isskew or isherm):
                break
    if issymm: return 'symmetric'
    if isskew: return 'skew-symmetric'
    if isherm: return 'hermitian'
    return 'general'
