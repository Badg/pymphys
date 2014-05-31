import numpy as np
import pandas as pd

def mphtxt_prep_headers(txtFile):
    """ Extracts the header from a mphtxt file, generates column names, etc.

    Does some reasonably intelligent pre-processing of the txt file and then 
    generates an output tuple including the headers (for logging), the numbers 
    of header lines (to skip during pandas conversion), the column specs (for 
    pandas import), the column names, etc.  See below.
    
    Inputs:
    -------
    + <txtFilename> is the path to the COMSOL text file.  If left blank, it
      will query the user.
    + <infer_lines> is the number of lines to use to infer the column widths.
    + <basename> is the "root" name to apply to all of the set.  If left 
      blank, it will be inferred from <txtFilename>.  As an example of this 
      inference, "foo.txt" would become a <basename> of "foo", which would 
      then turn into files like foo_log.txt or foo_raw.h5.  Will append 
      generic fieldnames to <fields> if the number of <fields> is less than
      the number of detected columns.
    
    Outputs (as tuple, in this order):
    + <basename>, a str of the (inferred or otherwise) base name
    + <headerlines>, a list of the int line numbers of headers to skip parsing
    + <headers>, a list (the elements are str and include \n) of strs
    + <fields>, a list of strs for column labels
    + <colspecs>, a list of tuples of column start -> ends in panda form (ex:
      [(0,3),(4,7)], etc)    
    """    
    # Localglobal declarations
    import re
    
    fields = None
    notDoGroup = None
    group = None
    groupname = None
    inrow = 'dummy'
    txtheader = ""
    headerlines = []
    headers = []
    colspec = []
    ii = -1
#    leakCount = 0
    header = True
    # Parse each line until readline returns '', signalling end of file
    while inrow: 
        # Always, always increment the row count, regardless of behavior
        ii += 1
        
        inrow = txtFile.readline()
        # Skip blank rows
        if not inrow or not inrow[0]: continue 
        
        # Look to see if it's a header
        header, payload = detect_columns(inrow)
        
        if header:
            # It's a header row
            headerlines.append(ii)
            if isinstance(payload, str):
                # Immediately pass the row to the header variable
                headers.append(payload)
                # We're done here.
                continue

            # Now we definitely have fields.  Make them lower than an
            # alcoholic in a clown suit pissing off the side of the
            # golden gate bridge.  And uniquer, too.
            if isinstance(payload, list):
                fields = remove_duplicates([fld.lower() for fld in payload])
        else:
            break
#            leakCount += 1

    # Now we should know how many rows of headers we have and what the 
    # fields are called.
    return headerlines, headers, fields

def mphtxt_detect_colspec(txtFile, infer_lines=50):
    # Since it appears that pandas doesn't do a good job of 
    # automagic column detection, let's go ahead and do that here.
    # All headers have been parsed.  This should be data.
    # Note that the file pointer must already be advanced to the start of the
    # data for this to work.
    from statistics import mean
    inrow = 'dummy'
    ii = -1
    widths = []

    while inrow and ii <= infer_lines: 
        # Always, always increment the row count, regardless of behavior
        ii += 1
        
        inrow = txtFile.readline()

        # Get the raw column widths
        thiswd = detect_columns(inrow, returnwidths=True)
        # Replace the irregular short width of the last column with 
        # the max colwidth seen in the row (including the last column)
        thiswd[len(thiswd)-1] = max(thiswd)
        widths.append(thiswd)
        continue

    # Let's examine each set of widths by transposing them first:
    widths = zip(*widths)
    cols = []
    # Now iterate on each field column
    for field in widths:
        # Append the rounded average length to the cols list
        colavg = mean(field)
        cols.append(int(round(colavg)))
        
    # Cols now contains the calculated average column widths. The ends will be
    # width - 1... fuckit, anyway point is now we're going to generate the
    # colspec for pandas read_fwf
    colspecs = []
    offset = -1
    for it in cols:
        colstarts = offset + 1
        offset += it
        colends = offset
        colspecs.append([colstarts, colends])

    return colspecs
        
def pad_fields(fields, colspecs):
    # Test that there are enough fields for the value
    if len(fields) < len(colspecs):
        import re
        # If there aren't enough fields, inflate fields accordingly
        for ii in range(1, len(colspecs) - len(fields) + 1):
            # Fields is too short.  Add a generic name.
            # Look for a previously-defined generic [field]
            if re.match(r"field\d+", fields[-1]): 
                # Match the number of the [field] (ex field1 -> 1)
                m = re.search(r"\d+", fields[-1]) 
                # Get the number
                useNum = int(m.group(0)) + 1 
                # Now add the incremented generic [field] to fields
                fields.append("field" + str(useNum)) 
            # no field1, so that's probably a good place to start
            else: 
                # Append field1 if fields exists, or create it
                try:
                    fields.append("field1")
                except AttributeError:
                    fields = ["field1"]

def spacetxt_to_panda(txtFilename, headerlines, fields, colspecs):
    """ Convert the body of a space-delimited .mphtxt file into a panda df.

    Relies upon prior pre-processing of the data file to create a panda 
    dataframe (pd.df) of the data.  Returns a pd.df.  Writing a function for 
    this is a bit silly right now, but might be useful down the road if more 
    advanced processing is required.
    
    + <txtFilename> is the path to the COMSOL text file.
    + <headerlines> is a list of lines to skip
    + <fields> is a list of the name of the fields
    + <colspecs> is a list of tuples of column start -> ends in panda form (ex:
      [(0,3),(4,7)], etc)    
    
    Returns a pandas dataframe.
    """
    # Localglobal declarations
    # (none)

    df = pd.read_fwf(txtFilename, skiprows=headerlines, names=fields, 
                     colspecs=colspecs)
    return df

def remove_duplicates(lst):
    """ Removes duplicates in a list, preserving list order."""
    unique = []
    for ii in lst:
        if ii not in unique:
            unique.append(ii)
    return unique

def dump_hdf5(h5Filename, dataframe):
    """ Dumps a pandas dataframe to the specified file.
    
    """
    store = pd.HDFStore(h5Filename)
    store.put('df', dataframe)

def detect_columns(str, tags={"#":True, "%":True}, columnThreshold = 7, 
    returnwidths=False):
    """ Detects columns in a space-delineated row.
    
    Assesses a string against some tags to determine if it is an information
    header, or a column header, or a data column.  tags are single-character 
    fields that represent a header row. columnThreshold is the sensitivity of 
    column detection in headers.  Higher is stricter matching of column text 
    widths. Currently assumes roughly equal column width, determined by the 
    threshold arg. Should really be reconfigured to examine multiple lines.
    
    + "str" is the string to examine.
    + "tags" is an optional dictionary of what tag determines a header row.
    + "columnThreshold" is the sensitivity of column detection to automatically
    discover fields.
    + "returnwidths", if true, will tell the function to only return the widths
      of the respective fields.
    
    Case 1: information header.  Returns True, String.
    Case 2: column header.  Returns True, list of strings.
    Case 3: data row.  Returns false, list of data entries.
    """
    # import required modules
    import re    
    from statistics import mean, stdev
    
    # Assume not a header
    header = False
    
    # First check if the first character of the str matches a header tag
    if (str[0] in tags) and tags[str[0]]:
        # Remove any tags
        str = str[1:]
        header = True
    
    # strip all remaining whitespace from the string.
    # For now, the deliverable is everything except whitespace and header tags.
    str = str.lstrip().rstrip()
    payload = str 
    
    # Use regex to preprocess the str.
    # find anything that looks like [text][whitespace], keeping both together
    splitstr = re.findall(r'(\S+\s+)', str) 
    # Note that this will not match the last column, which will not contain 
    # any whitespace, so it is unnecessary to strip it.
    
    numStr = len(splitstr)
    
    # prefilter anything that's empty
    if numStr > 0: 
        # look at each word+whitespace combo
        for chunk in splitstr: 
            # Replace the actual column texts with their lengths
            try:
                lengths.append(len(chunk)) 
            except UnboundLocalError:
                # If it's the first time around the loop, declare it
                lengths = [len(chunk)] 
        
        # Get the mean column length
        colMean = mean(lengths) 
        
        # Automagically detect columns
        # If the deviations in length are small compared to the average length
        devComp = numStr > 1 and colMean / stdev(lengths) > columnThreshold 
        # Comparator for absolute size
        absComp = True 
        # Comparator for whitespace size
        whiteComp = False 
        
        # This should catch straddling numbers, but not +/- 1.  In other words,
        # if 1 or more columns are off by exactly 1 in the same direction... 
        identityThreshold = 1 / numStr 
        for ii, length in enumerate(lengths):
            # Or if it's really damn close across the board, and there are 
            # more than two strings
            absComp = absComp and \
                      (abs(length - colMean) <= identityThreshold) and \
                      numStr > 2 
            # Checks for a minimum of two whitespace characters at the end
            whiteComp = whiteComp or length - len(splitstr[ii].rstrip()) >= 2 
        if devComp or (absComp and whiteComp): 
            # This should be more robust than a simple comparison, look for equal length columns, etc etc
            payload = str.split()
            
            # Try to cast it as a float, which would make it data
            try:
                for ii, package in enumerate(payload):
                    payload[ii] = float(package)
            # If we fail to make it into a float, it must be a header
            except ValueError:
                header = True
    # It's only one column long and not a header
    elif not header: 
        try:
            # Try to cast it as a float -- maybe it's data!
            payload = float(payload) 
        except ValueError:
            # If not, assume it's a header and move on.
            header = True 
    
    # If we're just going to return the widths...
    if returnwidths:
        # Create a splitstr so we can get the last column's length
        tempstr = str.split()
        # Get the last column's lengths, even though it's irregular
        lastlength = len(tempstr[len(tempstr)-1])
        # Add it ^ to the lengths list and return
        lengths.append(lastlength)
        return lengths
    else: 
        return header, payload

def detect_headers(str, tags={"#":True, "%":True}):
    """ Detects header tags in a row.
    
    Assesses a string against some tags to determine if it is a header / 
    comment row.
    
    + "str" is the string to examine.
    + "tags" is an optional dictionary of what tag determines a header row.
    
    Returns true if header tag is present.
    """
    
    # Remove any whitespace
    str = str.lstrip()
    str = str.split(' ', 1)[0]
    
    # If the first split of the str matches a header tag
    # Or the first character of the first split matches one
    if str and \
       ((str in tags and tags[str]) or \
       (str[0] in tags and tags[str[0]])):
        # Remove any tags
        str = str[1:]
        return True
    
def detect_TL(str):
    """ Detects a toplevel (non-indent, non-blank) line.
    
    + "str" is the line string
    + "indent" is the optional indent level / character (by convention, should 
    be four spaces)
    
    Returns true if it's a toplevel key, false if not.
    """
    
    # If the beginning of the line contains whitespace, it's not TL
    if str.lstrip() != str: return False
    
    # If the line is blank, it's not TL (wait, I think this is caught above)
    elif str == "\n": return False
    
    # If it's literally empty, it's not TL key
    elif str == "": return False
    
    else: return True

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
    