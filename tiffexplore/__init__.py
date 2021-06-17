#!/usr/bin/env python3

from PyQt5 import QtCore, QtWidgets, QtGui
from os.path import isfile, basename
from sys import argv

if __package__ is None:
    import tiffread
else:
    from . import tiffread


class UiMainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.resize(800, 600)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centrallayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.scrollArea = QtWidgets.QScrollArea(self.centralwidget)
        self.scrollArea.setFixedWidth(150)
        self.scrollArea.setMinimumHeight(200)
        self.scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.scrollArea.setWidgetResizable(True)
        self.leftcolumnWidget = QtWidgets.QWidget()
        self.leftcolumnWidget.setFixedWidth(130)
        self.leftcolumnWidget.setMinimumHeight(200)
        self.verticalLayoutWidget = QtWidgets.QWidget(self.leftcolumnWidget)
        self.verticalLayoutWidget.setFixedWidth(130)
        self.verticalLayoutWidget.setMinimumHeight(200)
        self.leftcolumn = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.leftcolumn.setContentsMargins(0, 0, 0, 0)
        self.scrollArea.setWidget(self.leftcolumnWidget)
        self.middlecolumnWidget = QtWidgets.QWidget()
        self.middlecolumn = QtWidgets.QVBoxLayout(self.middlecolumnWidget)
        self.middlecolumn.setContentsMargins(0, 0, 0, 0)
        self.properties = QtWidgets.QTextEdit(self.centralwidget)
        self.properties.setReadOnly(True)
        self.middlecolumn.addWidget(self.properties)
        self.rightcolumnWidget = QtWidgets.QWidget()
        self.rightcolumn = QtWidgets.QVBoxLayout(self.rightcolumnWidget)
        self.rightcolumn.setContentsMargins(0, 0, 0, 0)
        self.binary = QtWidgets.QTextEdit(self.rightcolumnWidget)
        self.binary.setReadOnly(True)
        self.rightcolumn.addWidget(self.binary)
        self.image = QtWidgets.QLabel(self.rightcolumnWidget)
        self.image.setMinimumWidth(200)
        self.image.setMinimumHeight(200)
        self.rightcolumn.addWidget(self.image)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 22))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionOpen = QtWidgets.QAction(MainWindow)
        self.actionOpen.setObjectName("actionOpen")
        self.menuFile.addAction(self.actionOpen)
        self.menubar.addAction(self.menuFile.menuAction())
        self.centrallayout.addWidget(self.scrollArea)
        self.centrallayout.addWidget(self.middlecolumnWidget)
        self.centrallayout.addWidget(self.rightcolumnWidget)
        self.centralwidget.setLayout(self.centrallayout)
        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "TiffExp"))
        self.menuFile.setTitle(_translate("MainWindow", "File"))
        self.actionOpen.setText(_translate("MainWindow", "Open"))
        self.actionOpen.setShortcut(_translate("MainWindow", "Ctrl+O"))


class PaintBox(QtWidgets.QWidget):
    def drawText(self, qp, rect, text):
        qp.setPen(QtGui.QColor('black'))
        qp.setFont(QtGui.QFont('Decorative', 10 if rect[3] > 20 else rect[3] // 2))
        qp.drawText(QtCore.QRect(*rect), QtCore.Qt.AlignCenter, text)

    def drawRectangle(self, qp, rect, color):
        color = QtGui.QColor(color) if isinstance(color, str) else QtGui.QColor(*color)
        qp.setPen(QtGui.QColor('gray'))
        qp.setBrush(color)
        qp.drawRect(*rect)

class Legend(PaintBox):
    def __init__(self, parent):
        self.parent = parent
        self.color = {'header': 'red', 'ifd': 'cyan', 'tagdata': 'lightgreen', 'image': 'yellow', 'empty': 'white',
                      'shared tagdata': 'green', 'shared image': 'orange', 'unknown': 'gray'}
        super().__init__()
        self.setFixedHeight(120)
        self.show()

    def paintEvent(self, *args, **kwargs):
        qp = QtGui.QPainter()
        qp.begin(self)
        for i, (key, value) in enumerate(self.color.items()):
            self.drawRectangle(qp, (0, 15*i, 125, 15), value)
            self.drawText(qp, (0, 15*i, 125, 15), key)
        qp.end()


class Bar(PaintBox):
    def __init__(self, parent):
        self.parent = parent
        self.color = {'header': 'red', 'ifd': 'cyan', 'tagdata': 'lightgreen', 'image': 'yellow', 'empty': 'white',
                      'HEADER': 'red', 'IFD': 'blue', 'TAGDATA': 'green', 'IMAGE': 'orange', 'EMPTY': 'white'}
        self.tiff = None
        self.bar = tiffread.assignments()
        super().__init__()
        self.setFixedWidth(150)
        self.show()

    def new_file(self):
        self.tiff = self.parent.tiff
        self.bar = tiffread.assignments() if self.tiff is None else self.get_bar()
        self.parent.leftcolumnWidget.setFixedHeight(self.bar.max_addr)
        self.parent.verticalLayoutWidget.setFixedHeight(self.bar.max_addr)

    def paintEvent(self, *args, **kwargs):
        qp = QtGui.QPainter()
        qp.begin(self)
        self.parent.leftcolumnWidget.setFixedHeight(self.bar.max_addr)
        self.parent.verticalLayoutWidget.setFixedHeight(self.bar.max_addr)
        for key, value in self.bar.items():
            self.drawRectangle(qp, (0, value[0], 125, value[1]), self.color.get(key[0], "gray"))
            self.drawText(qp, (0, value[0], 125, value[1]), ('_'.join(('{}',) * len(key))).format(*key).lower())
        qp.end()

    def get_bar(self):
        min_size = 10
        scale = 100
        bar = tiffread.assignments()
        pos = 0
        for item in self.tiff.addresses.get_assignments():
            key, value = item[0]
            size = value[1] // scale if value[1] // scale >= min_size else min_size
            if not (key[0].lower() == 'empty' and value[1] == 1):
                if key[0].lower() == 'empty':
                    bar[('empty', value[0] + value[1] // 2)] = (pos, size)
                else:
                    if len(item) > 1:
                        bar[(key[0].upper(),) + key[1:]] = (pos, size)
                    else:
                        bar[key] = (pos, size)
                pos += size

        bar.max_addr = pos
        return bar

    def mousePressEvent(self, event):
        keys, vals = zip(*self.bar.get_assignment(event.localPos().y()))
        key, val = keys[0], vals[0]
        if key[0].lower() == 'empty':
            addr = key[1]
        else:
            addr = self.tiff.addresses[(key[0].lower(),) + key[1:]]
            addr = addr[0] + addr[1] // 2
        keys, addrs = zip(*self.parent.tiff.addresses.get_assignment(addr))
        addr = addrs[0]

        text = [('_'.join(('{}',) * len(key))).format(*key) for key in keys]
        text.append('')
        text.append(f'Adresses: {addr[0]} - {sum(addr)}')
        text.append(f'Length: {addr[1]}')
        if key[0].lower() == 'header':
            text.append(f'\nFile size: {len(self.tiff)}')
            text.append(f'Byte order: {self.tiff.byteorder}')
            text.append(f'Big tiff: {self.tiff.bigtiff}')
            text.append(f'Tag size: {self.tiff.tagsize}')
            text.append(f'Tag number format: {self.tiff.tagnoformat}')
            text.append(f'Offset size: {self.tiff.offsetsize}')
            text.append(f'Offset format: {self.tiff.offsetformat}')
            text.append(f'First ifd offset: {self.tiff.offsets[0]}')
        if key[0].lower() == 'ifd':
            text.append(f'Number of tags: {self.tiff.nTags[key[1]]}\n')
            text.extend([self.tiff.fmt_tag(k, v)+'\n' for k, v in self.tiff.tags[key[1]].items()])
            if key[1] < len(self.tiff.offsets) - 1:
                text.append(f'Next ifd offset: {self.tiff.offsets[key[1] + 1]}')
        if key[0].lower() == 'tagdata':
            text.append('\n' + self.tiff.fmt_tag(key[2], self.tiff.tags[key[1]][key[2]]))
        if key[0].lower() == 'image':
            im = self.tiff.asarray(key[1], key[2])
            text.append(f'\nStrip size: {im.shape}')
            text.append(f'Data type: {im.dtype}')
            self.parent.setImage(im)
        else:
            self.parent.setImage()
        self.parent.properties.setText('\n'.join(text))
        self.parent.binary.setText(''.join([chr(i) for i in self.tiff[addr[0]:addr[0]+addr[1]]]))


class App(QtWidgets.QMainWindow, UiMainWindow):
    def __init__(self, tiff=None):
        super().__init__()
        self.tiff = None
        self.setupUi(self)
        self.bar = Bar(self)
        self.leftcolumn.addWidget(self.bar)
        self.legend = Legend(self)
        self.middlecolumn.addWidget(self.legend)
        self.actionOpen.triggered.connect(self.openDialog)
        self.open(tiff)
        self.show()

    def setImage(self, *args):
        if len(args):
            im = args[0]
            if im.ndim == 3:
                im = im.transpose(2, 0, 1).reshape((im.shape[0]*im.shape[2], im.shape[1]))
            if im.max() - im.min() > 0:
                im = (255 * ((im - im.min()) / (im.max() - im.min()))).astype('uint8')
            shape = im.shape
            im = QtGui.QImage(im, im.shape[1], im.shape[0], QtGui.QImage.Format_Grayscale8)
            f = min([a / b for a, b in zip((self.image.height(), self.image.width()), shape)])
            pix = QtGui.QPixmap(im).scaled(f * shape[1], f * shape[0])
        else:
            pix = QtGui.QPixmap()
        self.image.setPixmap(pix)

    def openDialog(self):
        file, _ = QtWidgets.QFileDialog.getOpenFileName(self,
                    "Open config file", "", "TIFF Files (*.tif *.tiff);;All Files (*)",
                    options=(QtWidgets.QFileDialog.Options() | QtWidgets.QFileDialog.DontUseNativeDialog))
        self.open(file)

    def open(self, file):
        if file is not None and isfile(file):
            if self.tiff is not None:
                self.tiff.close()
            self.tiff = tiffread.tiff(file)
            self.bar.new_file()
            self.setWindowTitle(f'TiffExp: {basename(self.tiff.file)}')

    def closeEvent(self, *args, **kwargs):
        if self.tiff is not None:
            self.tiff.close()


def main():
    app = QtWidgets.QApplication([])
    w = App(argv[1]) if len(argv) > 1 else App()
    exit(app.exec())


if __name__ == '__main__':
    main()
