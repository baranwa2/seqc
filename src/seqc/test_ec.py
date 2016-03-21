import correct_errors as err
import seqc
import pickle
import time
from three_bit import ThreeBit as bin_rep       #Using Ambrose coder for unity
import numpy as np
#import sam_reader
import sys
from scipy.special import gammaincinv

def from_thinair(barcode_files = ['/mnt/gel_barcode1_list_10.txt','/mnt/gel_barcode2_list_10.txt'], num_reads = 10000, err_rate = 0.01, num_features = 1, reverse_complement=True):
    '''
    USED FOR DEVELOPMENT ONLY
    Return a simulated grouped ReadArray for testing
    '''
    bases = ['A','C','G','T']
    alignment_d = {}
    
    def apply_error(str, err_rate):
        res = list(str)
        error = False
        for i in range(len(str)):
            if random.uniform(0,1)<err_rate:
                res[i] = random.choice(bases)   #There's a 1/4 chance for the same base to be elected so the actual err_rate is a bit smaller
                error = True
        return ''.join(res), error
    
    def generate_correct_rmt(rmt_length = 6):
        #return 'AAAAAA'
        res = ['A','A','A','A'] # To make sure erroneous rmt's are not as common as correct ones, we limit the range of correct rmt's to be only those starting with 'AA...'
        for i in range(rmt_length-len(res)):
            res.append(random.choice(bases))
        return ''.join(res)
    
    #TODO: this can be moved outside and merged with the snippet inside estimate error rate, also change to binary
    def get_codes(barcode_files, reverse_complement):
        correct_barcodes = []
        if reverse_complement:
            for barcode_file in barcode_files:
                with open(barcode_file) as f:
                    correct_barcodes.append(list(set(rev_comp(line.strip())
                                                for line in f.readlines())))
        else:
            for barcode_file in barcode_files:
                with open(barcode_file) as f:
                    correct_barcodes.append(list(set(line.strip()
                                                for line in f.readlines())))
        return correct_barcodes
        
    feature_list = range(num_features)
    codes = get_codes(barcode_files=barcode_files, reverse_complement=reverse_complement)
    validation_arr = np.zeros(num_reads)
    
    for i in range(num_reads):
        error = False
        c1, err = apply_error(random.choice(codes[0]), err_rate)
        c1 = bin_rep.str2bin(c1)
        error |= err
        c2, err = apply_error(random.choice(codes[1]), err_rate)
        c2 = bin_rep.str2bin(c2)
        error|= err
        rmt, err = apply_error(generate_correct_rmt(), err_rate)
        rmt = bin_rep.str2bin(rmt)
        error |= err
        feature = random.choice(feature_list)
        seq = bin_rep.ints2int([c1, c2, rmt])
        if feature in alignment_d.keys():
            try:    #TODO: try and use a list instead of an ndarray to save memory
                alignment_d[feature][seq] = np.append(alignment_d[feature][seq],i)    # Since we don't have a real RA to link back to, we use the index i itself
            except KeyError:
                alignment_d[feature][seq] = np.array([i])
        else:
            alignment_d[feature] = {}
            alignment_d[feature][seq] = np.array([i])
        if error:
            validation_arr[i] = 1
    return alignment_d, validation_arr


def compare_methods(err_res_mat):
    """Return a matrix containig the Jaccard score between each two methods"""
    jac_mat = np.zeros((err.NUM_OF_ERROR_CORRECTION_METHODS,err.NUM_OF_ERROR_CORRECTION_METHODS))
    for i in range(jac_mat.shape[0]):
        for j in range(jac_mat.shape[1]):
            jac_mat[i,j] = sum(err_res_mat[:,i]*err_res_mat[:,j]) / (sum(err_res_mat)[i]+sum(err_res_mat)[j]-sum(err_res_mat[:,i]*err_res_mat[:,j]))
    return jac_mat

def compare_methods_venn(err_res_mat):
    ''' Return the size of each area in the 4 venn diagram'''
    r = {'none': 0, 
          'AJC': 0,
          'sten': 0,
          'allon': 0,
          'jaitin': 0,
          'AJC-sten': 0,
          'AJC-allon': 0,
          'AJC-jaitin':0,
          'sten-allon': 0,
          'sten-jaitin': 0,
          'allon-jaitin': 0,
          'AJC-sten-allon': 0,
          'AJC-allon-jaitin': 0,
          'sten-allon-jaitin': 0,
          'all': 0}
          
    #Doing the calculations beforehand saves time by storing the result and avoiding duplicate calculations
    sums = sum(err_res_mat)         # area of all 4 methods
    aj_s = sum(err_res_mat[:,err.ERROR_CORRECTION_AJC]*err_res_mat[:,err.ERROR_CORRECTION_STEN])    #|AJC /\ sten|
    aj_al = sum(err_res_mat[:,err.ERROR_CORRECTION_AJC]*err_res_mat[:,err.ERROR_CORRECTION_ALLON])  #|AJC /\ allon|
    aj_j = sum(err_res_mat[:,err.ERROR_CORRECTION_AJC]*err_res_mat[:,err.ERROR_CORRECTION_jaitin]) #|AJC /\ jaitin|
    s_al = sum(err_res_mat[:,err.ERROR_CORRECTION_ALLON]*err_res_mat[:,err.ERROR_CORRECTION_STEN])  #|sten /\ allon|
    s_j = sum(err_res_mat[:,err.ERROR_CORRECTION_jaitin]*err_res_mat[:,err.ERROR_CORRECTION_STEN]) #|sten /\ jaitin|
    al_j = sum(err_res_mat[:,err.ERROR_CORRECTION_ALLON]*err_res_mat[:,err.ERROR_CORRECTION_jaitin])   #|allon /\ jaitin|
    aj_s_a = sum(err_res_mat[:,err.ERROR_CORRECTION_ALLON]*err_res_mat[:,err.ERROR_CORRECTION_STEN]*err_res_mat[:,err.ERROR_CORRECTION_AJC])    #|allon /\ sten /\ AJC|
    aj_s_j = sum(err_res_mat[:,err.ERROR_CORRECTION_AJC]*err_res_mat[:,err.ERROR_CORRECTION_STEN]*err_res_mat[:,err.ERROR_CORRECTION_jaitin])  #|AJC /\ sten /\ jaitin|
    s_a_j = sum(err_res_mat[:,err.ERROR_CORRECTION_ALLON]*err_res_mat[:,err.ERROR_CORRECTION_STEN]*err_res_mat[:,err.ERROR_CORRECTION_jaitin]) #|allon /\ sten /\ jaitin|
    aj_a_j = sum(err_res_mat[:,err.ERROR_CORRECTION_ALLON]*err_res_mat[:,err.ERROR_CORRECTION_jaitin]*err_res_mat[:,err.ERROR_CORRECTION_AJC]) #|allon /\ jaitin /\ AJC|

    r['all'] = sum(err_res_mat[:,err.ERROR_CORRECTION_AJC]*err_res_mat[:,err.ERROR_CORRECTION_STEN]*err_res_mat[:,err.ERROR_CORRECTION_jaitin]*err_res_mat[:,err.ERROR_CORRECTION_ALLON]) #|AJC /\ sten /\ allon /\ jaitin|

    r['AJC-sten-allon'] = aj_s_a - r['all']
    r['AJC-sten-jaitin'] = aj_s_j - r['all']
    r['AJC-allon-jaitin'] = aj_a_j - r['all']
    r['sten-allon-jaitin'] = s_a_j - r['all']

    r['AJC-allon'] = aj_al - r['AJC-sten-allon'] - r['AJC-allon-jaitin'] - r['all']
    r['AJC-sten'] = aj_s - r['AJC-sten-allon'] - r['AJC-sten-jaitin'] - r['all']
    r['AJC-jaitin'] = aj_j - r['AJC-sten-jaitin'] - r['AJC-allon-jaitin'] - r['all']
    r['sten-allon'] = s_al - r['AJC-sten-allon'] - r['sten-allon-jaitin'] - r['all']
    r['sten-jaitin'] = s_j - r['AJC-sten-jaitin'] - r['sten-allon-jaitin'] - r['all']
    r['allon-jaitin'] = al_j - r['AJC-allon-jaitin'] - r['sten-allon-jaitin'] - r['all']

    r['AJC'] = sums[err.ERROR_CORRECTION_AJC] - r['AJC-sten-allon'] - r['AJC-sten-jaitin'] - r['AJC-allon-jaitin'] - r['AJC-allon'] - r['AJC-sten'] - r['AJC-jaitin'] - r['all']
    r['sten'] = sums[err.ERROR_CORRECTION_STEN] - r['AJC-sten-allon'] - r['AJC-sten-jaitin'] -  r['sten-allon-jaitin'] - r['AJC-sten'] - r['sten-allon'] - r['sten-jaitin'] - r['all']
    r['allon'] = sums[err.ERROR_CORRECTION_ALLON] - r['AJC-sten-allon'] - r['AJC-allon-jaitin'] - r['sten-allon-jaitin'] - r['AJC-allon'] - r['sten-allon'] - r['allon-jaitin'] - r['all']
    r['jaitin'] = sums[err.ERROR_CORRECTION_jaitin] - r['AJC-sten-jaitin'] - r['AJC-allon-jaitin'] - r['sten-allon-jaitin'] - r['AJC-jaitin'] - r['sten-jaitin'] - r['allon-jaitin'] - r['all']

    r['none']  = err_res_mat.shape[0] - sum(r.values())
    
    return r

def test_err_correction(fname, read_array = None, barcodes = ['/mnt/gel_barcode1_list.txt','/mnt/gel_barcode2_list.txt'], annotations = '/mnt/annotations.gtf', fl = 1000, mat_file=''):
    '''run the error correction on all 4 methods and analyse the results'''
    
    #fout = open(fname+'_filter_out.txt','w+')
    ra = read_array
    if ra == None:
        print('converting features')
        cf = seqc.convert_features.ConvertFeatureCoordinates.from_gtf(annotations, fl)
        print ('reading from samfile')
        ra = seqc.arrays.ReadArray.from_samfile(fname,cf)
    #fout.write('len ra: '+str(len(ra))+'\n\n')
    print('correcting errors')  
    res_full, res_sum = err.correct_errors(ra, barcodes, compare_methods=True, P_VALUE=0.05)
    #fout.write(str(res_sum)+'\n\n')
    print('Applying filters')
    apply_filters(ra, res_full)
    #print('analyzing results - jaccard score')
    #r1 = compare_methods(res_full)
    #fout.write(str(r1)+'\n\n')
    #print('analyzing results - venn')
    #r2 = compare_methods_venn(res_full)
    #fout.write(str(r2)+'\n\n')
    if mat_file != '':
        print('Dumping result matrix to file')
        matf = open(mat_file, 'wb')
        pickle.dump(res_full, matf, protocol=4)
        matf.close()
    #fout.close()
    return res_full
    
def calc_read_dist(fname, barcodes = ['/mnt/gel_barcode1_list.txt','/mnt/gel_barcode2_list.txt'], annotations = '/mnt/annotations.gtf', fl = 1000):
    '''return a histogram of numbers of reads per gene/seq'''
    
    fout = open(fname+'_dist.txt','w+')
    print('converting features')
    cf = seqc.convert_features.ConvertFeatureCoordinates.from_gtf(annotations, fl)
    print ('reading from samfile')
    ra = seqc.arrays.ReadArray.from_samfile(fname,cf)
    
    print('grouping ReadArray')  
    ra_grouped = ra.group_for_error_correction(required_poly_t = 1)
    
    print('Counting read appearence frequency')
    hist = {}
    for feature in ra_grouped.keys():
        for seq in ra_grouped[feature].keys():
            q = ra_grouped[feature][seq].shape[0]
            if q in hist.keys():
                hist[q] += 1
            else:
                hist[q] = 1
    for k,v in hist.items():
        fout.write(str(k)+'\t'+str(v)+'\n')
    
    fout.close()

def validate_correct_errors(num_reads = 10000, err_rate = 0.01, num_features = 1, barcode_files = ['/mnt/gel_barcode1_list_10.txt','/mnt/gel_barcode2_list_10.txt'], reverse_complement = True, donor_cutoff=1, P_VALUE=0.1):
    ''' Use a simulation model to validate error_correction. The jaitin method is not validated and instead its column in the matrix is used for the
        true errors.'''
    
    fname = 'r'+str(num_reads)+'_er'+str(err_rate)+'_f'+str(num_features)
    fout = open(fname+'_simul.txt','w+')
    
    res_time_cnt = {}
    
    err_correction_res = np.zeros((num_reads, NUM_OF_ERROR_CORRECTION_METHODS))
    print('simulationg data')
    ra_grouped, validation = from_thinair(barcode_files, num_reads, err_rate, num_features)
    # The ra is not needed for these 3 methods and should also be removed as a parameter...
    print ('doing AJC')
    res_time_cnt[ERROR_CORRECTION_AJC] = correct_errors_AJC(ra_grouped, err_correction_res, barcode_files, reverse_complement, donor_cutoff, P_VALUE)
    print ('doing Sten')
    res_time_cnt[ERROR_CORRECTION_STEN] = correct_errors_sten(ra_grouped, err_correction_res)
    print ('doing Allon')
    res_time_cnt[ERROR_CORRECTION_ALLON] = correct_errors_allon(ra_grouped, err_correction_res, barcode_files, reverse_complement)
    err_correction_res[:,ERROR_CORRECTION_jaitin] = validation
    
    fout.write(str(res_time_cnt)+'\n\n')
    print('analyzing results - jaccard score')
    r1 = compare_methods(err_correction_res)
    fout.write(str(r1)+'\n\n')
    print('analyzing results - venn')
    r2 = compare_methods_venn(err_correction_res)
    fout.write(str(r2)+'\n\n')
        
    fout.close()
    
def apply_filters(alignments_ra, err_correction_res):
    """Correct errors using the method in Sten's paper.
       Remove any molecule supported by only a single read"""
    
    # for python 3
    start = time.process_time() 

    error_count = 0
    N = bin_rep._str2bindict['N']

    for idx, read in enumerate(alignments_ra.data):
        if bin_rep.contains(read['rmt'], N):
                continue
        if read['dust_score'] >= 10:
            err_correction_res[idx][err.ERROR_CORRECTION_FILTERS] = 1
            error_count+=1
    
    print ('filter count: ', error_count)
    tot_time=time.process_time()-start
    print('total filters runtime: ',tot_time)
    return error_count, tot_time
    
def gc_content(res_mat, samfile, col1, col2):
    ''' return the average gc content of reads from a sam_file that correspond to col in res_mat'''
    
    tot_len = {'all':0, 'col1': 0, 'col2': 0, 'both': 0}
    tot_gc = {'all':0, 'col1': 0, 'col2': 0, 'both': 0}
    sr = sam_reader.Reader(samfile)
    for i, r in enumerate(sr.iter_multialignments()):
        l = len(r[0].seq)
        gc = gc_count(r[0].seq)
        if i < res_mat.shape[0]:    # For a weird reason the ra is one record short on my test files
            tot_len['all'] += l
            tot_gc['all'] += gc
            if res_mat[i][col1] == 1 and res_mat[i][col2] == 1:
                tot_len['both'] += l
                tot_gc['both'] += gc
            elif res_mat[i][col1] == 1 and res_mat[i][col2] == 0:
                tot_len['col1'] += l
                tot_gc['col1'] += gc
            elif res_mat[i][col1] == 0 and res_mat[i][col2] == 1:
                tot_len['col2'] += l
                tot_gc['col2'] += gc
                
    res = {}
    for k in tot_len.keys():
        res[k] = tot_gc[k]/tot_len[k]
    return res
    
def triple_entropy(res_mat, samfile, col1, col2, fname=''):
    ''' return the average gc content of reads from a sam_file that correspond to col in res_mat'''
    if fname != '':
        fout = open(fname, 'w+')
    dist_all = {}
    dist_col1 = {}
    dist_col2 = {}
    dist_both = {}
    sr = sam_reader.Reader(samfile)
    l = len(sr)
    for i, r in enumerate(sr.iter_multialignments()):
        if 'N' in r[0].seq:
            continue
        if i%10000 == 0:
            print('\r'+str(i)+'/'+str(l)+' done')
        if i < res_mat.shape[0]:    # For a weird reason the ra is one record short on my test files
            dist_all = triple_entropy_count(r[0].seq, dist_all)
            if res_mat[i][col1] == 1 and res_mat[i][col2] == 1:
                dist_both = triple_entropy_count(r[0].seq, dist_both)
            elif res_mat[i][col1] == 1 and res_mat[i][col2] == 0:
                dist_col1 = triple_entropy_count(r[0].seq, dist_col1)
            elif res_mat[i][col1] == 0 and res_mat[i][col2] == 1:
                dist_col2 = triple_entropy_count(r[0].seq, dist_col2)                
    
    if fname != '':
        fout.write('triplet\tall\tcol1\tcol2\tboth\n')
        for k in sorted(dist_all.keys()):
            fout.write(k + '\t')
            try:
                fout.write(str(dist_all[k])+'\t')
            except KeyError:
                fout.write('0\t')
            try:
                fout.write(str(dist_col1[k])+'\t')
            except KeyError:
                fout.write('0\t')
            try:
                fout.write(str(dist_col2[k])+'\t')
            except KeyError:
                fout.write('0\t')
            try:
                fout.write(str(dist_both[k])+'\n')
            except KeyError:
                fout.write('0\n')
        fout.close()
    
def gc_count(seq):
    count=0
    for base in seq:
        if base=='G' or base=='C':
            count+=1
    return count

def triple_entropy_count(seq, dist_d):
    for i in range(3,len(seq)+1):
        try:
            dist_d[seq[i-3:i]] += 1
        except KeyError:
            dist_d[seq[i-3:i]] = 1
    return dist_d
    
def cell_dist(res_mat, ra, col1, col2, fname=''):
    '''return the average cell distribution for reads that correspond to col1, col2, col1/\col2 and all in res_mat'''
    if fname != '':
        fout = open(fname, 'w+')
    dist_all = {}
    dist_col1 = {}
    dist_col2 = {}
    dist_both = {}
    
    for i, r in enumerate(ra):
        if bin_rep.contains(r[0]['rmt'], 'N'):
            continue
        cell = r[0]['cell']
        try:
            dist_all[cell] += 1
        except KeyError:
            dist_all[cell] = 1
        if res_mat[i][col1] == 1 and res_mat[i][col2] == 1:
            try:
                dist_both[cell] += 1
            except KeyError:
                dist_both[cell] = 1
        elif res_mat[i][col1] == 1 and res_mat[i][col2] == 0:
            try:
                dist_col1[cell] += 1
            except KeyError:
                dist_col1[cell] = 1
        elif res_mat[i][col1] == 0 and res_mat[i][col2] == 1:
            try:
                dist_col2[cell] += 1
            except KeyError:
                dist_col2[cell] = 1

    if fname != '':
        fout.write('cell\tall\tcol1\tcol2\tboth\n')
        for k in dist_all.keys():
            fout.write(str(k) + '\t')
            try:
                fout.write(str(dist_all[k])+'\t')
            except KeyError:
                fout.write('0\t')
            try:
                fout.write(str(dist_col1[k])+'\t')
            except KeyError:
                fout.write('0\t')
            try:
                fout.write(str(dist_col2[k])+'\t')
            except KeyError:
                fout.write('0\t')
            try:
                fout.write(str(dist_both[k])+'\n')
            except KeyError:
                fout.write('0\n')
        fout.close()
        
        
def num_pos_dist(ra, fname = ''):
    dist_dic = {}
    res_dic = {}
    for i, r in enumerate(ra):
        if ra.features[i].shape[0] != 1:
            continue
        pos = ra.positions[i]
        if len(pos) < 1:
            continue
        gene = ra.features[i][0]
        try:
            l = dist_dic[(r[0]['cell'], r[0]['rmt'], gene)]
            dist_dic[(r[0]['cell'], r[0]['rmt'], gene)] = np.concatenate((l,pos))
        except KeyError:
            dist_dic[(r[0]['cell'], r[0]['rmt'], gene)] = pos
    
    for k in dist_dic.keys():
        try:
            res_dic[len(set(dist_dic[k]))]+=1
        except KeyError:
            res_dic[len(set(dist_dic[k]))] = 1
    if fname!='':
        fout = open(fname,'w')
        fout.write('num of positions\tnum reads\n')
        for num_pos in res_dic.keys():
            fout.write(str(num_pos)+'\t'+str(res_dic[num_pos])+'\n')    
        fout.close()
    return res_dic

def pos_instances(ra, fname = ''):
    pos_dic = {}
    for i, r in enumerate(ra):
        if ra.features[i].shape[0] != 1:
            continue
        for pos in ra.positions[i]:
            try:
                pos_dic[pos]+=1
            except KeyError:
                pos_dic[pos] = 1
    if fname!='':
        fout = open(fname, 'w')
        fout.write('position\tnum reads\n')
        for pos in pos_dic.keys():
            fout.write(str(pos)+'\t'+str(pos_dic[pos])+'\n')
        fout.close()
        
def gene_dist_grouped(ra_g, fname=''):
    gene_dic={}
    for gene in ra_g.keys():
        if gene not in gene_dic.keys():
            gene_dic[gene]=0
        for seq in ra_g[gene].keys():
            #gene_dic[gene]+=ra_g[gene][seq].shape[0]
            #gene_dic[gene]+=ra_g[gene][seq]
            gene_dic[gene]+=len(ra_g[gene][seq])
    if fname != '':
        fout = open(fname, 'w')
        fout.write('gene\tnum reads\n')
        for gene in gene_dic.keys():
            fout.write(str(gene)+'\t'+str(gene_dic[gene])+'\n')
        fout.close()

def gene_dist_ra(ra, fname=''):
    gene_dic={}
    for r in ra.features:
        if len(r)!=1:
            continue
        gene = r[0]
        if gene==0:
            continue
        try:
            gene_dic[gene]+=1
        except KeyError:
            gene_dic[gene]=1
        
    if fname != '':
        fout = open(fname, 'w')
        fout.write('gene\tnum reads\n')
        for gene in gene_dic.keys():
            fout.write(str(gene)+'\t'+str(gene_dic[gene])+'\n')
        fout.close()


def pos_gene_instances(ra, fname = ''):
    pos_dic = {}
    for i, r in enumerate(ra):
        if ra.features[i].shape[0] != 1:
            continue
        gene = ra.features[i][0]
        for pos in ra.positions[i]:
            try:
                pos_dic[gene][pos]+=1
            except KeyError:
                try:
                    pos_dic[gene][pos] = 1
                except KeyError:
                    pos_dic[gene] = {}
                    pos_dic[gene][pos] = 1
    if fname != '':
        fout = open(fname, 'w')
        fout.write('gene\tposition\tnum reads\n')
        for gene in pos_dic.keys():
            for pos in pos_dic[gene].keys():
                fout.write(str(gene)+'\t'+str(pos)+'\t'+str(pos_dic[gene][pos])+'\n')
        fout.close()

    
def group_hamm_dist(ra, reads):
    '''Gets an ra and a list on indices representing reads and returns:
        1. Average hamming distance between all pairs
        2. fraction of pairs with hamming distance of 1 or less'''

    cnt = 0
    sum = 0
    low_cnt = 0
    for r1 in reads:
        for r2 in reads:
            d_codes = err.hamming_dist_bin(int(ra[r1][0]['cell']), int(ra[r2][0]['cell']))
            d_rmt = err.hamming_dist_bin(int(ra[r1][0]['rmt']), int(ra[r2][0]['rmt']))
            if d_codes!=err.high_value:
                cnt+=1
                sum+=d_codes+d_rmt
                if d_codes+d_rmt<= 1:
                    low_cnt+=1
    return sum/cnt, low_cnt/cnt
    
def test_ham_dist(ra, pos, gene=None):
    
    reads = []
    for i, r in enumerate(ra):
        if pos in ra.positions[i]:
            if gene==None:
                reads.append(i)
            elif gene in ra.features[i]:
                reads.append(i)
    avg, frac = group_hamm_dist(ra, reads)
    return avg, frac

def n_random_reads(ra, fname='', n=100):
    '''Returns indexes of n random reads from the readArray'''
    iter = 1000
    res = []
    for i in range(iter):
        res.append(group_hamm_dist(ra, np.random.randint(len(ra), size=n)))
    if fname!='':
        f = open(fname,'w')
        f.write('average distance\tfraction of close reads\n')
        for avg, frac in res:
            f.write(str(avg) + '\t' + str(frac) + '\n')
        f.close()
        
def base_rmt_count(ra_grouped):
    base_freq = {bin_rep._str2bindict['A']:0, bin_rep._str2bindict['C']:0, bin_rep._str2bindict['G']:0, bin_rep._str2bindict['T']:0}
    N = bin_rep._str2bindict['N']
    for gene in ra_grouped.keys():
        for seq in ra_grouped[gene].keys():
            if bin_rep.contains(seq, N):
                continue
            rmt = bin_rep.rmt_from_int(seq)
            while rmt>0:
                base_freq[rmt&0b111]+=len(ra_grouped[gene][seq])
                rmt>>=3
    return base_freq
    
def correct_errors_AJC(ra_grouped, err_rate, err_correction_res, reverse_complement=True, donor_cutoff=1, P_VALUE=0.1, fname=''):
    """calculate and correct errors in barcode sets"""
    start = time.process_time()
    d = ra_grouped

    threshold_donors_l=[]
    err_gene_dic = {}
    error_count = 0
    #err_rate = err.estimate_error_rate(barcode_files, ra_grouped, reverse_complement)
    
    tot_feats = len(ra_grouped)
    cur_f = 0
    
    N = bin_rep._str2bindict['N']
    for_removal = []
    for feature in d.keys():
        sys.stdout.write('\r' + str(cur_f) + '/' + str(tot_feats) + ' features processed. ('+str((100*cur_f)/tot_feats)+'%)')
        cur_f += 1
        if feature==0:  
            continue
        
        group_size=0
        for r_seq in d[feature].keys():
            if bin_rep.contains(r_seq, N):
                continue
            group_size += len(d[feature][r_seq])
                
        for r_seq in d[feature].keys():
            if bin_rep.contains(r_seq, N):
                continue
            
            gene = feature
            r_c1 = bin_rep.c1_from_int(r_seq)
            r_c2 = bin_rep.c2_from_int(r_seq)
            r_rmt = bin_rep.rmt_from_int(r_seq)
            r_num_occurences = len(d[gene][r_seq])


            threshold = gammaincinv(r_num_occurences, P_VALUE)
            
            expected_errors = 0
            tot_donors = 0
            for d_rmt in err.generate_close_seq(r_rmt):
                d_seq = bin_rep.ints2int([r_c1,r_c2,d_rmt])
                try:
                    d_num_occurences = len(d[gene][d_seq])
                    tot_donors += d_num_occurences
                except KeyError:
                    continue
                if d_num_occurences<=donor_cutoff:
                    continue
                d_rmt = bin_rep.rmt_from_int(d_seq)

                p_dtr = err.prob_d_to_r_bin(d_rmt, r_rmt, err_rate)
                
                expected_errors += d_num_occurences * p_dtr
                if expected_errors > threshold:
                    for_removal.append((gene, r_seq))
                    error_count+=r_num_occurences
                    try:
                        err_gene_dic[gene] += r_num_occurences
                    except KeyError:
                        err_gene_dic[gene] = r_num_occurences
                    break
            #if r_num_occurences <= 1:
            #    threshold_donors_l.append((group_size, tot_donors, expected_errors))
    for (gene, r_seq) in for_removal:
        err_correction_res[ra_grouped[gene][r_seq],[err.ERROR_CORRECTION_AJC]] = 1
    if fname!='':
        f=open(fname, 'w+')
        #f.write('Num of potential donors\tnum of actual donors\tlambda')
        f.write('gene\tnum of errors\n')
        #for pos_d, act_don, lam in threshold_donors_l:
            #f.write(str(pos_d) + '\t' + str(act_don) + '\t' + str(lam) + '\n')
        for gene in err_gene_dic.keys():
            f.write(str(gene) + '\t' + str(err_gene_dic[gene]) + '\n')
        f.close()
    print ('\nAJC error_count: ', error_count)
    tot_time=time.process_time()-start
    print('total AJC error_correction runtime: ',tot_time)
    return error_count, tot_time
    
def seq_hist(ra_grouped, gene, fname):
    f=open(fname,'w')
    f.write('seq/tnum reads/n')
    for seq in ra_grouped[gene].keys():
        f.write(str(seq)+'/t'+str(ra_grouped[gene][seq].shape[0])+'/n')
    f.close()

def correct_errors_jaitin(alignment_ra, ra_grouped, err_correction_res):
    """Correct errors according to jaitin method """
    
    #sort reads by number of positions
    #go from least to most:
    #   go over all d_seq:
    #       if d_seq is 1 dist from r_seq and covers the same positions:
    #           remove r_seq.
    #
    # Note: the sorting isn't really important, it just saves time.
    
    """calculate and correct errors in barcode sets"""
    start = time.process_time()
    d = ra_grouped
#   print('version 6.0 - using readArray')

    error_count = 0
    
    tot_feats = len(ra_grouped)
    cur_f = 0
    
    N = bin_rep._str2bindict['N']
    for_removal = []
    tot=0
    for feature in d.keys():
        sys.stdout.write('\r' + str(cur_f) + '/' + str(tot_feats) + ' features processed. ('+str((100*cur_f)/tot_feats)+'%)')
        cur_f += 1
        if feature==0:
            continue
        cur_seq=0
        tot_seq=len(d[feature].keys())
        sorted_seq_l = sorted([(seq, len(set(np.hstack(alignment_ra.positions[d[feature][seq]])))) for seq in d[feature].keys()], key=lambda x:x[1])
        for idx, r_seqs in enumerate(sorted_seq_l):
            r_seq = r_seqs[0]
            cur_seq+=1
            sys.stdout.write('\rfeature: '+str(cur_f) + '/' + str(tot_feats) + ', seq: ' + str(cur_seq) + '/' + str(tot_seq))
            if bin_rep.contains(r_seq, N):
                continue
            
            gene = feature
            r_rmt = bin_rep.rmt_from_int(r_seq)
            r_pos_list = np.hstack(alignment_ra.positions[d[feature][r_seq]])

            for d_idx in range(idx-1, -1, -1):
                d_seq = sorted_seq_l[d_idx][0]
                d_rmt = bin_rep.rmt_from_int(d_seq)
                d_pos_list = np.hstack(alignment_ra.positions[d[feature][r_seq]])

                if err.hamming_dist_bin(r_rmt, d_rmt) == 1 and set(r_pos_list).issubset(set(d_pos_list)):
     #               for_removal.append((gene, r_seq))
                    error_count+=len(d[feature][r_seq])
                    break
    for (gene, r_seq) in for_removal:
        err_correction_res[ra_grouped[gene][r_seq],[err.ERROR_CORRECTION_jaitin]] = 1
    
    print ('\njaitin error_count: ', error_count)
    tot_time=time.process_time()-start
    print('total jaitin error_correction runtime: ',tot_time)
    return error_count, tot_time
	
#This is used just for running the Jaitin method for comparison.
def group_for_ec_pos(ra, scid_to_gene_map, required_poly_t=1):
    res = {}
    no_single_gene = 0
    cell_0 = 0
    rmt_0 = 0
    small_poly_t = 0
    tot = 0
    
    for i, v in enumerate(ra.data):
        tot += 1
        #Apply various perliminary filters on the data
        if ra.features[i][0] == 0:
            no_single_gene += 1
            continue
        if v['cell']==0:
            cell_0 += 1
            continue
        if v['rmt']==0:
            rmt_0 += 1
            continue
        if v['n_poly_t']<=required_poly_t:
            small_poly_t += 1
            continue
            
        
        #map the feature to a gene
        try:
            gene = scid_to_gene_map[ra.features[i][0]]
        except KeyError:
            print ('No gene mapped to feature ', ra.features[i][0], ' ignoring.')
            continue
        
        seq = bin_rep.ints2int([int(v['cell']),int(v['rmt'])])
        
        try:
            res[gene][int(v['cell'])][int(v['rmt'])].append(i)
        except KeyError:
            try:
                res[gene][int(v['cell'])][int(v['rmt'])] = [i]
            except KeyError:
                try:
                    res[gene][int(v['cell'])] = {}
                    res[gene][int(v['cell'])][int(v['rmt'])] = [i]
                except KeyError:
                    res[gene]={}
                    res[gene][int(v['cell'])] = {}
                    res[gene][int(v['cell'])][int(v['rmt'])] = [i]
    print('total reads: ',tot,' no single gene: ',no_single_gene,' cell is zero: ',cell_0, ' rmt is zero: ',rmt_0,' small poly_t: ',small_poly_t)
    return res

	        
def correct_errors_jaitin(alignment_ra, ra_grouped, err_correction_res):
    """Correct errors according to jaitin method """
    
    #sort reads by number of positions
    #go from least to most:
    #   go over all d_seq:
    #       if d_seq is 1 dist from r_seq and covers the same positions:
    #           remove r_seq.
    #
    # Note: the sorting isn't really important, it just saves time.
    
    """calculate and correct errors in barcode sets"""
    start = time.process_time()
    d = ra_grouped

    error_count = 0
    
    tot_feats = len(ra_grouped)
    cur_f = 0
    
    N = bin_rep._str2bindict['N']
    for_removal = []
    tot=0
    for feature in d.keys():
        #sys.stdout.write('\r' + str(cur_f) + '/' + str(tot_feats) + ' features processed. ('+str((100*cur_f)/tot_feats)+'%)')
        #cur_f += 1
        if feature==0:
            continue
        #cur_seq=0
        #tot_seq=len(d[feature].keys())
        sorted_seq_l = sorted([(seq, len(set(np.hstack(alignment_ra.positions[d[feature][seq]])))) for seq in d[feature].keys()], key=lambda x:x[1])
        for idx, r_seqs in enumerate(sorted_seq_l):
            r_seq = r_seqs[0]
            #cur_seq+=1
            #sys.stdout.write('\rfeature: '+str(cur_f) + '/' + str(tot_feats) + ', seq: ' + str(cur_seq) + '/' + str(tot_seq))
            if bin_rep.contains(r_seq, N):
                continue
            
            gene = feature
            r_rmt = bin_rep.rmt_from_int(r_seq)
            r_pos_list = np.hstack(alignment_ra.positions[d[feature][r_seq]])

            for d_idx in range(idx-1, -1, -1):
                d_seq = sorted_seq_l[d_idx][0]
                d_rmt = bin_rep.rmt_from_int(d_seq)
                d_pos_list = np.hstack(alignment_ra.positions[d[feature][r_seq]])

                if hamming_dist_bin(r_rmt, d_rmt) == 1 and set(r_pos_list).issubset(set(d_pos_list)):
                    for_removal.append((gene, r_seq))
                    error_count+=len(d[feature][r_seq])
                    break
    for (gene, r_seq) in for_removal:
        err_correction_res[ra_grouped[gene][r_seq],[err.ERROR_CORRECTION_jaitin]] = 1
    
    print ('\nJaitin error_count: ', error_count)
    tot_time=time.process_time()-start
    print('total Jaitin error_correction runtime: ',tot_time)
    return error_count, tot_time

# This is old and probably needs to be updated before use
def correct_errors_allon(ra_grouped, err_correction_res, barcode_files, reverse_complement=True):
    """Correct errors using the method in Allon paper.
       Compare barcodes to list and discard any reads that have more
       than two mismatches from all barcodes on the list"""

    start = time.process_time()
    d = ra_grouped
    
    error_count = 0
    N = bin_rep._str2bindict['N']
    for_removal = []
    
    tot_feats = len(ra_grouped)
    cur_f = 0

    #create barcode list from barcode_files
    correct_barcodes = []
    if reverse_complement:
        for barcode_file in barcode_files:
            with open(barcode_file) as f:
                correct_barcodes.append(set(bin_rep.str2bin(rev_comp(line.strip()))
                                            for line in f.readlines()))
    else:
        for barcode_file in barcode_files:
            with open(barcode_file) as f:
                correct_barcodes.append(set(bin_rep.str2bin(line.strip())
                                            for line in f.readlines()))
    for feature in d.keys():
        sys.stdout.write('\r' + str(cur_f) + '/' + str(tot_feats) + ' features processed. ('+str((100*cur_f)/tot_feats)+'%)')
        cur_f += 1
        for r_seq in d[feature].keys():
            if bin_rep.contains(r_seq, N):
                continue

            gene = feature
            r_c1 = bin_rep.c1_from_int(r_seq)
            r_c2 = bin_rep.c2_from_int(r_seq)
            r_err_cnt = 0
            if r_c1 not in correct_barcodes[0]:
                r_err_cnt += len(list_errors(r_c1, correct_barcodes[0]))
            if r_c2 not in correct_barcodes[1]:
                r_err_cnt += len(list_errors(r_c2, correct_barcodes[1]))
            if(r_err_cnt > 2):
                for_removal.append((gene, r_seq))
                error_count+=1

    for (gene, r_seq) in for_removal:
        err_correction_res[ra_grouped[gene][r_seq],[ERROR_CORRECTION_ALLON]] = 1

    print ('\nAllon error count: ', error_count)
    tot_time=time.process_time()-start
    print('total Allon error_correction runtime: ',tot_time)
    return error_count, tot_time

# This is old and probably needs to be updated before use
def correct_errors_sten(ra_grouped, err_correction_res):
    """Correct errors using the method in Sten's paper.
       Remove any molecule supported by only a single read"""
    
    # for python 3
    start = time.process_time() 

    d = ra_grouped
    

    error_count = 0
    N = bin_rep._str2bindict['N']
    for_removal = []

    for feature in d.keys():
        for r_seq in d[feature].keys():
            if bin_rep.contains(r_seq, N):
                continue

            gene = feature
            r_num_occurences = d[gene][r_seq].shape[0]

            if(r_num_occurences <= 1):
                for_removal.append((gene, r_seq))
                error_count+=1

    for (gene, r_seq) in for_removal:
        err_correction_res[ra_grouped[gene][r_seq],[ERROR_CORRECTION_STEN]] = 1        #TODO: check that this is the correct way to address the array
    print ('Sten error_count: ', error_count)
    tot_time=time.process_time()-start
    print('total Sten error_correction runtime: ',tot_time)
    return error_count, tot_time

   def estimate_error_rate(barcode_files, grouped_ra, reverse_complement=True):
    '''
    Estimate the error rate based on the barcodes in the data and the correct barcodes in the barcode file.
    Return an error_rate table.
    ''' 
    correct_barcodes = []
    if reverse_complement:
        for barcode_file in barcode_files:
            with open(barcode_file) as f:
                correct_barcodes.append(set(bin_rep.str2bin(rev_comp(line.strip()))
                                            for line in f.readlines()))
    else:
        for barcode_file in barcode_files:
            with open(barcode_file) as f:
                correct_barcodes.append(set(bin_rep.str2bin(line.strip())
                                            for line in f.readlines()))

    # go over the sequences in the file to calculate the error rate
    correct_instances = 0
    errors = list(bin_rep.ints2int([p[0],p[1]]) for p in permutations(bin_rep.bin_nums, r=2))
    error_table = dict(zip(errors, [0] * len(errors)))
    
    N = bin_rep._str2bindict['N']     
    
    
    dynamic_codes_table_c1 = {}
    dynamic_codes_table_c2 = {}
    #tot = len(ra.data)
    tot = 0
    print('\n')
    ignored=0
    repeated = 0
    new = 0
    #for i, read in enumerate(ra.data):
    #for read in ra.data:
    for gene in grouped_ra.keys():
        tot+=len(grouped_ra[gene])
    #    if i%100000==0:
    #        sys.stdout.write('\rDoing read: '+str(i)+'/'+str(tot)+' ('+str(i/tot)+'%)')
        for seq in grouped_ra[gene].keys():
                    
            #if bin_rep.contains(int(read['cell']), N):
            if bin_rep.contains(seq, N):
                    ignored+=1
                    continue
                    
            #c1 = bin_rep.c1_from_codes(int(read['cell']))
            #c2 = bin_rep.c2_from_codes(int(read['cell']))
            c1 = bin_rep.c1_from_int(seq)
            c2 = bin_rep.c2_from_int(seq)
            #print(str(c1), str(c2))
            
            try:
                #print('a.')
                cor_c1, err_c1, ed_1 = dynamic_codes_table_c1[c1]
                repeated+=1
            except KeyError:
                #print('b')
                new+=1
                cor_c1, err_c1, ed_1 = find_correct_barcode(c1, correct_barcodes[0])
                dynamic_codes_table_c1[c1] = cor_c1, err_c1, ed_1
            try:
                #print('c')
                cor_c2, err_c2, ed_2 = dynamic_codes_table_c2[c2]
                repeated+=1
            except KeyError:
                #print ('d')
                #return correct_barcodes
                cor_c2, err_c2, ed_2 = find_correct_barcode(c2, correct_barcodes[1])
                #print('d1')
                dynamic_codes_table_c2[c2] = cor_c2, err_c2, ed_2
                new+=1
            
            if ed_1+ed_2 == 0:
                #print('e')
                correct_instances += ((bin_rep.seq_len(c1) + bin_rep.seq_len(c2)) / 4)*len(grouped_ra[gene][seq])
            elif ed_1+ed_2 > 1:
                #print('f')
                continue    # Ignore codes that are too noisy in the error correction calculation
            else:
                try:
                    if ed_1 == 1:
                        #print('g')
                        error_table[err_c1] += len(grouped_ra[gene][seq])
                    elif ed_2 == 1:
                        #print('h')
                        error_table[err_c2] += len(grouped_ra[gene][seq])
                except TypeError:   # TODO: The 'N' in the codes create a key error. A good idea might be to just ignore them or even filter them completely.
                    #print('i')
                    pass
                except KeyError:
                    pass
        

    
    # convert to error rates    
    default_error_rate = 0.02
    err_rate = dict(zip(errors, [0.0] * len(errors)))
    if sum(error_table.values()) == 0:
        print('No errors were detected, using %f uniform error chance.' % (
            default_error_rate))
        err_rate = dict(zip(errors, [default_error_rate] * len(errors)))
    for k, v in error_table.items():
        try:
            err_rate[k] = v / (sum(n for err_type, n in error_table.items()
                               if err_type&0b111000 == k&0b111000) + correct_instances)
        except ZeroDivisionError:
            print('Warning: too few reads to estimate error rate for %r '
                  'setting default rate of %f' % (k, default_error_rate))
            err_rate[k] = default_error_rate
    print('total reads: ',str(tot),', ignored: ',str(ignored), ', new entries: ',str(new),', repeated entries: ',str(repeated))
    return err_rate

#deprecated
#def list_errors(code, correct_barcodes):
    """
    For a given code and a list of correct barcodes - find the correct barcode
    that is closest to code and return the list of errors that turned it into
    code. An error is a six bit int representing a two chr string of type "AG","CT", etc.
    """
    # find the closest correct barcode
#    min_dist = high_value
#    donor = 0
#    for cor_code in correct_barcodes:
#        hamm_d = hamming_dist_bin(code, cor_code)
#        if hamm_d < min_dist:
#            min_dist = hamm_d
#            donor = cor_code
#            if hamm_d <= max_ed:
#                break
    
#    if donor==0:
#        print('Error: no donor code was found to be closest. code = ', bin_rep.bin2str(code))
    # return the actual error
#    err_list = []
#    while code > 0:
#        if code&0b111 != donor&0b111:
#            err_list.append(bin_rep.ints2int([donor&0b111, code&0b111]))
#        code>>=3
#    return err_list