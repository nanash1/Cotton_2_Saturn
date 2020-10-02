# -*- coding: utf-8 -*-
"""
Created on Fri Oct  2 21:41:07 2020

@author: nanashi
"""

use_fallback = False

try:
    import ss_cotton_lz00
except ModuleNotFoundError:
    use_fallback = True
    
if use_fallback:
    def _find_match(labuff, match, check_repeats):
        
        match_len = len(match)
        max_len = len(labuff)
        
        if labuff[0:match_len] == match:
            i = match_len
        else:
            return 0
             
        if check_repeats:
            j = 0
            while i < max_len:
                if labuff[i] == match[j]:
                    i += 1
                    j += 1
                else:
                    break
                
                if j > match_len - 1:
                    j = 0
        
        return i
    
    def find_best_match(labuff, sbuff):
        sbuff_len = len(sbuff)
        pos = 0
        max_match_len = 0
        match = ("seq", 0, 0)
        while pos < sbuff_len:
            
            for i in range(0, pos+1):
                check_repeats = pos == i
                match_len = _find_match(labuff, sbuff[sbuff_len-1-pos:sbuff_len-pos+i], check_repeats)
                
                if match_len > max_match_len:
                    match = ("seq", pos+1, match_len)
                    max_match_len = match_len
                elif match_len == 0:
                    break
            pos += 1
            
        return match
else:
    find_best_match = ss_cotton_lz00.find_best_match