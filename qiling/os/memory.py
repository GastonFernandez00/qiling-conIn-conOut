#!/usr/bin/env python3
# 
# Cross Platform and Multi Architecture Advanced Binary Emulation Framework
#

import os, re
from typing import Any, List, MutableSequence, Optional, Sequence, Tuple

from qiling import Qiling
from qiling.const import *
from qiling.exception import *

# tuple: range start, range end, permissions mask, range label
MapInfoEntry = Tuple[int, int, int, str]

from unicorn import (
    UC_PROT_ALL,
    UC_PROT_EXEC,
    UC_PROT_NONE,
    UC_PROT_READ,
    UC_PROT_WRITE,
)

class QlMemoryManager:
    """
    some ideas and code from:
    https://github.com/zeropointdynamics/zelos/blob/master/src/zelos/memory.py
    """

    def __init__(self, ql: Qiling):
        self.ql = ql
        self.map_info: MutableSequence[MapInfoEntry] = []

        bit_stuff = {
            64 : (1 << 64) - 1,
            32 : (1 << 32) - 1,
            16 : (1 << 20) - 1   # 20bit address line
        }

        if ql.archbit not in bit_stuff:
            raise QlErrorStructConversion("Unsupported Qiling archtecture for memory manager")

        max_addr = bit_stuff[ql.archbit]

        #self.read_ptr = read_ptr
        self.max_addr = max_addr
        self.max_mem_addr = max_addr

    def __read_string(self, addr: int) -> str:
        ret = bytearray()
        c = self.read(addr, 1)

        while c[0]:
            ret += c
            addr += 1
            c = self.read(addr, 1)

        return ret.decode()

    def __write_string(self, addr: int, s: str, encoding: str):
        self.write(addr, bytes(s, encoding) + b'\x00')

    # TODO: this is an obsolete utility method that should not be used anymore
    # and here for backward compatibility. use QlOsUtils.read_cstring instead
    def string(self, addr: int, value=None, encoding='utf-8') -> Optional[str]:
        """Read or write string to memory.

        Args:
            addr: source / destination address
            value: string to write, or None if reading one from memory
            encoding: string encoding

        Returns: null-terminated string read from memory, or None if wrote one
        """

        if value is None:
            return self.__read_string(addr)

        self.__write_string(addr, value, encoding)

    def add_mapinfo(self, mem_s: int, mem_e: int, mem_p: int, mem_info: str):
        tmp_map_info = []
        insert_flag = 0
        map_info = self.map_info
        if len(map_info) == 0:
            tmp_map_info.append([mem_s, mem_e, mem_p, mem_info])
        else:
            for s, e, p, info in map_info:
                if e <= mem_s:
                    tmp_map_info.append([s, e, p, info])
                    continue
                if s >= mem_e:
                    if insert_flag == 0:
                        insert_flag = 1
                        tmp_map_info.append([mem_s, mem_e, mem_p, mem_info])
                    tmp_map_info.append([s, e, p, info])
                    continue
                if s < mem_s:
                    tmp_map_info.append([s, mem_s, p, info])

                if s == mem_s:
                    pass

                if insert_flag == 0:
                    insert_flag = 1
                    tmp_map_info.append([mem_s, mem_e, mem_p, mem_info])

                if e > mem_e:
                    tmp_map_info.append([mem_e, e, p, info])

                if e == mem_e:
                    pass
            if insert_flag == 0:
                tmp_map_info.append([mem_s, mem_e, mem_p, mem_info])

        self.map_info = tmp_map_info


    def del_mapinfo(self, mem_s: int, mem_e: int):
        """Subtract a memory range from map.

        Args:
            mem_s: memory range start
            mem_e: memory range end
        """

        tmp_map_info = []

        for s, e, p, info in self.map_info:
            if e <= mem_s:
                tmp_map_info.append((s, e, p, info))
                continue

            if s >= mem_e:
                tmp_map_info.append((s, e, p, info))
                continue

            if s < mem_s:
                tmp_map_info.append((s, mem_s, p, info))

            if s == mem_s:
                pass

            if e > mem_e:
                tmp_map_info.append((mem_e, e, p, info))

            if e == mem_e:
                pass

        self.map_info = tmp_map_info

    def get_mapinfo(self) -> Sequence[Tuple[int, int, str, str, Optional[str]]]:
        """Get memory map info.

        Returns: A sequence of 5-tuples representing the memory map entries. Each
        tuple contains range start, range end, permissions, range label and path of
        containing image (or None if not contained by any image)
        """

        def __perms_mapping(ps: int) -> str:
            perms_d = {
                UC_PROT_READ  : 'r',
                UC_PROT_WRITE : 'w',
                UC_PROT_EXEC  : 'x'
            }

            return ''.join(val if idx & ps else '-' for idx, val in perms_d.items())

        def __process(lbound: int, ubound: int, perms: int, label: str) -> Tuple[int, int, str, str, Optional[str]]:
            perms_str = __perms_mapping(perms)

            image = self.ql.os.find_containing_image(lbound)
            container = image.path if image else None

            return (lbound, ubound, perms_str, label, container)

        return tuple(__process(*entry) for entry in self.map_info)

    def show_mapinfo(self):
        """Emit memory map info in a nicely formatted table.
        """
        def _perms_mapping(ps):
            perms_d = {1: "r", 2: "w", 4: "x"}
            perms_sym = []
            for idx, val in perms_d.items():
                if idx & ps != 0:
                    perms_sym.append(val)
                else:
                    perms_sym.append("-")
            return "".join(perms_sym)

        self.ql.log.info("[+] Start      End        Perm.  Path")
        for  start, end, perm, info in self.map_info:
            _perm = _perms_mapping(perm)
            image = self.ql.os.find_containing_image(start)
            if image:
                info += f" ({image.path})"
            self.ql.log.info("[+] %08x - %08x - %s    %s" % (start, end, _perm, info))


    def get_lib_base(self, filename: str) -> int:
        for s, e, p, info in self.map_info:
            if os.path.split(info)[1] == filename:
                return s
        return -1

    def align(self, addr: int, alignment: int = 0x1000) -> int:
        """Round up to nearest alignment.

        Args:
            addr: address to align
            alignment: alignment granularity, must be a power of 2
        """

        # rounds up to nearest alignment
        mask = ((1 << self.ql.archbit) - 1) & -alignment
        return (addr + (alignment - 1)) & mask

    # save all mapped mem
    def save(self):
        mem_dict = {}
        seq = 1
        for start, end, perm, info in self.map_info:
            mem_read = self.read(start, end-start)          
            mem_dict[seq] = start, end, perm, info, mem_read
            seq += 1
        return mem_dict

    # restore all dumped memory
    def restore(self, mem_dict):
        for key, value in mem_dict.items():
            start = value[0]
            end = value[1]
            perm = value[2]
            info = value[3]
            mem_read = bytes(value[4])

            self.ql.log.debug("restore key: %i 0x%x 0x%x %s" % (key, start, end, info))
            if self.is_mapped(start, end-start) == False:
                self.ql.log.debug("mapping 0x%x 0x%x mapsize 0x%x" % (start, end, end-start))
                self.map(start, end-start, perms=perm, info=info)

            self.ql.log.debug("writing 0x%x size 0x%x write_size 0x%x " % (start, end-start, len(mem_read)))
            self.write(start, mem_read)

    def read(self, addr: int, size: int) -> bytearray:
        """Read bytes from memory.

        Args:
            addr: source address
            size: amount of bytes to read

        Returns: bytes located at the specified address
        """

        return self.ql.uc.mem_read(addr, size)

    def read_ptr(self, addr: int, size: int=None) -> int:
        """Read an integer value from a memory address.

        Args:
            addr: memory address to read
            size: pointer size (in bytes): either 1, 2, 4, 8, or None for arch native size

        Returns: integer value stored at the specified memory address
        """

        if not size:
            size = self.ql.pointersize

        if size == 1:
            return self.ql.unpack8(self.read(addr, 1))
        elif size == 2:
            return self.ql.unpack16(self.read(addr, 2))
        elif size == 4:
            return self.ql.unpack32(self.read(addr, 4))
        elif size == 8:
            return self.ql.unpack64(self.read(addr, 8))
        else:
            raise QlErrorStructConversion(f"Unsupported pointer size: {size}")

    def write(self, addr: int, data: bytes) -> None:
        """Write bytes to a memory.

        Args:
            addr: destination address
            data: bytes to write
        """

        try:
            self.ql.uc.mem_write(addr, data)
        except:
            self.show_mapinfo()
            self.ql.log.debug("addresss write length: " + str(len(data)))
            self.ql.log.error("addresss write error: " + hex(addr))
            raise

    def search(self, needle: bytes, begin: int = None, end: int = None):
        """
        Search for a sequence of bytes in memory. Returns all sequences
        that match
        """

        addrs = []
        if (begin and end) and end > begin:
            haystack = self.read(begin, end - begin)
            addrs = [x.start(0) + begin for x in re.finditer(needle, haystack)]

        if not begin:
            begin = self.map_info[0][0] # search from the first mapped region 
        if not end:
            end = self.map_info[-1][1] # search till the last mapped region

        mapped_range = [(_begin, _end) for _begin, _end, _ in self.ql.uc.mem_regions()
                if _begin in range(begin, end) or _end in range(begin, end)]
        
        for _begin, _end in mapped_range:
            haystack = self.read(_begin, _end - _begin)
            addrs += [x.start(0) + _begin for x in re.finditer(needle, haystack)]

        return addrs

    def unmap(self, addr: int, size: int) -> None:
        """Reclaim a memory range.

        Args:
            addr: range base address
            size: range size (in bytes)
        """

        self.del_mapinfo(addr, addr + size)
        self.ql.uc.mem_unmap(addr, size)


    def unmap_all(self):
        """Reclaim the entire memory space.
        """

        for region in list(self.ql.uc.mem_regions()):
            if region[0] and region[1]:
                return self.unmap(region[0], ((region[1] - region[0])+0x1))


    def is_available(self, addr, size):
        '''
        The main function of is_available is to determine 
        whether the memory starting with addr and having a size of length can be used for allocation.

        If it can be allocated, returns True.

        If it cannot be allocated, it returns False.
        '''
        try:
            self.map(addr, addr)
        except:
            return False    
        
        self.unmap(addr, addr)
        return True


    def is_mapped(self, address, size): 
        '''
        The main function of is_mmaped is to determine 
        whether the memory starting with addr and size has been mapped.
        Returns true if it has already been allocated.
        If unassigned, returns False.
        '''   

        for region in list(self.ql.uc.mem_regions()):
            if ((address >= region[0] and address < region[1]) or
            ((address + size - 1) >= region[0] and (address + size - 1) < region[1]) or
            (address <= region[0] and (address + size - 1) > region[1])):
                self.ql.log.info("%x - %x is taken" % (address, address + size - 1))
                return True

        return False
        
    
    def is_free(self, address, size):
        '''
        The main function of is_free first must fufull is_mapped condition.
        then, check for is the mapped range empty, either fill with 0xFF or 0x00
        Returns true if mapped range is empty else return Flase
        If not not mapped, map it and return true
        '''
        if self.is_mapped(address, size) == True:
            address_end = (address + size)
            while address < address_end:
                mem_read = self.ql.mem.read(address, 0x1)
                if (mem_read[0] != 0x00) and (mem_read[0] != 0xFF):
                    return False
                address += 1
            return True
        else:
            return True


    def find_free_space(self, size, min_addr=0, max_addr = 0, alignment=0x10000):
        """
        Finds a region of memory that is free, larger than 'size' arg,
        and aligned.
        """
        mapped = []
        
        for address_start, address_end, perm, info in self.ql.mem.map_info:
            mapped += [[address_start, (address_end - address_start)]]
        
        for address_start, address_end, perms in self.ql.uc.mem_regions():
            mapped += [[address_start, (address_end - address_start)]]
        
        for i in range(0, len(mapped)):
            addr = self.align(
                mapped[i][0] + mapped[i][1], alignment=alignment
            )
            # Enable allocating memory in the middle of a gap when the
            # min requested address falls in the middle of a gap
            if addr < min_addr:
                addr = min_addr
            # Cap the gap's max address by accounting for the next
            # section's start address, requested max address, and the
            # max possible address

            max_gap_addr = (
                self.max_addr
                if i == len(mapped) - 1
                else mapped[i + 1][1]
            )

            max_gap_addr = min(max_gap_addr, self.max_mem_addr)
            # Ensure the end address is less than the max and the start
            # address is free
            if addr + size < max_gap_addr and self.is_mapped(addr, size) == False:
                return addr
        raise QlOutOfMemory("Out Of Memory")


    def map_anywhere(
        self,
        size,
        #name = "",
        #kind = "",
        min_addr = 0,
        alignment = 0x1000,
        #prot: int = ProtType.RWX,
    ) -> int:
        """
        Maps a region of memory with requested size, within the
        addresses specified. The size and start address will respect the
        alignment.

        Args:
            size: # of bytes to map. This will be rounded up to match
                the alignment.
            name: String used to identify mapped region. Used for
                debugging.
            kind: String used to identify the purpose of the mapped
                region. Used for debugging.
            min_addr: The lowest address that could be mapped.
            max_addr: The highest address that could be mapped.
            alignment: Ensures the size and start address are multiples
                of this. Must be a multiple of 0x1000. Default 0x1000.
            prot: RWX permissions of the mapped region. Defaults to
                granting all permissions.
        Returns:
            Start address of mapped region.
        """
        max_mem_addr = self.max_mem_addr
        address = self.find_free_space(
            size, min_addr=min_addr, max_addr=max_mem_addr, alignment=alignment
        )
        """
        we need a better mem_map as defined in the issue
        """
        #self.map(address, util.align(size), name, kind)
        self.map(address, self.align(size))
        return address

    def protect(self, addr, size, perms):
        aligned_address = (addr >> 12) << 12
        aligned_size = self.align((addr & 0xFFF) + size)
        self.ql.uc.mem_protect(aligned_address, aligned_size, perms)


    def map(self, addr, size, perms=UC_PROT_ALL, info=None, ptr=None):
        '''
	    The main function of mem_mmap is to implement memory allocation in unicorn, 
	    which is slightly similar to the function of syscall_mmap. 

	    When the memory can satisfy the given addr and size, 
	    it needs to be allocated to the corresponding address space.
	    
	    Upon successful completion, mem_map() shall return 0; 

    	otherwise, it shall return -1 and set errno to indicate the error.
         
        is should call other API to get_available mainly gives a length, 
        and then the memory manager returns  an address that can apply for that length.

        '''
        if ptr == None:
            if self.is_mapped(addr, size) == False:
                self.ql.uc.mem_map(addr, size, perms)
                self.add_mapinfo(addr, addr + size, perms, info if info else "[mapped]")
            else:
                raise QlMemoryMappedError("Memory Mapped")    
        else:
            self.ql.uc.mem_map_ptr(addr, size, perms, ptr)

    def get_mapped(self):
        for idx, val in enumerate(self.ql.uc.mem_regions()):
            self.ql.log.info(idx, list(map(hex, val)))

# A Simple Heap Implementation
class Chunk():
    def __init__(self, address: int, size: int):
        self.inuse = True
        self.address = address
        self.size = size

    @staticmethod
    def compare(chunk):
        return chunk.size

class QlMemoryHeap:
    def __init__(self, ql: Qiling, start_address: int, end_address: int):
        self.ql = ql
        self.chunks: List[Chunk] = []
        self.start_address = start_address
        self.end_address = end_address
        # unicorn needs 0x1000
        self.page_size = 0x1000
        # current alloced memory size
        self.current_alloc = 0
        # curent use memory size
        self.current_use = 0
        # save all memory regions allocated
        self.mem_alloc = []
    
    def save(self):
        saved_state = {}
        saved_state['chunks'] = self.chunks
        saved_state['start_address'] = self.start_address
        saved_state['end_address'] = self.end_address
        saved_state['page_size'] = self.page_size
        saved_state['current_alloc'] = self.current_alloc
        saved_state['current_use'] = self.current_use
        saved_state['mem_alloc'] = self.mem_alloc
        return saved_state

    def restore(self, saved_state):
        self.chunks = saved_state['chunks']
        self.start_address = saved_state['start_address']
        self.end_address = saved_state['end_address']
        self.page_size = saved_state['page_size']
        self.current_alloc = saved_state['current_alloc']
        self.current_use = saved_state['current_use']
        self.mem_alloc = saved_state['mem_alloc']

    def alloc(self, size: int):
        # Find the heap chunks that best matches size 
        self.chunks.sort(key=Chunk.compare)
        for chunk in self.chunks:
            if chunk.inuse is False and chunk.size > size:
                chunk.inuse = True
                return chunk.address

        chunk = None
        # If we need mem_map new memory
        if self.current_use + size > self.current_alloc:
            real_size = self.ql.mem.align(size, self.page_size)
            # If the heap is not enough
            if self.start_address + self.current_use + real_size > self.end_address:
                return 0
            self.ql.mem.map(self.start_address + self.current_alloc, real_size, info="[heap]")
            chunk = Chunk(self.start_address + self.current_use, size)
            self.mem_alloc.append((self.start_address + self.current_alloc, real_size))
            self.current_alloc += real_size
            self.current_use += size
            self.chunks.append(chunk)
        else:
            chunk = Chunk(self.start_address + self.current_use, size)
            self.current_use += size
            self.chunks.append(chunk)

        chunk.inuse = True
        #ql.log.debug("heap.alloc addresss: " + hex(chunk.address))
        return chunk.address

    def size(self, addr: int) -> int:
        """Get the size of allocated memory chunk starting at a specific address.

        Args:
            addr: chunk starting address

        Returns: chunk size (in bytes), or 0 if no chunk starts at that address
        """

        for chunk in self.chunks:
            if addr == chunk.address and chunk.inuse:
                return chunk.size
        return 0

    def free(self, addr: int) -> bool:
        """Free up memory at a specific address.

        Args:
            addr: address of memory to free

        Returns: True iff memory was freed successfully, False otherwise
        """

        for chunk in self.chunks:
            if addr == chunk.address and chunk.inuse:
                chunk.inuse = False
                return True
        return False

    # clear all memory regions alloc
    def clear(self):
        for chunk in self.chunks:
            chunk.inuse = False

        for addr, size in self.mem_alloc:
            self.ql.mem.unmap(addr, size)

        self.mem_alloc.clear()

        self.current_alloc = 0
        self.current_use = 0

    def _find(self, addr: int, inuse: bool = None) -> Optional[Chunk]:
        """Find a chunk starting at a specified address.

        Args:
            addr: starting address of the requested chunk
            inuse: whether the chunk should be in-use; None if dont care

        Returns: chunk instance starting at specified address whose in-use status is set
        as required (if required), None if no such chunk was found
        """

        for chunk in self.chunks:
            if addr == chunk.address:
                return chunk
        return None
