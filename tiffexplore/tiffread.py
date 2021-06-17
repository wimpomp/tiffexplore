import struct
import tifffile
import numpy as np


class tiff():
    def __init__(self, file):
        self.file = file
        self.fh = open(file, 'rb')
        self.tiff = tifffile.TiffFile(self.file)
        self.tags = []
        self.get_file_len()
        self.addresses = assignments(len(self))
        nifd = self.read_header()
        i = 0
        while nifd:
            nifd = self.read_ifd(nifd, i)
            i += 1
        self.nifds = i
        for i, tags in enumerate(self.tags):
            if 273 in tags and 279 in tags:
                for j, a in enumerate(zip(tags[273][-1], tags[279][-1])):
                    self.addresses[('image', i, j)] = a

    def get_file_len(self):
        self.fh.seek(0, 2)
        self.len = self.fh.tell()

    def __len__(self):
        return self.len

    def asarray(self, page, segment):
        return [d for d in zip(self.tiff.pages[page].segments(), range(segment + 1))][-1][0][0].squeeze()

    def read_header(self):
        self.fh.seek(0)
        self.byteorder = {b'II': '<', b'MM': '>'}[self.fh.read(2)]
        self.bigtiff = {42: False, 43: True}[struct.unpack(self.byteorder + 'H', self.fh.read(2))[0]]
        if self.bigtiff:
            self.tagsize = 20
            self.tagnoformat = 'Q'
            self.offsetsize = struct.unpack(self.byteorder + 'H', self.fh.read(2))[0]
            self.offsetformat = {8: 'Q', 16: '2Q'}[self.offsetsize]
            assert struct.unpack(self.byteorder + 'H', self.fh.read(2))[0] == 0, 'Not a TIFF-file'
            self.offset = struct.unpack(self.byteorder + self.offsetformat, self.fh.read(self.offsetsize))[0]
        else:
            self.tagsize = 12
            self.tagnoformat = 'H'
            self.offsetformat = 'I'
            self.offsetsize = 4
            self.offset = struct.unpack(self.byteorder + self.offsetformat, self.fh.read(self.offsetsize))[0]
        self.addresses[('header',)] = (0, 4 + self.bigtiff * 4 + self.offsetsize)
        return self.offset

    def read_ifd(self, offset, idx):
        """ Reads an IFD of the tiff file
            wp@tl20200214
        """
        self.fh.seek(offset)
        nTags = struct.unpack(self.byteorder + self.tagnoformat, self.fh.read(struct.calcsize(self.tagnoformat)))[0]
        # print('Found {} tags'.format(nTags))
        assert nTags < 4096, 'Too many tags'

        length = 8 if self.bigtiff else 2
        length += nTags * self.tagsize + self.offsetsize

        tags = {}
        for i in range(nTags):
            pos = offset + struct.calcsize(self.tagnoformat) + self.tagsize * i
            self.fh.seek(pos)

            code, ttype = struct.unpack(self.byteorder + 'HH', self.fh.read(4))
            count = struct.unpack(self.byteorder + self.offsetformat, self.fh.read(self.offsetsize))[0]
            dtype = tifffile.TIFF.DATA_FORMATS[ttype]
            dtypelen = struct.calcsize(dtype)

            toolong = struct.calcsize(dtype) * count > self.offsetsize
            if toolong:
                caddr = struct.unpack(self.byteorder + self.offsetformat, self.fh.read(self.offsetsize))[0]
                self.addresses[('tagdata', idx, code)] = (caddr, dtypelen * count)
                cp = self.fh.tell()
                self.fh.seek(caddr)
            else:
                caddr = self.fh.tell()

            if ttype == 1:
                value = self.fh.read(count)
            elif ttype == 2:
                value = self.fh.read(count).decode('ascii').rstrip('\x00')
            elif ttype == 5:
                value = [struct.unpack(self.byteorder + dtype, self.fh.read(dtypelen)) for _ in range(count)]
            else:
                value = [struct.unpack(self.byteorder + dtype, self.fh.read(dtypelen))[0] for _ in range(count)]

            if toolong:
                self.fh.seek(cp)

            tags[code] = (ttype, caddr, dtypelen*count, value)

        nifd = struct.unpack(self.byteorder + self.tagnoformat, self.fh.read(struct.calcsize(self.tagnoformat)))[0]
        self.fh.seek(offset)
        self.addresses[('ifd', idx)] = (offset, 2 * struct.calcsize(self.tagnoformat) + nTags * self.tagsize)
        self.tags.append(tags)
        return nifd

    def __getitem__(self, item):
        if not isinstance(item, slice):
            item = slice(item, item+1)
        start = 0 if item.start is None or item.start < 0 else item.start
        step = item.step or 1
        stop = len(self) if item.stop is None or item.stop > len(self) else item.stop
        self.fh.seek(start)
        return self.fh.read(stop - start)[::step]

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.tiff.close()
        self.close()

    def close(self, *args, **kwargs):
        self.fh.close()

    def get_bytes(self, part):
        offset, length = self.addresses[part]
        self.fh.seek(offset)
        return self.fh.read(length)


class assignments(dict):
    def __init__(self, max_addr=0, *args, **kwargs):
        self.max_addr = max_addr
        super().__init__(*args, **kwargs)

    def get_assignment(self, addr):
        keys, values = zip(*self.items())
        offsets, lengths = zip(*values)
        offset_arr = np.array(offsets)
        offset_len = offset_arr + lengths
        nearest_addr = np.max(offset_arr[offset_arr <= addr])
        idxs = np.where(offset_arr == nearest_addr)[0]
        if addr < nearest_addr + lengths[idxs[0]]:
            return [(keys[idx], self[keys[idx]]) for idx in idxs]
        else:
            previous_addr = np.max(offset_len[offset_len <= addr])
            next_addr = offset_arr[offset_arr > addr]
            length = np.min(next_addr) - previous_addr if len(next_addr) else self.max_addr - previous_addr
            return [(('empty',), (previous_addr, length))]

    def get_assignments(self, start=0, end=-1):
        addr = start
        if end == -1:
            end = self.max_addr
        while addr < end:
            item = self.get_assignment(addr)
            addr = sum(item[0][1])
            yield item
