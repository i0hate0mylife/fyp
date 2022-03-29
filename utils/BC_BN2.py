import numpy as np
import math
from numpy import linalg as LA
from math import comb
from collections import OrderedDict
import torch
import copy

def maxFinder(w_locals, bc_arr, Kc, K,glob):  #w_locals => M, bc_arr => M
    w = []
    for i in range(len(w_locals)):
        temp = []
        for item in w_locals[i].keys():
            temp = (np.concatenate((temp, (w_locals[i][item].cpu().numpy()-glob[item].cpu().numpy())), axis=None))
        w.append(temp)
    l2_arr = LA.norm(np.array(w), axis=1)
    a = np.array(bc_arr)
    h = LA.norm(a, axis=1)

    idxs1 = h.argsort()[::-1][:Kc]
    w_1 = np.array(np.array(w_locals)[idxs1])
    h_1 = np.array(h[idxs1])
    l2_1 = np.array(l2_arr[idxs1])



    idxs2 = l2_1.argsort()[::-1][:K]
    ret_w = np.array(w_1[idxs2])
    ret_h = np.array(h_1[idxs2])
    ret_l2 = np.array(l2_1[idxs2])

    return (ret_w, ret_l2, ret_h)  #ret_w => K, ret_l2 => K, ret_h => K

def cFinder(h, K, M): #h => K
    ret_arr = []
    for i in range(K):
        c = math.log((1 + h[i] * h[i] * (M / K)), 2)
        ret_arr.append(c)
    return ret_arr  #ret_arr => K

def nFinder(l2_arr, C_arr, K, n):  #l2_arr => K, C_arr => K
    ret_arr = []
    lower = 0
    for j in range(K):
        lowerMulti = 1
        for i in range(K-1):
            if (i != j):
                lowerMulti *= C_arr[i]
        lower += lowerMulti * l2_arr[j]

    for q in range(K):
        upper = 1
        for i in range(K):
            if (i != q):
                upper *= C_arr[i]
        ret_arr.append( math.ceil((upper/lower) * n * l2_arr[q]))
    return ret_arr  #ret_arr => K



def qFinder(C_arr, N_arr, new_w_locals, K,glob):
    ret_arr=[]

    for index in range(K):
        #######get variable

        array_x = []
        flat_glob = []
        iwLen = np.array(new_w_locals[index]['layer_input.weight'].cpu().numpy()).shape
        ibLen = np.array(new_w_locals[index]['layer_input.bias'].cpu().numpy()).shape
        hwLen = np.array(new_w_locals[index]['layer_hidden.weight'].cpu().numpy()).shape
        hbLen = np.array(new_w_locals[index]['layer_hidden.bias'].cpu().numpy()).shape
        iw = np.prod(iwLen)
        ib = np.prod(ibLen)
        hw = np.prod(hwLen)
        hb = np.prod(hbLen)
        d = iw + ib + hw + hb
        target = 0

        #####perform binary search
        start = 0
        end = d

        while True:
            midpoint = (end + start) // 2
            check = math.log(comb(d, midpoint), 2) + 33 * midpoint
            if (end - start == 1):
                target = midpoint
                break
            elif check > N_arr[index] * C_arr[index]:
                end = midpoint
            else:
                start = midpoint
            # print(midpoint)



        for item in new_w_locals[index].keys():
            new_w_local_cpu=new_w_locals[index][item].cpu().numpy()
            glob_cpu = glob[item].cpu().numpy()
            k = new_w_local_cpu - glob_cpu
            flat_glob = np.concatenate((flat_glob,glob_cpu),axis=None)
            array_x = np.concatenate((array_x, k), axis=None)

        abs_x = np.array(np.abs(array_x))


        ind_that_set_to_zero = np.argpartition(abs_x, -target)[:-target]

        ind_that_quantize = np.argpartition(abs_x, -target)[-target:]

        array_x[ind_that_set_to_zero] = 0

        max_ele = max(array_x)
        min_ele = min(array_x)

        a=(max_ele-min_ele)/2**32

        array_x_temp = ((np.round((array_x - min_ele) / a)) * a) + min_ele

        array_x_temp[ind_that_set_to_zero] = 0

        if target == 0:
            array_x_temp = flat_glob
        elif target > 0:
            array_x_temp = np.add(flat_glob, array_x_temp)



        ret_arr.append(OrderedDict([
            ('layer_input.weight', torch.FloatTensor((np.reshape(array_x_temp[:iw], iwLen)).tolist())),
            ('layer_input.bias', torch.FloatTensor((np.reshape(array_x_temp[iw:iw + ib], ibLen)).tolist())),
            ('layer_hidden.weight', torch.FloatTensor((np.reshape(array_x_temp[iw + ib:iw + ib + hw], hwLen)).tolist())),
            ('layer_hidden.bias', torch.FloatTensor((np.reshape(array_x_temp[iw + ib + hw:], hbLen)).tolist()))
        ]))



    return ret_arr