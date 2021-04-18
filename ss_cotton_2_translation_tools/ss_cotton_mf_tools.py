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
        *.SAN       Contains animation sequences
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
        *.SAN       Contains animation sequences
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
                
                bpp = int((8*size)/(width*height))
                
                if format_str == "LZ00":
                    img_name = name+".lz00"
                    uncomp_size = int.from_bytes(fspt_file.read(4), byteorder="big")
                    bpp = int((8*uncomp_size)/(width*height))
                    fspt_file.seek(-8,1)
                elif bpp > 0:
                    img_name = name+".bin"
                    fspt_file.seek(-4,1)
                else:
                    img_name = name+".tlm"
                    fspt_file.seek(-4,1)
                    
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
        
def gen_font_table(temp_file):
    """
    Uses the template file to generate a reducted font table that contains
    all characters used in the template.

    Parameters
    ----------
    temp_file : string
        Template file.

    Returns
    -------
    None.

    """
    working_dir = ntpath.dirname(temp_file)+'/'
    base_name = ntpath.basename(temp_file).split(".")[0]
    
    font_lut = {'A':'A','a':'_a','B':'B','b':'_b','C':'C','c':'_c','D':'D',
                'd':'_d','E':'E','e':'_e','F':'F','f':'_f','G':'G','g':'_g',
                'H':'H','h':'_h','I':'I','i':'_i','J':'J','j':'_j','K':'K',
                'k':'_k','L':'L','l':'_l','M':'M','m':'_m','N':'N','n':'_n',
                'O':'O','o':'_o','P':'P','p':'_p','Q':'Q','q':'_q','R':'R',
                'r':'_r','S':'S','s':'_s','T':'T','t':'_t','U':'U','u':'_u',
                'V':'V','v':'_v','W':'W','w':'_w','X':'X','x':'_x','Y':'Y',
                'y':'_y','Z':'Z','z':'_z',' ':'_spc','.':'_dot','-':'_dash',
                '#comma':'_comma','!':'_excl','!!':'_dexcl','?':'_qm',
                '_"':'_lqt','"_':'_rqt',"'":'_apo','..':'_ddot','(':'_bral',
                ')':'_brar'}
    
    with open(temp_file, 'r') as ifile:
        temp_data = ifile.read().split('\n')
    
    sym_list = []
    for line in temp_data:
        symb = line.split(',')[0]
        if symb == '\\n':
            continue
        if symb not in sym_list:
            sym_list.append(symb)
            
    nout = working_dir+base_name+'.SPT.temp'
    with open(nout, 'w') as ofile:
        for sym in sym_list:
            if sym == '':
                continue
            ofile.write(sym+','+font_lut[sym]+'.bin,0,8,16,4\n')
    
            
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
            rtn = int(command_dict[line.pop(0)]).to_bytes(4, 'big')
        except KeyError:
            rtn = int(command_dict["a"]).to_bytes(4, 'big')
        for elem in line:
            rtn += int(elem).to_bytes(2, 'big')
        return rtn
            
    with codecs.open(sch_info_file, 'r', 'utf-8') as in_file:
        
        '''
        generate binary command data
        '''
        line_cntr = 0
        commands_bin = bytes()
        length_lst = []
        for line in in_file:
            
            line = line.split(",")
            line[-1] = line[-1].strip('\r\n')
            line_cntr += 1
            
            new_command = line2bin(line)
            length_lst.append(len(new_command))
            commands_bin += new_command
        
        '''
        generate pointer table
        '''
        ptable_bin = bytes()
        current_pointer = (line_cntr + 1) * 4
        for length in length_lst:
            ptable_bin += current_pointer.to_bytes(4, 'big')
            current_pointer += length
        ptable_bin += b'\xff\xff\xff\xff'
        
    with open(sch_file, 'wb') as out_file:
        out_file.write(ptable_bin)
        out_file.write(commands_bin)
        
        
def san_decompose(san_file, sch_info_file):
    
    working_dir = ntpath.dirname(san_file)+'/'
    base_name = ntpath.basename(san_file).split(".")[0]
    
    with codecs.open(sch_info_file, 'r', 'utf-8') as fsch:
        sch_data = fsch.read().split('\n')
    
    san_lst = []
    pt_pos = 0
    with open(san_file, 'rb') as fsan:
        f_pos = int.from_bytes(fsan.read(4), byteorder="big")
        while f_pos != 0xffffffff:
            san_lst.append([])
            pt_pos = fsan.tell()
            fsan.seek(f_pos, 0)
            while True:
                img_id = int.from_bytes(fsan.read(2), byteorder="big")
                img_id = sch_data[img_id].split(',')[0]
                num = int.from_bytes(fsan.read(2), byteorder="big", signed=True)
                unk = int.from_bytes(fsan.read(4), byteorder="big")
                san_lst[-1].append((img_id, num, unk))
                
                if num == -1:
                    break
            fsan.seek(pt_pos, 0)
            f_pos = int.from_bytes(fsan.read(4), byteorder="big")
            
    outfile = working_dir+base_name+'.SAN.info'
    with open(outfile, 'w') as ofile:
        for line in san_lst:
            for item in line:
                ofile.write(item[0]+','+str(item[1])+','+str(item[2]))
                ofile.write(';')
            ofile.seek(ofile.tell()-1,0)
            ofile.write('\n')
            
def san_compose(san_info_file, sch_info_file):
    
    def find_item(lst, string):
        for i in range(0, len(lst)):
            if lst[i].find(string) > -1:
                return i
                
    working_dir = ntpath.dirname(san_info_file)+'/'
    base_name = ntpath.basename(san_info_file).split(".")[0]
    
    with codecs.open(sch_info_file, 'r', 'utf-8') as fsch:
        sch_data = fsch.read().split('\n')

    with open(san_info_file, 'r') as inf_file:
        inf_data = inf_file.read()
    inf_data = inf_data.split('\n')
    
    while inf_data[-1] == '':
        inf_data.pop(-1)
    
    pt_table = []
    data = bytearray()
    empty = 0
    
    pos = 0
    for line in inf_data:
        pt_table.append(pos)
        line = line.split(';')
        for item in line:
            item = item.split(',')
            sch_idx = find_item(sch_data, item[0])
            data += (sch_idx).to_bytes(2, 'big')
            data += int(item[1]).to_bytes(2, 'big', signed=True)  
            data += int(item[2]).to_bytes(4, 'big')  
            pos += 8
            
    with open(working_dir+base_name+'.SAN', 'wb') as fout:
        offset = (len(pt_table)-empty+1)*4
        for pt in pt_table:
            fout.write((pt+offset).to_bytes(4, 'big'))
        fout.write((0xffffffff).to_bytes(4, 'big'))
        fout.write(data)
                  
                
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
            sch_data = in_file.read()
        
        '''
        read pointer table
        '''   
        ptr_lst = []
        ptable_pos = 0
        while True:
            cmd_pointer = int.from_bytes(sch_data[ptable_pos:ptable_pos+4], byteorder="big")
            
            if cmd_pointer == 4294967295:
                break
            
            ptr_lst.append(cmd_pointer)
            ptable_pos += 4
            
        ptr_lst.append(len(sch_data))
        
        '''
        read data
        '''
        for i in range(0, len(ptr_lst)-1):
            pos = ptr_lst[i]
            img_addr = int.from_bytes(sch_data[pos:pos+4], byteorder="big")
            pos += 4
            img_num = _spt_find_num(spt_file, img_addr)
            cmd_ident = img_list[img_num]
            
            cmd_args = []
            while pos < ptr_lst[i+1]:
                cmd_arg = int.from_bytes(sch_data[pos:pos+2], byteorder="big")
                pos += 2
                cmd_args.append(cmd_arg)
                
            line = cmd_ident
            for cmd_arg in cmd_args:
                line += ","+str(cmd_arg)
            out_file.write(line+"\n")
                
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
                bpp = 8
                img_name = name+".tlm"
                tile_map = True
            
            '''
            search palette
            '''
            img_cntr = 0
            pimage = 0
            plt_addr = -1
            with open(working_dir+"/"+base_name+".SCH", "rb") as sch_file:
                '''
                read header
                '''
                pimage = int.from_bytes(sch_file.read(4), byteorder="big")
                while pimage != 4294967295:
                    sch_file.seek(pimage)
                    
                    sch_addr = int.from_bytes(sch_file.read(4), byteorder="big")
                    if sch_addr == img_addr:
                        plt_addr = int.from_bytes(sch_file.read(4), byteorder="big") >> 11
                        if plt_addr > -1:
                            plt_prev = plt_addr
                        break
                    
                    img_cntr += 1
                    sch_file.seek(4*img_cntr, 0)
                    pimage = int.from_bytes(sch_file.read(4), byteorder="big")
                    
            if plt_addr == -1:
                plt_addr = plt_prev
                
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
                if tile_map:
                    ss_img_tools.tlm2png(working_dir+"/"+img_name, 
                                         working_dir+"/"+base_name+".SCP", 
                                         working_dir+"/"+base_name+".SPL", 
                                         width, height)
                else:
                    if compressed:
                        ss_img_tools.decode(working_dir+"/"+img_name, working_dir+"/"+name+".bin")
                    ss_img_tools.spt2png(working_dir+"/"+name+".bin", width, height, bpp)
                
            
            ident = spt_file.read(4)
            cntr += 1