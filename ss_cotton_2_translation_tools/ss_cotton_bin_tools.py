# -*- coding: utf-8 -*-
"""
Created on Sat Feb  6 21:10:05 2021

@author: nanashi
"""

import ntpath
import codecs
import os, fnmatch
import numpy as np

func_sig_init_char = (b'\x2F\x86\x2F\x96\x2F\xA6\x2F\xB6'
                      b'\x2F\xC6\x2F\xD6\x4F\x22\x69\x43'
                      b'\x6D\x53\xD6\x27\xD0\x27\xE7\x07'
                      b'\x51\x95\xE5\x68\x5A\x12\xE4\x01')

func_sig_init_grp = (b'\x2F\x86\x2F\x96\x2F\xA6\x2F\xB6'
                     b'\x2F\xC6\x2F\xD6\x2F\xE6\x4F\x22'
                     b'\x7F\xEC\x69\x43\x1F\x54\x6D\x63'
                     b'\x6E\x73\xD6\x3F\x95\x75\xD1\x3F')

def find(pattern, path):
    result = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root, name))
    return result

def find_item(lst, string):
    for i in range(0, len(lst)):
        if lst[i].find(string) > -1:
            return i

def change_chr_spacing(bin_file, space):
    """
    Changes the character spacing in the bin file.

    Parameters
    ----------
    bin_file : string
        Absolute path to the bin file.
    space : int
        New spacing.

    Returns
    -------
    None.

    """
    with open(bin_file, 'rb') as ifile:
        bin_data = bytearray(ifile.read())
        
    func_pos = bin_data.find(func_sig_init_char)
    if func_pos == -1:
        raise ValueError('Function not found')
    data_pos = func_pos + 0x75
    bin_data[data_pos] = space
    
    with open(bin_file, 'wb') as ofile:
        ofile.write(bin_data)
        
def change_txt_speed(bin_file, speed):
    """
    Changes the text speed.

    Parameters
    ----------
    bin_file : string
        Absolute path to the bin file.
    speed : int
        New speed.

    Returns
    -------
    None.

    """
    with open(bin_file, 'rb') as ifile:
        bin_data = bytearray(ifile.read())
        
    func_pos = bin_data.find(func_sig_init_grp)
    if func_pos == -1:
        raise ValueError('Function not found')
    data_pos = func_pos + 0xAF
    bin_data[data_pos] = speed
    
    with open(bin_file, 'wb') as ofile:
        ofile.write(bin_data)

def update_sch_ptr_table(mf_folder):
    """
    Updates the sch reentry pointer positions from the VS*.bin file. The
    SCH.ptr file must be present in the folder.

    Parameters
    ----------
    mf_folder : string
        absolute path to the folder with MF section files.

    """
    working_dir = mf_folder
    
    start_pts = []
    cfile = find("*.SCH.info", working_dir)[0]
    with codecs.open(cfile, 'r', 'utf-8') as ifile:
        lines = ifile.read().split('\n')
        for j in range(0, len(lines)):
            if '#starta' in lines[j]:
                break
        for i in range(j, len(lines)):
            start_pts.append(i)
            if '#endz' in lines[i]:
                break
        for j in range(i, len(lines)):
            if '#start' in lines[j]:
                start_pts.append(j)
                
    ptr_lst = []
    cfile = find("*.SCH.ptr", working_dir)[0]
    with open(cfile, 'rb') as ifile:
        ptr_data = ifile.read()
        i = 0
        size = int(len(ptr_data)/4)
        for _ in range(0, size):
            ptr_lst.append(int().from_bytes(ptr_data[i:i+4], 'big'))
            i += 4
                
    if len(ptr_lst) != len(start_pts):
        raise ValueError('Mismatched data')
            
    cfile = find("VS*.bin", working_dir)[0]
    with open(cfile, 'rb') as ifile:
        bin_data = bytearray(ifile.read())
            
    for i in range(0, len(ptr_lst)):
        new = start_pts[i].to_bytes(2, 'big')
        bin_data[ptr_lst[i]:ptr_lst[i]+2] = new
        
    with open(cfile, 'wb') as ofile:
        ofile.write(bin_data)

def gen_sch_ptr_table(mf_folder):
    """
    Extracts the sch reentry pointer positions from the VS*.bin file by
    analysising the sch.info file. These pointers are used to determine
    where to re-enter the sch table after an #exit command occured.

    Parameters
    ----------
    mf_folder : string
        absolute path to the folder with MF section files.

    """
    working_dir = mf_folder
    start_pts = []
    
    cfile = find("*.SCH.info", working_dir)[0]
    
    folder = ntpath.dirname(cfile)+'/'
    base_name = ntpath.basename(cfile).split(".")[0]
    
    with codecs.open(cfile, 'r', 'utf-8') as ifile:
        lines = ifile.read().split('\n')
        for j in range(0, len(lines)):
            if '#starta' in lines[j]:
                break
        for i in range(j, len(lines)):
            start_pts.append(i)
            if '#endz' in lines[i]:
                break
        for j in range(i, len(lines)):
            if '#start' in lines[j]:
                start_pts.append(j)
                
    cfile = find("*.SIF", working_dir)[0]
    with open(cfile, 'rb') as ifile:
        search = ifile.read()
            
    sch_size = int().from_bytes(search[0:2], 'big')
    tlm_size = int().from_bytes(search[2:4], 'big')
    san_size = int().from_bytes(search[4:6], 'big')
            
    cfile = find("VS*.bin", working_dir)[0]
    with open(cfile, 'rb') as ifile:
        bin_data = ifile.read()
        
    end_pos = bin_data.find(search)
    pos = end_pos - (sch_size + tlm_size + san_size)*2
    
    start_pts = np.array(start_pts)
    sort_idx = np.argsort(start_pts)
    unsort_idx = np.argsort(sort_idx)
    start_pts = start_pts[sort_idx].tolist()
    ptr_lst = []
    start_ptr = start_pts.pop(0).to_bytes(2, 'big')
    while pos < end_pos:
        elem = bin_data[pos:pos+2]
        if elem == start_ptr:
            ptr_lst.append(pos)
            try:
                start_ptr = start_pts.pop(0).to_bytes(2, 'big')
            except IndexError:
                break
        pos += 2
            
    ptr_lst = np.array(ptr_lst)
    ptr_lst = ptr_lst[unsort_idx].tolist()
    with open(folder+base_name+'.SCH.ptr', 'wb') as outfile:
        for ptr in ptr_lst:
            outfile.write(ptr.to_bytes(4, 'big'))
            
def update_san_ptr_table(mf_folder):
    """
    Updates the san entry pointer positions from the VS*.bin file. The
    SAN.ptr file must be present in the folder.

    Parameters
    ----------
    mf_folder : string
        absolute path to the folder with MF section files.

    """
    working_dir = mf_folder
    
    cfile = find("*.SCH.info", working_dir)[0]
    with codecs.open(cfile, 'r', 'utf-8') as ifile:
        sch_data = ifile.read().split('\n')
    
    cfile = find("*.SAN.info", working_dir)[0]
    sch_ptr_lst = []
    with open(cfile, 'r') as ifile:
        lines = ifile.read().split('\n')
    
    while lines[-1] == '':
        lines.pop(-1)
        
    for line in lines:
        line = line.split(';')
        item = min([item.split(',')[0] for item in line])
        try:
            sch_ptr = find_item(sch_data, item)
            sch_ptr_lst.append(sch_ptr)
        except ValueError:
            pass
    
    ptr_lst = []
    cfile = find("*.SAN.ptr", working_dir)[0]
    with open(cfile, 'rb') as ifile:
        ptr_data = ifile.read()
        i = 0
        size = int(len(ptr_data)/4)
        for _ in range(0, size):
            ptr_lst.append(int().from_bytes(ptr_data[i:i+4], 'big'))
            i += 4
                
    if len(ptr_lst) != len(sch_ptr_lst):
        raise ValueError('Mismatched data')
                    
            
    cfile = find("VS*.bin", working_dir)[0]
    with open(cfile, 'rb') as ifile:
        bin_data = bytearray(ifile.read())
            
    for i in range(0, len(ptr_lst)):
        new = sch_ptr_lst[i].to_bytes(2, 'big')
        bin_data[ptr_lst[i]:ptr_lst[i]+2] = new
        
    with open(cfile, 'wb') as ofile:
        ofile.write(bin_data)
            
def gen_san_ptr_table(mf_folder):
    """
    Extracts the san entry pointer positions from the VS*.bin file by
    analysising the san.info file. These pointers are used to determine
    where to enter the sch table for animations.

    Parameters
    ----------
    mf_folder : string
        absolute path to the folder with MF section files.

    """
    working_dir = mf_folder
    
    cfile = find("*.SCH.info", working_dir)[0]
    with codecs.open(cfile, 'r', 'utf-8') as ifile:
        sch_data = ifile.read().split('\n')
    while sch_data[-1] == '':
        sch_data.pop(-1)
    
    cfile = find("*.SAN.info", working_dir)[0]
    
    folder = ntpath.dirname(cfile)+'/'
    base_name = ntpath.basename(cfile).split(".")[0]
    
    sch_ptr_lst = []
    with open(cfile, 'r') as ifile:
        lines = ifile.read().split('\n')
    while lines[-1] == '':
        lines.pop(-1)
        
    for line in lines:
        line = line.split(';')
        item = min([item.split(',')[0] for item in line])
        try:
            sch_ptr = find_item(sch_data, item)
            sch_ptr_lst.append(sch_ptr)
        except ValueError:
            pass
                    
    cfile = find("*.SIF", working_dir)[0]
    with open(cfile, 'rb') as ifile:
        search = ifile.read()
        
    sch_size = int().from_bytes(search[0:2], 'big')
    tlm_size = int().from_bytes(search[2:4], 'big')
    san_size = int().from_bytes(search[4:6], 'big')
            
    cfile = find("VS*.bin", working_dir)[0]
    with open(cfile, 'rb') as ifile:
        bin_data = ifile.read()
        
    end_pos = bin_data.find(search)
    pos = end_pos - (sch_size + tlm_size + san_size)*2
    
    sch_ptr_lst = np.array(sch_ptr_lst)
    sort_idx = np.argsort(sch_ptr_lst)
    unsort_idx = np.argsort(sort_idx)
    sch_ptr_lst = sch_ptr_lst[sort_idx].tolist()
    ptr_lst = []
    sch_ptr = sch_ptr_lst.pop(0).to_bytes(2, 'big')
    while pos < end_pos:
        elem = bin_data[pos:pos+2]
        if elem == sch_ptr:
            ptr_lst.append(pos)
            try:
                while sch_ptr == sch_ptr_lst[0].to_bytes(2, 'big'):
                    ptr_lst.append(pos)
                    sch_ptr = sch_ptr_lst.pop(0).to_bytes(2, 'big')
                sch_ptr = sch_ptr_lst.pop(0).to_bytes(2, 'big')
            except IndexError:
                pass
        pos += 2
            
    ptr_lst = np.array(ptr_lst)
    ptr_lst = ptr_lst[unsort_idx].tolist()
    with open(folder+base_name+'.SAN.ptr', 'wb') as outfile:
        for ptr in ptr_lst:
            outfile.write(ptr.to_bytes(4, 'big'))
