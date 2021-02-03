# -*- coding: utf-8 -*-
"""
Created on Tue Jun 16 17:06:50 2020

@author: nanashi
"""

import ntpath
import codecs
import os, fnmatch
from ss_cotton_2_translation_tools import ss_cotton_image_tools as ss_img_tools

def mf_compose(mf_folder):
    '''
    Composes MF file sections into a MF file. Requires the *.MF.info file to be
    in the same folder.
    
    Known sections are:
        *.SCH       Contains the sequence in which images are loaded
        *.SAN       Unknown, could be related to animations
        *.SIF       Contains the number of image load instructions in *.SCH
        *.SPL       Contains color palettes for images in *.SPT
        *.SPT       Contains all images
        *.SCP       Contains tiles
        *.AIF       PCM samples
    
    Parameters
    ----------
    mf_folder : string
        absolute path to the folder with MF section files.
    '''
    def find(pattern, path):
        result = []
        for root, dirs, files in os.walk(path):
            for name in files:
                if fnmatch.fnmatch(name, pattern):
                    result.append(os.path.join(root, name))
        return result
    
    def write_section(outfile, section, working_dir, terminator=b'#0`\xe9'):    # no idea what the terminator does
        current_file = find("*."+section, working_dir)[0]    
        current_section = ntpath.basename(current_file)
        data_size = os.path.getsize(current_file)
    
        padding = data_size % 4
        if padding > 0:
            padding = 4 - padding
        section_size = 32 + data_size + padding
        
        '''
        write 32 byte header
        '''
        out_file.write(section_size.to_bytes(4, 'big'))
        out_file.write(bytes(current_section.ljust(16, '\x00'), 'ascii'))
        out_file.write(data_size.to_bytes(4, 'big'))
        out_file.write(terminator)
        out_file.write(bytearray(4))
        
        '''
        write data
        '''
        with open(current_file, 'rb') as in_file:
            out_file.write(in_file.read())
        
        if padding > 0:                                                         # sometimes padding is required to align the data
            out_file.write(bytearray(padding))    
            
    
    working_dir = mf_folder
    mf_info_file = find("*.MF.info", working_dir)[0]
    with open(mf_info_file, "r") as in_file:
        sections = in_file.readlines()
    
    mf_name = sections[0][0:7]
    with open(working_dir+"/"+mf_name+".MF", 'wb') as out_file:
        for section in sections:
            section = section.strip('\r\n').split(",")
            write_section(out_file, section[0][-3:], working_dir, int(section[1]).to_bytes(4, 'big'))
        
        out_file.write(b'\xff\xff\xff\xff')

def mf_decompose(mf_file):
    '''
    Decomposes MF files into its components for editing.
    
    Known sections are:
        *.SCH       Contains the sequence in which images are loaded
        *.SAN       Unknown, could be related to animations
        *.SIF       Contains the number of image load instructions in *.SCH
        *.SPL       Contains color palettes for images in *.SPT
        *.SPT       Contains all images
        *.SCP       Contains tiles
        *.AIF       PCM samples

    Parameters
    ----------
    mf_file : string
        MF file with absolute path.

    '''
    working_dir = ntpath.dirname(mf_file)
    
    with open(mf_file, 'rb') as in_file:
        with open(mf_file+".info", "w") as info_file:
            next_section = int.from_bytes(in_file.read(4), byteorder="big")
            
            while next_section > 0 and next_section != 4294967295:
                
                section_start = in_file.tell() - 4
            
                section_name = str(in_file.read(16)).strip(str(b'\x00'))
                section_size = int.from_bytes(in_file.read(4), byteorder="big")
                terminator = in_file.read(4)
                
                info_file.write(section_name+","+str(int.from_bytes(terminator, 'big'))+"\n")
                
                in_file.seek(4, 1)
                
                with open(working_dir+"/"+section_name, 'wb') as out_file:
                    data = in_file.read(section_size)
                    out_file.write(data)
                    
                in_file.seek(section_start+next_section, 0)
                next_section = int.from_bytes(in_file.read(4), byteorder="big")
                
                if next_section == "":
                    raise Exception("unexpected end of file")
                    break

def spt_gen_info(spt_file):
    """
    Generates meta info file for the content of the SPT file. The info file
    contains the follwing informations for each image in the file
        - sch identifier     symbolic name that is used in the sch info meta file
        - file name          file name of the image in the folder
        - plt identifer      internal identifier used by the game
        - width              image pixel width
        - height             image pixel height
        - bpp                bits per pixel
        
    Note: The sch identifier may be changed for a better symbolic name.

    Parameters
    ----------
    spt_file : string
        spt file with absolute path.

    """
    working_dir = ntpath.dirname(spt_file)
    
    base_name = ntpath.basename(spt_file).split(".")[0]
    
    with open(working_dir+"/"+base_name+".SPT.info", 'w') as meta_file:
        cntr = 0
        with open(spt_file, 'rb') as fspt_file:
            ident = fspt_file.read(4)
            
            while ident:
                
                '''
                generate image number
                '''
                num_str = str(cntr)
                leading_zeros = "0"*(4 - len(num_str))
                num_str = leading_zeros + num_str
                
                '''
                generate meta info
                '''
                ident = int.from_bytes(ident, byteorder="big")
                width = int.from_bytes(fspt_file.read(2), byteorder="big")
                height = int.from_bytes(fspt_file.read(2), byteorder="big")
                size = int.from_bytes(fspt_file.read(4), byteorder="big")
                
                fspt_file.seek(20,1)
                try:
                    format_str = fspt_file.read(4).decode("ascii")
                except UnicodeDecodeError:
                    format_str = "0000"
                name = num_str +"_" + base_name
                
                if format_str == "LZ00":
                    img_name = name+".lz00"
                    uncomp_size = int.from_bytes(fspt_file.read(4), byteorder="big")
                    fspt_file.seek(-8,1)
                else:
                    img_name = name+".bin"
                    uncomp_size = size
                    fspt_file.seek(-4,1)
                    
                bpp = int((8*uncomp_size)/(width*height))
                    
                '''
                write info
                '''
                meta_string = num_str+","+img_name+","+str(ident)+","+str(width)+","+str(height)+","+str(bpp)
                meta_file.write(meta_string+"\n")
                
                fspt_file.seek(size, 1)
                
                ident = fspt_file.read(4)
                cntr += 1
                
def txt2sch(txt_file, template):
    """
    Generates a template file from a text file. Template files can be used
    to facilitate the generation of custom sch info meta files

    Parameters
    ----------
    txt_file : string
        text file with absolute path.
    template : tuple
        tuple that contains the default values for the image loading instructions.

    Returns
    -------
    None.

    """
    working_dir = ntpath.dirname(txt_file)
    base_name = ntpath.basename(txt_file).split(".")[0]
    
    lut = {',':'#comma','\n':'\\n'}
    
    with codecs.open(txt_file, 'r', 'utf-8') as txt_file:
        text = txt_file.read()
        
    braket_start = True
    with open(working_dir+'/'+base_name+'.sch.temp', 'w') as temp_file:
        for char in text:
            if char in lut:
                char = lut[char]
            if char == '\r':
                continue
            if char == '"':
                if braket_start:
                    char = '_"'
                    braket_start = False
                else:
                    char = '"_'
                    braket_start = True
                    
            for elem in template:
                char += ','+str(elem)
            
            temp_file.write(char+'\n')
        
    
            
def sch_compose(sch_info_file):
    """
    Composes the sch file from the info meta file.
    
    Note: The first entry for each element of the meta file is the symbolic 
    name that is used in the spt.info file.

    Parameters
    ----------
    sch_info_file : string
        sch.info file with absolute path.

    """
    working_dir = ntpath.dirname(sch_info_file)
    base_name = ntpath.basename(sch_info_file).split(".")[0]
    spt_info_file = working_dir+"/"+base_name+".SPT.info"
    spt_file = working_dir+"/"+base_name+".SPT"
    sch_info_file = working_dir+"/"+base_name+".SCH.info"
    sch_file = working_dir+"/"+base_name+".SCH"
    
    '''
    get image address
    '''
    addr_list = []
    with open(spt_file, 'rb') as fspt_file:
        
        while True:
            
            addr_list.append(fspt_file.tell())
            
            fspt_file.seek(8,1)
            bsize = fspt_file.read(4)
            if not bsize:
                break
            size = int.from_bytes(bsize, byteorder="big")
            
            fspt_file.seek(20+size,1)
            
    addr_list.pop(-1)
    
    '''
    read command list
    '''
    command_dict = {}
    with codecs.open(spt_info_file, 'r', 'utf-8') as in_file:
        for line in in_file:
            line = line.split(",")
            command_dict[line[0]] = addr_list.pop(0)
    
    def line2bin(line):
        try:
            rtn = int(command_dict[line[0]]).to_bytes(4, 'big')
        except KeyError:
            rtn = int(command_dict["A"]).to_bytes(4, 'big')
        for i in range(1,9):
            rtn += int(line[i]).to_bytes(2, 'big')
        return rtn
            
    with codecs.open(sch_info_file, 'r', 'utf-8') as in_file:
        
        '''
        generate binary command data
        '''
        line_cntr = 0
        commands_bin = bytes()
        for line in in_file:
            
            line = line.split(",")
            line[-1] = line[-1].strip('\r\n')
            line_cntr += 1
            
            commands_bin += line2bin(line)
        
        '''
        generate pointer table
        '''
        ptable_bin = bytes()
        current_pointer = (line_cntr + 1) * 4
        while line_cntr:
            ptable_bin += current_pointer.to_bytes(4, 'big')
            current_pointer += 20
            line_cntr -= 1
        ptable_bin += b'\xff\xff\xff\xff'
        
    with open(sch_file, 'wb') as out_file:
        out_file.write(ptable_bin)
        out_file.write(commands_bin)  
                
def sch_decompose(sch_file):
    """
    The file starts with a pointer table to the entries. Each pointer is 32 bit
    long. The pointer table is terminated with 0xffffffff.

    After the pointer table the image loading instructions begin. Each
    instruction is 20 bytes long and structured like this:
        32 bit, relative pointer to the image in the *.SPT file
        16 bit, CMDLINK instruction when distorted sprite, else palette index
        16 bit, x position when distorted sprite, else nothing
        16 bit, y position when distorted sprite, else nothing
        16 bit, unknown
        16 bit, unknown
        16 bit, unknown
        16 bit, unknown

    Parameters
    ----------
    sch_file : string
         sch file with absolute path.

    """
    
    def _spt_find_num(spt_file, addr):
        with open(spt_file, 'rb') as fspt_file:
            
            cntr = 0
            while True:
                
                if addr == fspt_file.tell():
                    return cntr
                
                fspt_file.seek(8,1)
                bsize = fspt_file.read(4)
                if not bsize:
                    return -1
                size = int.from_bytes(bsize, byteorder="big")
                
                fspt_file.seek(20+size,1)
                cntr += 1
    
    working_dir = ntpath.dirname(sch_file)
    base_name = ntpath.basename(sch_file).split(".")[0]
    
    spt_info_file = working_dir+"/"+base_name+".SPT.info"
    spt_file = working_dir+"/"+base_name+".SPT"
    sch_info_file = working_dir+"/"+base_name+".SCH.info"
    
    '''
    read spt file meta informations
    '''
    img_list = []
    with codecs.open(spt_info_file, 'r', 'utf-8') as in_file:
        for line in in_file:
            line = line.split(",")
            img_list.append(line[0])
        
    '''
    generate command list
    '''
    with codecs.open(sch_info_file, 'w', 'utf-8') as out_file:
        with open(sch_file, 'rb') as in_file:
            '''
            read pointer table
            '''
            cmd_pointer = int.from_bytes(in_file.read(4), byteorder="big")
            
            while cmd_pointer != 4294967295:
                ptable_pos = in_file.tell()
                
                in_file.seek(cmd_pointer, 0)
                img_addr = int.from_bytes(in_file.read(4), byteorder="big")
                
                img_num = _spt_find_num(spt_file, img_addr)
                
                cmd_ident = img_list[img_num]
                
                cmd_args = []
                for i in range(0,8):
                    cmd_arg = int.from_bytes(in_file.read(2), byteorder="big")
                    cmd_args.append(cmd_arg)
                    
                line = cmd_ident
                for cmd_arg in cmd_args:
                    line += ","+str(cmd_arg)
                out_file.write(line+"\n")
                
                in_file.seek(ptable_pos, 0)
                cmd_pointer = int.from_bytes(in_file.read(4), byteorder="big")
                
def spt_compose(spt_info_file):
    """
    Composes the SPT file from an info meta file. All files that are listed
    in the meta file must be present in the same folder

    Parameters
    ----------
    spt_info_file : string
        spt file with absolute path.

    Returns
    -------
    None.

    """
    working_dir = ntpath.dirname(spt_info_file)
    base_name = ntpath.basename(spt_info_file).split(".")[0]
    
    with codecs.open(spt_info_file, 'r', 'utf-8') as fsch_info:
        images = fsch_info.readlines()
        
    with open(working_dir+"/"+base_name+".SPT", "wb") as spt_file:
        for img in images:
            img = img.split(",")
            spt_file.write(int(img[2]).to_bytes(4, 'big'))
            spt_file.write(int(img[3]).to_bytes(2, 'big'))
            spt_file.write(int(img[4]).to_bytes(2, 'big'))
            
            with open(working_dir+"/"+img[1], "rb") as fimg:
                image_data = fimg.read()
                
            spt_file.write(len(image_data).to_bytes(4, 'big'))
            padding = bytes(b'\x00')*20
            spt_file.write(padding)
            spt_file.write(image_data)

def spt_decompose(spt_file, lz2png=False):
    """
    Decomposes a spt file into its image components. Known image types are
        Type               Extension        Comment
        tile maps          *.tlm            Tile maps without the tiles. Tiles are stored in *.SCP
        compressed images  *.lz00           Compressed images can be decompressed with the "ss_img_tools.decode" function
        images             *.bin            Raw binary image. Color tables are contained in the *.PLT file. 
                                            Use "ss_img_tools.spt2png" to convert to png

    Parameters
    ----------
    spt_file : string
        spt file with absolute path.
    lz2png : bool, optional
        When true lz00 compressed images are decompressed to png. 
        The default is False.

    Returns
    -------
    None.

    """
    
    working_dir = ntpath.dirname(spt_file)
    
    base_name = ntpath.basename(spt_file).split(".")[0]
    
    cntr = 0
    with open(spt_file, 'rb') as spt_file:
        ident = spt_file.read(4)
        
        while ident:
            '''
            read header
            '''
            img_addr = spt_file.tell() - 4
            ident = int.from_bytes(ident, byteorder="big")
            width = int.from_bytes(spt_file.read(2), byteorder="big")
            height = int.from_bytes(spt_file.read(2), byteorder="big")
            size = int.from_bytes(spt_file.read(4), byteorder="big")
            spt_file.seek(20,1)
            try:
                format_str = spt_file.read(4).decode("ascii")
            except UnicodeDecodeError:
                format_str = "0000"
            
            name = str(cntr)
            leading_zeros = "0"*(4 - len(name))
            name = leading_zeros + name +"_" + base_name
            compressed = False
            tile_map = False
            
            if format_str == "LZ00":
                img_name = name+".lz00"
                uncomp_size = int.from_bytes(spt_file.read(4), byteorder="big")
                spt_file.seek(-8,1)
                compressed = True
            else:
                img_name = name+".bin"
                uncomp_size = size
                spt_file.seek(-4,1)
                
            bpp = int((8*uncomp_size)/(width*height))
            
            if bpp == 0:
                img_name = name+".tlm"
                tile_map = True
            
            '''
            search palette
            '''
            if not tile_map:
                img_cntr = 0
                pimage = 0
                plt_addr = -1
                with open(working_dir+"/"+base_name+".SCH", "rb") as sch_file:
                    '''
                    read header
                    '''
                    pimage = int.from_bytes(sch_file.read(4), byteorder="big")
                    while pimage != 65535:
                        sch_file.seek(pimage)
                        
                        sch_addr = int.from_bytes(sch_file.read(4), byteorder="big")
                        if sch_addr == img_addr:
                            plt_addr = int.from_bytes(sch_file.read(4), byteorder="big") >> 11
                            break
                        
                        img_cntr += 1
                        sch_file.seek(4*img_cntr, 0)
                        pimage = int.from_bytes(sch_file.read(4), byteorder="big")
                    
                '''
                read palette
                '''
                if plt_addr > -1:
                    with open(working_dir+"/"+base_name+".SPL", "rb") as spl_file:
                        spl_file.seek(plt_addr, 0)
                        palette = spl_file.read(2**bpp * 2)
                    
                '''
                write palette
                '''
                if plt_addr > -1:
                    with open(working_dir+"/"+name+".plt", "wb") as plt_file:
                        plt_file.write(palette)
            
                '''
                write image
                '''
                with open(working_dir+"/"+img_name, "wb") as image_file:
                    image_file.write(spt_file.read(size))
                    
                if lz2png:
                    if compressed:
                        ss_img_tools.decode(working_dir+"/"+img_name, working_dir+"/"+name+".bin")
                    ss_img_tools.spt2png(working_dir+"/"+name+".bin", width, height, bpp)
            else:
                '''
                write image
                '''
                with open(working_dir+"/"+img_name, "wb") as image_file:
                    image_file.write(spt_file.read(size))
                
            
            ident = spt_file.read(4)
            cntr += 1