#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" 
utilities.py 

This script when imported as a module allows search.py, transform.py and 
assemble.py in the ah package to run smoothly. 

This file contains the following functions:

    * add_annotations - Adds annotations to each pair of repeated structures 
    according to their length and order of occurence. 

    * create_sdm - Creates a self-dissimilarity matrix; this matrix is found 
    by creating audio shingles from feature vectors, and finding cosine 
    distance between shingles. 

    * find_initial_repeats - Finds all diagonals present in thresh_mat, 
    removing each diagonal as it is found.
    
    * reconstruct_full_block - Creates a record of when pairs of repeated
    structures occur, from the first beat in the song to the last beat of the
    song. Pairs of repeated structures are marked with 1's. 
    
    * reformat - Transforms a binary matrix representation of when repeats 
    occur in a song into a list of repeated structures detailing the length
    and occurence of each repeat.      
    
    * stretch_diags - Fill out diagonals in binary self dissimilarity matrix
    from diagonal starts and lengths
    
    * __find_song_pattern - stitches information from thresh_diags matrix into a single
    row, song_pattern, that shows the timesteps containing repeats
"""

import numpy as np
from scipy import signal
import scipy.sparse as sps
import scipy.spatial.distance as spd

def add_annotations(input_mat, song_length):
    """
    Adds annotations to the pairs of repeats in input_mat; Annotations depend 
    on length of repeats and the time that repeats occur in song

    Args
    ----
    input_mat: np.array
        list of pairs of repeats. The first two columns refer to 
        the first repeat of the pair. The third and fourth columns refer
        to the second repeat of the pair. The fifth column refers to the
        repeat lengths. The sixth column contains any previous annotations,
        which will be removed.
        
    song_length: int
        number of audio shingles in the song.
    
    Returns
    -------
    anno_list: array
        list of pairs of repeats with annotations marked. 
    """
    num_rows = input_mat.shape[0]
    
    # Removes any already present annotation markers
    input_mat[:, 5] = 0
    
    # Find where repeats start
    s_one = input_mat[:,0]
    s_two = input_mat[:,2]
    
    # Creates matrix of all repeats
    s_three = np.ones((num_rows,), dtype = int)
    
    up_tri_mat = sps.coo_matrix((s_three, 
                                 (s_one, s_two)), shape = (song_length + 1, song_length + 1)).toarray()
    
    low_tri_mat = up_tri_mat.conj().transpose()
    
    full_mat = up_tri_mat + low_tri_mat
    
    # Stitches info from input_mat into a single row
    song_pattern = __find_song_pattern(full_mat)

    # Restructures song_pattern
    song_pattern = song_pattern[:,:-1]
    song_pattern = np.insert(song_pattern, 0, 0, axis=1)
    
    # Adds annotation markers to pairs of repeats
    for i in song_pattern[0]:
        pinds = np.nonzero(song_pattern == i)
        
        #One if annotation not already marked, 0 if it is
        check_inds = (input_mat[:,5] == 0)
        
        for j in pinds[1]:
            
            # Finds all starting pairs that contain time step j
            # and DO NOT have an annotation
            mark_inds = (s_one == j) + (s_two == j)
            mark_inds = (mark_inds > 0)
            mark_inds = check_inds * mark_inds
            
            # Adds found annotations to the relevant time steps
            input_mat[:,5] = (input_mat[:,5] + i * mark_inds)
            
            # Removes pairs of repeats with annotations from consideration
            check_inds = check_inds ^ mark_inds
     
    temp_inds = np.argsort(input_mat[:,5])
    
    # Creates list of annotations
    anno_list = input_mat[temp_inds,]
    
    return anno_list

def create_sdm(fv_mat, num_fv_per_shingle):
    """
    Creates self-dissimilarity matrix; this matrix is found by creating audio 
    shingles from feature vectors, and finding cosine distance between 
    shingles
    
    Args
    ----
    fv_mat: np.array
        matrix of feature vectors where each column is a timestep and each row
        includes feature information i.e. an array of 144 columns/beats and 12
        rows corresponding to chroma values
        
    num_fv_per_shingle: int
        number of feature vectors per audio shingle
    
    Returns
    -------
    self_dissim_mat: np.array 
        self dissimilarity matrix with paired cosine distances between 
        shingles
    """
    [num_rows, num_columns] = fv_mat.shape
    if num_fv_per_shingle == 1:
        mat_as = fv_mat
    else:
        mat_as = np.zeros(((num_rows * num_fv_per_shingle),
                           (num_columns - num_fv_per_shingle + 1)))
        for i in range(1, num_fv_per_shingle+1):
            # Use feature vectors to create an audio shingle
            # for each time step and represent these shingles
            # as vectors by stacking the relevant feature
            # vectors on top of each other
            mat_as[((i-1)*num_rows+1)-1:(i*num_rows), : ] = fv_mat[:, 
                   i-1:(num_columns- num_fv_per_shingle + i)]

    sdm_row = spd.pdist(mat_as.T, 'cosine')
    self_dissim_mat = spd.squareform(sdm_row)
    return self_dissim_mat
  
def find_initial_repeats(thresh_mat, bandwidth_vec, thresh_bw):
    """
    Identifies all repeated structures in a sequential data stream which are 
    represented as diagonals in thresh_mat and then stores the pairs of
    repeats that correspond to each repeated structure in a list. 
    
    Args
    ----
        thresh_mat: np.array[int]:
            thresholded matrix that we extract diagonals from
        
        bandwidth_vec: np.array[1D,int]:
            vector of lengths of diagonals to be found
        
        thresh_bw int:
            smallest allowed diagonal length
    
    Returns
    -------
        all_lst: np.array[int]:
            list of pairs of repeats that correspond to 
            diagonals in thresh_mat
    """    
    
    bw_len = bandwidth_vec.shape[1]
    
    int_all = []
    sint_all = []
    eint_all = []
    mint_all = []
    
    for bw in bandwidth_vec:
        if bw > thresh_bw:
            # Use convolution mx to find diagonals of length bw
            id_mat = np.identity(bw)
            diagonal_mat = signal.convolve2d(thresh_mat, id_mat, 'valid')
            
            # Mark where diagonals of length bw start
            diag_markers = (diagonal_mat == bw)
            
            if sum(diag_markers) > 0:
                full_bw = bw
                # 1) Search outside the overlapping shingles
                # Search for paired starts
                upper_tri = np.triu(diag_markers, full_bw)
                (start_i, start_j) = upper_tri.nonzero()
                num_nonoverlaps = start_i.shape[0]
                
                # Find the matching ends for the prevously found starts
                match_i = start_i + (full_bw - 1)
                match_j = start_j + (full_bw - 1)
                
                # List pairs of starts with their ends and the widths of the
                # non-overlapping intervals
                int_lst = np.column_stack([start_i, match_i, start_j, match_j,
                                           full_bw*np.ones(num_nonoverlaps,1)])
    
                # Add the new non-overlapping intervals to the full list of
                # non-overlapping intervals
                int_all.append(int_lst)
                
                # 2) Overlaps: Search only the overlaps in shingles
                shin_ovrlaps = np.nonzero((np.tril(np.triu(diag_markers), 
                                                   (full_bw - 1))))
                start_i_shin = np.array(shin_ovrlaps[0]) # row
                start_j_shin = np.array(shin_ovrlaps[1]) # column
                num_ovrlaps = start_i.shape[0]
                
                if(num_ovrlaps == 1 and start_i_shin == start_j_shin):
                    sint_lst = np.column_stack([start_i_shin, 
                                                (start_i_shin + (full_bw - 1)), 
                                                start_j_shin, 
                                                (start_j_shin + (full_bw - 1)),
                                                full_bw])
                    sint_all.append(sint_lst)
                    
                elif num_ovrlaps > 0:
                        # Since you are checking the overlaps you need to 
                        # cut these intervals into pieces: left, right, and 
                        # middle. NOTE: the middle interval may NOT exist.
                        
                        # Create vector of 1's that is the length of the 
                        # number of overlapping intervals. This is used a lot. 
                        ones_no = np.ones(num_ovrlaps,1)
                        
                        # 2a) Left Overlap
                        K = start_j_shin - start_i_shin 
                        # NOTE: matchJ - matchI will also equal this, since the 
                        # intervals that are overlapping are the same length. 
                        # Therefore the "left" non-overlapping section is the 
                        # same length as the "right" non-overlapping section. 
                        # It does NOT follow that the "middle" section is 
                        # equal to either the "left" or "right" piece. It is
                        # possible, but unlikely.
                        
                        sint_lst = np.column_stack([start_i_shin, 
                                                    (start_j_shin - ones_no), 
                                                    start_j_shin, 
                                                    (start_j_shin + K - ones_no), 
                                                    K])
                        i_s = np.argsort(K)
                        sint_lst = sint_lst[i_s,]
                        
                        # Remove pairs that fall below the bandwidth threshold
                        cut_s = np.amin((sint_lst[:,4]).nonzero())
                        sint_lst = sint_lst[cut_s:,]
                        
                        # Add new left overlapping intervals to the full list
                        # of left overlapping intervals
                        sint_all.append(sint_lst)
                        
                        # 2b) Right Overlap
                        end_i_right = start_i_shin + (full_bw - 1)
                        end_j_right = start_j_shin + (full_bw - 1)
                        eint_lst = np.column_stack([(end_i_right + ones_no - K),
                                                    end_i_right,
                                                    (end_i_right + ones_no), 
                                                    end_j_right, K])
                        ie = np.argsort(K)
                        eint_lst = eint_lst[ie,]
                        
                        # Remove pairs that fall below the bandwidth threshold
                        cut_e = np.amin((eint_lst[:,4]).nonzero())
                        eint_lst = eint_lst[cut_e:,]
                        
                        # Add the new right overlapping intervals to the full list
                        # of right overlapping intervals
                        eint_all.append(eint_lst)
                        
                        # 2b) Middle Overlap
                        mnds = (end_i_right - start_j_shin - K + ones_no) > 0
                        start_i_mid = (start_j_shin * mnds)
                        end_i_mid = (end_i_right * (mnds) - K * (mnds))
                        start_j_mid = (start_j_shin * (mnds) + K * (mnds))
                        end_j_mid = (end_i_mid * mnds)
                        km = (end_i_mid * (mnds) - start_j_mid * 
                              (mnds) - K * (mnds) + ones_no * (mnds))
                        
                        if mnds.sum() > 0:
                            mint_lst = np.column_stack([start_i_mid, end_i_mid,
                                                        start_j_mid, end_j_mid,
                                                        km])
                            im = np.argsort(km)
                            mint_lst = mint_lst[im,]
                            
                            # Add the new middle overlapping intervals to 
                            # the full list of middle overlapping intervals
                            mint_all.append(mint_lst)
                            
                        # 4) Remove found diagonals of length bw from consideration
                        sdm = stretch_diags(diag_markers, bw)
                        thresh_mat = thresh_mat - sdm
                        
                if thresh_mat.sum() == 0:
                        break
                            
    # Combine non-overlapping intervals with the left, right, and middle parts
    # of the overlapping intervals
    ovrlap_lst = np.concatenate((sint_all, eint_all, mint_all), axis = 0)
    all_lst = np.concatenate((int_all, ovrlap_lst))
    all_lst = filter(None, all_lst)

    # Sort the list by bandwidth size
    I = np.argsort(all_lst[:,4])
    all_lst = all_lst[I,]                     
    
    return all_lst

def reconstruct_full_block(pattern_mat, pattern_key): 
    """
    Creates a record of when pairs of repeated structures occur, from the 
    first beat in the song to the end. This record is a binary matrix with a 
    block of 1's for each repeat encoded in pattern_mat whose length 
    is encoded in pattern_key
    
    Args
    ----
    pattern_mat: np.array
        binary matrix with 1's where repeats begin 
        and 0's otherwise
     
    pattern_key: np.array
        vector containing the lengths of the repeats 
        encoded in each row of pattern_mat

    Returns
    -------
    pattern_block: np.array
        binary matrix representation for pattern_mat 
        with blocks of 1's equal to the length's 
        prescribed in pattern_key
    """
    #First, find number of beats (columns) in pattern_mat: 
    #Check size of pattern_mat (in cases where there is only 1 pair of
    #repeated structures)
    if (pattern_mat.ndim == 1): 
        #Convert a 1D array into 2D array 
        #From:
        #https://stackoverflow.com/questions/3061761/numpy-array-dimensions
        pattern_mat = pattern_mat[None, : ]
        #Assign number of beats to sn 
        sn = pattern_mat.shape[1]
    else: 
        #Assign number of beats to sn 
        sn = pattern_mat.shape[1]
        
    #Assign number of repeated structures (rows) in pattern_mat to sb 
    sb = pattern_mat.shape[0]
    
    #Pre-allocating a sn by sb array of zeros 
    pattern_block = np.zeros((sb,sn)).astype(int)  
    
    #Check if pattern_key is in vector row 
    if pattern_key.ndim != 1: 
        #Convert pattern_key into a vector row 
        length_vec = np.array([])
        for i in pattern_key:
            length_vec = np.append(length_vec, i).astype(int)
    else: 
        length_vec = pattern_key 
    
    for i in range(sb):
        #Retrieve all of row i of pattern_mat 
        repeated_struct = pattern_mat[i,:]
    
        #Retrieve the length of the repeats encoded in row i of pattern_mat 
        length = length_vec[i]
    
        #Pre-allocate a section of size length x sn for pattern_block
        sub_section = np.zeros((length, sn))
    
        #Replace first row in block_zeros with repeated_structure 
        sub_section[0,:] = repeated_struct
        
        #Creates pattern_block: Sums up each column after sliding repeated 
        #sastructure i to the right bw - 1 times 
        for b in range(2, length + 1): 
    
            #Retrieve repeated structure i up to its (1 - b) position 
            sub_struct_a = repeated_struct[0:(1 - b)]
    
            #Row vector with number of entries not included in sub_struct_a  
            sub_struct_b = np.zeros((1,( b  - 1)))
    
            #Append sub_struct_b in front of sub_struct_a 
            new_struct = np.append(sub_struct_b, sub_struct_a)
            
            #Replace part of sub_section with new_struct 
            sub_section[b - 1,:] = new_struct
    
    #Replaces part of pattern_block with the sums of each column in 
    #sub_section 
    pattern_block[i,:] = np.sum(sub_section, axis = 0)
    
    return pattern_block
    
#line 217: 
#https://stackoverflow.com/questions/2828059/sorting-arrays-in-np-by-column

def reformat(pattern_mat, pattern_key):
    """
    Transforms a binary array with 1's where repeats start and 0's
    otherwise into an a list of repeated stuctures. This list consists of
    information about the repeats including length, when they occur and when
    they end. 
    
    Every row has a pair of repeated structure. The first two columns are 
    the time steps of when the first repeat of a repeated structure start and 
    end. Similarly, the second two columns are the time steps of when the 
    second repeat of a repeated structure start and end. The fourth colum is 
    the length of the repeated structure. 
    
    reformat.py may be helpful when writing example inputs for aligned 
    hiearchies.
    
    Args
    ----
        pattern_mat: np.array 
            binary array with 1's where repeats start and 0's otherwise 
        
        pattern_key: np.array 
            array with the lengths of each repeated structure in pattern_mat
            
    Returns
    -------
        info_mat: np.array 
            array with the time steps of when the pairs of repeated structures 
            start and end organized 

    """

    #Pre-allocate output array with zeros 
    info_mat = np.zeros((pattern_mat.shape[0], 5))
    
    #Retrieve the index values of the repeats in pattern_mat 
    results = np.where(pattern_mat == 1)
    
    #1. Find the starting indices of the repeated structures row by row 
    for r in range(pattern_mat.shape[0]):
        #Find where the repeats start  
        r_inds = (pattern_mat[r] == 1) 
        inds = np.where(r_inds)
        
        #Retrieve the starting indices of the repeats 
        s_ij = inds[0] 
        
        #Seperate the starting indices of the repeats 
        i_ind = s_ij[0]
        j_ind = s_ij[1]
        
        #2. Assign the time steps of the repeated structures into  info_mat
        for x in results[0]:
            #If the row equals the x-value of the repeat
            if r == x:
                info_mat[r, 0] = i_ind + 1
                info_mat[r, 1] = i_ind + pattern_key[r] 
                info_mat[r, 2] = j_ind + 1 
                info_mat[r, 3] = j_ind + pattern_key[r]
                info_mat[r, 4] = pattern_key[r]
                
    return info_mat 

def stretch_diags(thresh_diags, band_width):
    """
    Creates binary matrix with full length diagonals from binary matrix of
        diagonal starts and length of diagonals
                                                                                 
    Args
    ----
    thresh_diags: np.array
        binary matrix where entries equal to 1 signal the existence 
        of a diagonal
    
    band_width: int
        length of encoded diagonals
    
    Returns
    -------
    stretch_diag_mat: np.array [boolean]
        logical matrix with diagonals of length band_width starting 
        at each entry prescribed in thresh_diag
    """
    # Creates size of returned matrix
    n = thresh_diags.shape[0] + band_width - 1
    
    temp_song_marks_out = np.zeros(n)
    
    (jnds, inds) = thresh_diags.nonzero()
    
    subtemp = np.identity(band_width)
    
    # Expands each entry in thresh_diags into diagonal of
    # length band width
    for i in range(inds.shape[0]):
        tempmat = np.zeros((n,n))
        
        tempmat[inds[i]:(inds[i] + band_width), 
                jnds[i]:(jnds[i] + band_width)] = subtemp
        
        temp_song_marks_out = temp_song_marks_out + tempmat
                
    # Ensures that stretch_diag_mat is a binary matrix
    stretch_diag_mat = (temp_song_marks_out > 0)
    
    return stretch_diag_mat

def __find_song_pattern(thresh_diags):
    """
    Stitches information from thresh_diags matrix into a single
        row, song_pattern, that shows the timesteps containing repeats;
        From the full matrix that decodes repeat beginnings (thresh_diags),
        the locations, or beats, where these repeats start are found and
        encoded into the song_pattern array

    Args
    ----
    thresh_diags: np.array
        binary matrix with 1 at the start of each repeat pair (SI,SJ) and 
        0 elsewhere. 
        WARNING: must be symmetric
    
    Returns
    -------
    song_pattern: np.array [shape = (1, song_length)]
        row where each entry represents a time step and the group 
        that time step is a member of
    """
    
    song_length = thresh_diags.shape[0]

    # Initialize song pattern base
    pattern_base = np.zeros((1,song_length), dtype = int)

    # Initialize group number
    pattern_num = 1
    
    col_sum = thresh_diags.sum(axis = 0)

    check_inds = col_sum.nonzero()
    check_inds = check_inds[0]
    
    # Creates vector of song length
    pattern_mask = np.ones((1, song_length))
    pattern_out = (col_sum == 0)
    pattern_mask = pattern_mask - pattern_out
    
    while np.size(check_inds) != 0:
        # Takes first entry in check_inds
        i = check_inds[0]
        
        # Takes the corresponding row from thresh_diags
        temp_row = thresh_diags[i,:]
        
        # Finds all time steps that i is close to
        inds = temp_row.nonzero()
        
        if np.size(inds) != 0:
            while np.size(inds) != 0:
                # Takes sum of rows corresponding to inds and
                # multiplies the sums against p_mask
                c_mat = np.sum(thresh_diags[inds,:], axis = 0)
                c_mat = c_mat*pattern_mask
                
                # Finds nonzero entries of c_mat
                c_inds = c_mat.nonzero()
                c_inds = c_inds[1]
                
                # Gives all elements of c_inds the same grouping 
                # number as i
                pattern_base[0,c_inds] = pattern_num
                
                # Removes all used elements of c_inds from
                # check_inds and p_mask
                check_inds = np.setdiff1d(check_inds, c_inds)
                pattern_mask[0,c_inds] = 0
                
                # Resets inds to c_inds with inds removed
                inds = np.setdiff1d(c_inds, inds)
                inds = np.delete(inds,0)
                
            # Updates grouping number to prepare for next group
            pattern_num = pattern_num + 1
            
        # Removes i from check_inds
        check_inds = np.setdiff1d(check_inds, i)
        
    pattern_base = pattern_base[:,1:]
    pattern_base = np.append(pattern_base, np.array([[0]]), axis = 1)
    song_pattern = pattern_base
    
    return song_pattern