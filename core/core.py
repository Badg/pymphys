import pandas as pd
import numpy as np

def remove_duplicates(lst):
    """ Removes duplicates in a list, preserving list order."""
    unique = []
    for ii in lst:
        if ii not in unique:
            unique.append(ii)
    return unique

def detect_broken_pattern(iterable, threshold=1):
    """ Examines a 1d iterable for pattern discontinuities.
    
    Note: will always return false for lists of singular length.  Will return
    true for lists of length n=2 IFF the difference between the two items is
    greater than 5% of the first item.
    
    + "iterable" is the object to examine.
    + "threshold" is the allowable percentage deviation from trimmed midrange. 
      Higher values result in looser patterns and hence, rarer deviation 
      detectance.
    
    Returns True if a discontinuity is found, false otherwise.
    """
    from statistics import mean, stdev

    # Sets sensitivity of stdev:avg ratio
    statRat = 10000
    # Sets sensitivity of maxerror:spread ratio
    errRat = 10
    # Sets sensitivity of deltas:spread ratio
    deltRat = 10
    
    n = len(iterable)
    
    # Catch very short iterables immediately (can't establish a pattern 
    # without a minimum of three items)
    if n <= 2: return False
    # elif len(iterable) == 2:
        # if iterable[0] == 0 and iterable[1] == 0:
            # return False
        # elif iterable[0] == 0 or iterable[1] == 0:
            # if 1 >= permissible2Delta: return True
            # else: return False
        # else:
            # deltas = iterable[1] - iterable[0]
            # if abs(deltas / iterable[0]) >= permissible2Delta: return True
            # else: return False
    
    itmax = max(iterable)
    itmin = min(iterable)
    
    spread = itmax - itmin
    # Ignore when spread is less than the average of the extremes.  Aka, you 
    # can jump one "field length" but not more.
    if spread < (itmax + itmin) / 2 * 2: return False
    # elif max(errors) / spread >= errRat: return True
    
    # Create a temporary copy and delete the min and max entries (partially-
    # trimmed midrange)
    temp = iterable.copy()
    del temp[temp.index(max(iterable))]
    del temp[temp.index(min(iterable))]
    midmean = mean(temp)
    midsd = stdev(temp, midmean)
    
    fullmean = mean(iterable)
    fullsd = stdev(iterable, fullmean)
    
    # If the mean of the whole sample is several standard deviations outside 
    # the trimmed mean, then there's probably an outlier.
    if midsd and abs((fullmean - midmean) / midsd) >= 10: return True

    return False
    