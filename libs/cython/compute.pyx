import numpy as np
cimport numpy as np
cimport cython
from libc.math cimport fabs
from libc.math cimport isnan

ctypedef np.float64_t DTYPE_t

@cython.boundscheck(False)
@cython.cdivision
@cython.wraparound(False)
cpdef compute_stats(DTYPE_t[:,:] ms, DTYPE_t[:,:] b, DTYPE_t[:,:] st, DTYPE_t[:,:] fs5p, Py_ssize_t time_lapse):
    
    # ms
    cdef Py_ssize_t idx_open = 0
    cdef Py_ssize_t idx_now = 2
    cdef Py_ssize_t idx_high = 3
    cdef Py_ssize_t idx_low = 4
    cdef Py_ssize_t idx_close = 1
    cdef Py_ssize_t idx_turnover = 5
    cdef Py_ssize_t idx_volume = 6
    
    # statistic
    cdef Py_ssize_t idx_zf = 0
    cdef Py_ssize_t idx_jj = 1
    cdef Py_ssize_t idx_lb = 2
    cdef Py_ssize_t idx_zs = 3
    cdef Py_ssize_t idx_tb = 4
    cdef Py_ssize_t idx_sum5 = 5
    cdef Py_ssize_t idx_sum10 = 6
    cdef Py_ssize_t idx_sum20 = 7
    cdef Py_ssize_t idx_sum30 = 8
    cdef Py_ssize_t idx_sum60 = 9
    
    cdef Py_ssize_t rows = ms.shape[0]
    cdef Py_ssize_t cols = ms.shape[1]
        
    for i in range(rows):
        
        # if ms[i,idx_open]:
        #     st[i,idx_zf] = 100*(ms[i,idx_now]/ms[i,idx_close]-1)
        if ms[i,idx_now]:
            st[i,idx_zf] = 100*(ms[i,idx_now]/ms[i,idx_close]-1)
        else:
            st[i,idx_zf] = np.nan

        if ms[i,idx_turnover]:
            st[i,idx_jj] = ms[i,idx_volume]/ms[i,idx_turnover]
            st[i,idx_zs] = 100*(ms[i,idx_now]/fs5p[i, idx_now]-1)
            if fabs(ms[i,idx_high] - b[i,0]) < 0.001:
                st[i,idx_tb] = 0.5
                if fabs(ms[i,idx_high] - ms[i,idx_now]) < 0.001:
                    st[i,idx_tb] = 1
            elif fabs(ms[i,idx_low] - b[i,1]) < 0.001:
                st[i,idx_tb] = -0.5
                if fabs(ms[i,idx_low] - ms[i,idx_now]) < 0.001:
                    st[i,idx_tb] = -1
            
            st[i,idx_sum5] = (b[i, 4]+ms[i,idx_now])/5
            st[i,idx_sum10] = (b[i, 5]+ms[i,idx_now])/10
            st[i,idx_sum20] = (b[i, 6]+ms[i,idx_now])/20
            st[i,idx_sum30] = (b[i, 7]+ms[i,idx_now])/30
            st[i,idx_sum60] = (b[i, 8]+ms[i,idx_now])/60
                

        if b[i,2] and ms[i,idx_turnover]:
            st[i,idx_lb] = ms[i,idx_turnover]/time_lapse/b[i,2]
            

