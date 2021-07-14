import struct
import tifffile
import numpy as np
from traceback import format_exc

ifdcodes = {330: 'sub', 34665: 'exif', 34853: 'gps', 40965: 'inter'}

class tiff():
    def __init__(self, file):
        self.file = file
        self.fh = open(file, 'rb')
        try:
            self.tiff = tifffile.TiffFile(self.file)
        except Exception:
            self.tiff = None
        self.tags = {}
        self.get_file_len()
        self.addresses = assignments(len(self))
        self.offsets = []
        self.nTags = {}
        self.tagsread = set()
        try:
            self.offsets = [self.read_header()]
            idx = 0
            while 0 < self.offsets[-1] < len(self):
                self.offsets.append(self.read_ifd(self.offsets[-1], idx))
                idx += 1
            self.readtags()
        except Exception:
            print(format_exc())

    def readtags(self):
        while len(set(self.tags.keys()) - self.tagsread):
            for idx in set(self.tags.keys()) - self.tagsread:
                tags = self.tags[idx]
                if idx not in self.tagsread:
                    if 273 in tags and 279 in tags:
                        for i, a in enumerate(zip(tags[273][-1], tags[279][-1])):
                            self.addresses[('image', idx, i)] = a
                    for code, id in ifdcodes.items():
                        if code in tags:
                            if len(tags[code][3]) == 1:
                                self.offsets.append(self.read_ifd(tags[code][3][0], f'{id}_{idx}'))
                            else:
                                for i, offset in enumerate(tags[code][3]):
                                    self.offsets.append(self.read_ifd(offset, f'{id}_{idx}_{i}'))
                self.tagsread.add(idx)

    @staticmethod
    def fmt_tag(code, value):
        text = [f'Code: {code}']
        if code in tifffile.TIFF.TAGS:
            text[-1] += f'; {tifffile.TIFF.TAGS[code]}'
        text.append(f'data format: {value[0]}')
        try:
            text[-1] += f'; {tifffile.TIFF.DATATYPES(value[0]).name.lower()}'
        except ValueError:
            pass
        text.append(f'address: {value[1]}')
        text.append(f'count: {value[2]}')
        if value[0] in (5, 10):
            text.append(f'value: [{", ".join(["-" * (sum([w<0 for w in v]) % 2) + "/".join([str(abs(w)) for w in v[::-1]]) for v in value[3]])}]')
        else:
            text.append(f'value: {value[3]}')
        return '\n'.join(text)

    def get_file_len(self):
        self.fh.seek(0, 2)
        self.len = self.fh.tell()

    def __len__(self):
        return self.len

    def asarray(self, page, segment):
        if self.tiff is not None:
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
        self.nTags[idx] = nTags
        self.tags[idx] = {}
        assert nTags < 4096, 'Too many tags'

        length = 8 if self.bigtiff else 2
        length += nTags * self.tagsize + self.offsetsize

        for i in range(nTags):
            code, ttype, caddr, dtypelen, count, value = 0, 0, 0, 0, 0, [0]
            try:
                self.fh.seek(offset + struct.calcsize(self.tagnoformat) + self.tagsize * i)

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
                elif ttype in (5, 10):
                    value = [struct.unpack(self.byteorder + dtype, self.fh.read(dtypelen)) for _ in range(count)]
                else:
                    value = [struct.unpack(self.byteorder + dtype, self.fh.read(dtypelen))[0] for _ in range(count)]

                if toolong:
                    self.fh.seek(cp)
            except Exception:
                print(format_exc())
            self.tags[idx][code] = (ttype, caddr, dtypelen*count, value)

        self.fh.seek(offset + struct.calcsize(self.tagnoformat) + self.tagsize * nTags)
        nifd = struct.unpack(self.byteorder + self.offsetformat, self.fh.read(self.offsetsize))[0]
        self.addresses[('ifd', idx)] = (offset, 2 * struct.calcsize(self.tagnoformat) + nTags * self.tagsize)
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
