# -*- coding: utf-8 -*-
"""
Created on Mon Jun 15 19:23:16 2020

@author: nanashi
"""

import ntpath
import PIL as pil
import numpy as np

use_fallback = False
try:
    from ss_cotton_2_translation_tools import ss_cotton_lz00
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
    
def _x_mirror_tile(tile):
    """
    Mirrors tiles along the x-axis.

    Parameters
    ----------
    tile : np.ndarray
        8x8 array.

    Returns
    -------
    np.ndarray
        Mirrored array.

    """
    rtn = bytearray(64)
    for i in range(0,8):
        start = i*8
        rtn[start:start+8] = tile[start:start+8][::-1]
    return bytes(rtn)
    
def _y_mirror_tile(tile):
    rtn = bytearray(64)
    for i in range(0,8):
        rtn[i*8:(i+1)*8] = tile[(7-i)*8:(8-i)*8]
    return bytes(rtn)

def _plt2clut(plt_data, bpp):
    """
    Converts palette from *.plt file to RGB color lut

    Parameters
    ----------
    plt_data : byte-like
        Raw palette data.
    bpp : int
        Bit per pixel.

    Returns
    -------
    RGB color lut.

    """
    palette_size = 2**bpp
    rgb_clut = []
    j = 0
    for i in range(0,palette_size):
    
        rgb_clut_triplet = [0, 0, 0]
        color = plt_data[j] >> 2
        color = int(color * 8)
        rgb_clut_triplet[2] = color
        
        color = ((plt_data[j] & 3) << 3) | (plt_data[j+1] >> 5)
        color = int(color * 8)
        rgb_clut_triplet[1] = color
        
        color =  plt_data[j+1] & 31
        color = int(color * 8)
        rgb_clut_triplet[0] = color
        
        rgb_clut.append(rgb_clut_triplet)
        
        j += 2
        
    return rgb_clut

def _bin2rgb(image_bin, rgb_clut, width, height, bpp):
    """
    Converts binary image with indexed colors to an RGB image

    Parameters
    ----------
    image_bin : byte-like
        Image data as indexed colors.
    rgb_clut : list
        Color lut.
    width : int
        Image width in px.
    height : int
        Image height in px.
    bpp : int
        Bit per pixel.

    Returns
    -------
    image_rgb : byte-like
        Image RGB data.

    """
    image_rgb = bytes()
    for i in range(0,int(width*height*(bpp/8))):
        if bpp == 8:
            index = image_bin[i]
            image_rgb +=  rgb_clut[index][0].to_bytes(1, 'big')
            image_rgb +=  rgb_clut[index][1].to_bytes(1, 'big')
            image_rgb +=  rgb_clut[index][2].to_bytes(1, 'big')
        elif bpp == 4:
            index = (image_bin[i] & 240) >> 4
            image_rgb +=  rgb_clut[index][0].to_bytes(1, 'big')
            image_rgb +=  rgb_clut[index][1].to_bytes(1, 'big')
            image_rgb +=  rgb_clut[index][2].to_bytes(1, 'big')
            index = image_bin[i] & 15
            image_rgb +=  rgb_clut[index][0].to_bytes(1, 'big')
            image_rgb +=  rgb_clut[index][1].to_bytes(1, 'big')
            image_rgb +=  rgb_clut[index][2].to_bytes(1, 'big')
    return image_rgb

def decode(file, ofile):
    """
    Decompresses LZ00 files from cotton 2 SPT containers

    Parameters
    ----------
    file : str
        Input file with path.
    ofile : str
        Output file with path.

    Returns
    -------
    max_chunk_dist : int
        maximum distance the lz00 compression used to look ahead.

    """
    decoded = bytearray(0)
    out_pos = 0
    
    max_chunk_dist = 0
    with open(file, 'rb') as in_file:
        format_str = in_file.read(4).decode("ascii")
        length = int().from_bytes(in_file.read(4), "big")
        
        if format_str != "LZ00":
            raise TypeError("Wrong file type")
            
        while length:
            
            chunk_len = in_file.read(1)
            if not chunk_len:
                break
            chunk_len = int().from_bytes(chunk_len, 'big')
            
            if chunk_len > 15:
                chunk_dist = chunk_len - 15
                
                max_chunk_dist = max(max_chunk_dist, chunk_dist)
                
                chunk_len = in_file.read(1)
                if not chunk_len:
                    break
                chunk_len = int().from_bytes(chunk_len, "big") + 3
                
                out_pos = len(decoded) - chunk_dist
                
                while chunk_len > 0:
                    chunk_dat = bytes([decoded[out_pos]])
                    if not chunk_dat:
                        break
                    
                    chunk_len -= 1
                    decoded += chunk_dat
                    length -= 1
                    out_pos += 1
                
            else:
                
                while chunk_len >= 0:
                    chunk_dat = in_file.read(1)
                    if not chunk_dat:
                        break
                    
                    chunk_len -= 1
                    decoded += chunk_dat
                    length -= 1
                    out_pos += 1
            
    with open(ofile, 'wb') as out_file:
        for byte in decoded:
            out_file.write(bytes([byte]))
            
    return max_chunk_dist
            
def encode(file, ofile):
    """
    Compresses binary images with the LZ00 cotton 2 algorihmn

    Parameters
    ----------
    file : str
        Input file with path.
    ofile : str
        Output file with path.

    Returns
    -------
    compressed_len : int
        Byte size of the compressed file.

    """
    encoded = []
    encoded_len = 0
    compressed_len = 0
    with open(file, 'rb') as in_file:
        data_byte = in_file.read(1)
        
        cpy_len = 1
        cpy_data = bytes(0)
        cpy_data += data_byte

    
        sbuff = bytes(0)
        sbuff += data_byte

        labuff = bytes(0)
        labuff += in_file.read(258)
        
        cntr = 0
        while True:
            
            sbuff_len = len(sbuff)
            if sbuff_len > 240:
                sbuff = sbuff[-240:]
                sbuff_len = 240
            
            match = find_best_match(labuff, sbuff)
            
            max_match_len = match[2]
            
            if max_match_len > 2:
                
                if cpy_len > 0:
                    encoded.append(("cpy", cpy_len, cpy_data))
                    compressed_len += 1 + cpy_len
                    cpy_len = 0
                    cpy_data = bytes(0)
                
                encoded.append(match)
                compressed_len += 2
                sbuff += labuff[:max_match_len]
                labuff = labuff[max_match_len:] + in_file.read(max_match_len)
                encoded_len += max_match_len
            else:
                cpy_len += 1
                cpy_data += labuff[0:1]
                sbuff += labuff[0:1]
                labuff = labuff[1:] + in_file.read(1)
                encoded_len += 1
                
            if cpy_len == 16:
                encoded.append(("cpy", cpy_len, cpy_data))
                compressed_len += 1 + cpy_len
                cpy_len = 0
                cpy_data = bytes(0)
                
            if len(labuff) == 0:
                break
                
                
            cntr += 1
          
        padding_len = compressed_len % 4
        if padding_len > 0:
            padding_len = 4 - padding_len
        padding = bytes(b'\x00') * padding_len
        with open(ofile, "wb") as enc_file:
            
            enc_file.write("LZ00".encode("ascii"))
            enc_file.write(int.to_bytes(encoded_len+1, 4, 'big'))
            
            write_len = 0
            for elem in encoded:
                
                if elem[0] == "cpy":
                    enc_file.write((elem[1] - 1).to_bytes(1, "big"))
                    enc_file.write(elem[2])
                    write_len += len(elem[2]) + 1
                else:
                    enc_file.write((elem[1] + 15).to_bytes(1, "big"))
                    enc_file.write((elem[2] - 3).to_bytes(1, "big"))
                    write_len += 2
                    
            enc_file.write(padding)
                    
        return compressed_len
    
def tlm2png(tlm_file, scp_file, spl_file, width, height):
    """
    Converts tile maps to png images. Each tilemap has this structure:
        - 1 byte control flags that are used to indicate mirrored tiles
        - 1 byte palette idx of the tile
        - 2 bytes index of the tile in the SCP file

    Parameters
    ----------
    tlm_file : string
        *.tlm tile map file.
    scp_file : .
        *.SCP tiles file.
    spl_file : .
        *.SPL palette file.
    width : int
        Image width in px.
    height : int
        Image height in px.

    Returns
    -------
    None.

    """
    base_name = ntpath.basename(tlm_file).split(".")[0]
    working_dir = ntpath.dirname(tlm_file)
    
    with open(scp_file, "rb") as ifile:
        tile_data = ifile.read()
        
    tiles = []
    for i in range(0, int(len(tile_data)/64)):
        tiles.append(tile_data[i*64:(i+1)*64])
    
    tilemap = []
    plt_lut = {}
    with open(tlm_file, "rb") as ifile:
        ctrl_code = ifile.read(1)
        plt_adr = ifile.read(1)
        tlm_idx = ifile.read(2)
        
        while tlm_idx:
            ctrl_code = int().from_bytes(ctrl_code, "big")
            plt_adr = int().from_bytes(plt_adr, "big") << 5
            tlm_idx = int(int().from_bytes(tlm_idx, "big")/2)
            
            if not plt_adr in plt_lut:
                
                with open(spl_file, "rb") as i2_file:
                    i2_file.seek(plt_adr, 0)
                    plt_lut[plt_adr] = _plt2clut(i2_file.read(512), 8)
            
            if ctrl_code & 0x3F:
                raise ValueError('Unknown control code')
            
            tilemap.append((tlm_idx, ctrl_code, plt_adr))

            ctrl_code = ifile.read(1)
            plt_adr = ifile.read(1)
            tlm_idx = ifile.read(2)
            
    rgb_data = bytearray(width*height*3)
    tlm_idx = 0
    htiles = int(width/8)
    vtiles = int(height/8)
    for i in range(0, vtiles):
        for j in range(0, htiles):
            pos = i*192*htiles+j*24
            tl_idx = tilemap[tlm_idx][0]
            clut = tilemap[tlm_idx][2]
            tile = tiles[tl_idx]
            if tilemap[tlm_idx][1] & 0x40:
                tile = _x_mirror_tile(tile)
            if tilemap[tlm_idx][1] & 0x80:
                tile = _y_mirror_tile(tile)
                
            tile = _bin2rgb(tile, plt_lut[clut], 8, 8, 8)
            
            for k in range(0,8):
                rgb_data[pos:pos+24] = tile[k*24:(k+1)*24]
                pos += width*3
            tlm_idx += 1
            
    image = pil.Image.frombytes("RGB", (width,height), bytes(rgb_data))
    image.save(working_dir+"/"+base_name+".png", "PNG")
    
def spt2png(image, width, height, bpp):     
    '''
    Converts binary images from SPT-files to png. There must be a palette file
    with the same name and the ending "*.plt" for this to work.

    Parameters
    ----------
    image : string
        Image path string.
    width : int
        Image width in pixels.
    height : int
        Image height in pixels.
    bpp : int
        Bits per pixel.

    '''
    base_name = ntpath.basename(image).split(".")[0]
    working_dir = ntpath.dirname(image)
    plt_file = working_dir+"/"+base_name+".plt"
    
    with open(plt_file, 'rb') as in_file:
        plt_bin = in_file.read()
        
    rgb_clut = _plt2clut(plt_bin, bpp)
        
    with open(image, 'rb') as in_file:
        image_bin = in_file.read()
        
    image_rgb = _bin2rgb(image_bin, rgb_clut, width, height, bpp)
        
    image = pil.Image.frombytes("RGB",(width,height),image_rgb)
    image.save(working_dir+"/"+base_name+".png", "PNG")
    
def png2spt(png_image, bpp):

    working_dir = ntpath.dirname(png_image)
    base_name = ntpath.basename(png_image).split(".")[0]
    pallet_file = working_dir+"/"+base_name+".plt"
    
    image = pil.Image.open(png_image)
    
    
    rgb_clut = {}
    with open(pallet_file, 'rb') as in_file:
        
        pbyte = in_file.read(2)
        cntr = 0
        while pbyte:
            palette_color = int.from_bytes(pbyte, 'big')
            
            rcolor = palette_color & 31
            gcolor = (palette_color >> 5) & 31
            bcolor = (palette_color >> 10) & 31
            
            rgb_clut[(rcolor*8, gcolor*8, bcolor*8)] = cntr
            cntr += 1
            pbyte = in_file.read(2)
            
    raw_image = bytes()
    for y in range(0, image.height):
        for x in range(0, image.width):
            
            if bpp == 8:
                colorid = rgb_clut[image.getpixel((x,y))[0:3]]
                raw_image += colorid.to_bytes(1, 'big')
            elif bpp == 4:
                if not x % 2:
                    colorid = rgb_clut[image.getpixel((x,y))[0:3]] << 4
                else:
                    colorid |= rgb_clut[image.getpixel((x,y))[0:3]]
                    raw_image += colorid.to_bytes(1, 'big')
                
            
    with open(working_dir+"/"+base_name+".bin", 'wb') as out_file:
        out_file.write(raw_image)
        
def _str2img_space(lenght_px):
    return np.full((16,lenght_px, 4), np.array([32, 0, 96, 255], dtype='uint8'))
        
def str2img(string, font_folder, out, chr_space=1, space=7):
    """
    Generates an image from a string.

    Parameters
    ----------
    string : str
        String.
    font_folder : str
        Folder that contains the font bitmaps.
    out : str
        Output file.
    chr_space : int, optional
        Space in px inbetween characters. The default is 1.
    space : int, optional
        Space between words. The default is 7.

    Returns
    -------
    None.

    """
    font_lut = {'A':'A','a':'_a','B':'B','b':'_b','C':'C','c':'_c','D':'D',
                'd':'_d','E':'E','e':'_e','F':'F','f':'_f','G':'G','g':'_g',
                'H':'H','h':'_h','I':'I','i':'_i','J':'J','j':'_j','K':'K',
                'k':'_k','L':'L','l':'_l','M':'M','m':'_m','N':'N','n':'_n',
                'O':'O','o':'_o','P':'P','p':'_p','Q':'Q','q':'_q','R':'R',
                'r':'_r','S':'S','s':'_s','T':'T','t':'_t','U':'U','u':'_u',
                'V':'V','v':'_v','W':'W','w':'_w','X':'X','x':'_x','Y':'Y',
                'y':'_y','Z':'Z','z':'_z','.':'_dot','-':'_dash',
                '#comma':'_comma','!':'_excl','!!':'_dexcl','?':'_qm',
                '_"':'_lqt','"_':'_rqt',"'":'_apo','(':'_bral',')':'_brar',
                '★':'_star','&':'_and'}
    
    cmd_lut = {'space':_str2img_space}
    
    bgc = np.array([32, 0, 96, 255], dtype='uint8')
    if chr_space > 0:
        chr_space = np.full((16,chr_space, 4), bgc)
    if space > 0:
        space = np.full((16,space, 4), bgc)
    skip = 0
    
    lines_lst = []
    txt_lst = []
    for idx, char in enumerate(string):
        if skip:
            skip -= 1
            continue
        
        if char in font_lut:
            temp_im = pil.Image.open(font_folder+'/'+font_lut[char]+'.png')
            temp = np.array(temp_im)
            txt_lst.append(temp)
            if type(chr_space) is np.ndarray:
                txt_lst.append(chr_space)
        elif char == ' ':
            if txt_lst[-1] is chr_space:
                txt_lst.pop(-1)
            if type(space) is np.ndarray:
                txt_lst.append(space)
        elif char == '$':
            spf = string.find(' ', idx)
            spvs = string.find('<', idx)
            spve = string.find('>', idx)
            if spvs > -1:
                cmd = string[idx+1:spvs]
                cmd_arg = int(string[spvs+1:spve])
                skip = spve - idx
            else:
                cmd = string[idx+1:spf]
                cmd_arg = 0
                skip = spf - idx
            txt_lst.append(cmd_lut[cmd](cmd_arg))
        elif char == '\n':
            if txt_lst[-1] is chr_space:
                txt_lst.pop(-1)
            lines_lst.append(txt_lst)
            txt_lst = []
            
    if txt_lst[-1] is chr_space:
        txt_lst.pop(-1)
    lines_lst.append(txt_lst)
        
    width_lst = []
    for txt_lst in lines_lst:
        width = 0
        for item in txt_lst:
            width += item.shape[1]
        width_lst.append(width)
        
    max_width = max(width_lst)
    pad = max_width % 8
    left = 0
    if pad > 0:
        pad = 8-pad
        
        max_width += pad
        
        left = int(pad / 2)
        
        if pad % 2:
            left += 1
            
    for idx, txt_lst in enumerate(lines_lst):
        width = width_lst[idx]
        right = max_width - (width + left)
    
        if left > 0:
            txt_lst.insert(0, np.full((16,left, 4), bgc))
        if right > 0:
            txt_lst.append(np.full((16,right, 4), bgc))
    
    vert = []
    for txt_lst in lines_lst:
        vert.append(np.hstack(txt_lst))
    image_im = pil.Image.fromarray(np.vstack(vert))
    image_im.save(out)
    