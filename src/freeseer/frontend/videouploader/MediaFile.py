'''
Created on Nov 11, 2011

@author: jord
'''
import os
import mimetypes

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt
from freeseer.framework.presentation import PresentationFile
from freeseer.framework import uploader
from freeseer.framework.metadata import FreeseerMetadataLoader

listabsdir = lambda d: [os.path.join(str(d), f) for f in os.listdir(str(d))]
isAVmimetype = lambda t: t[0] != None and (t[0].find("video") >= 0 or t[0].find("audio") >= 0)

class MediaFileView(QtGui.QTableView):
    def __init__(self, parent=None):
        QtGui.QTableView.__init__(self, parent)
        
        self.verticalHeader().hide()
        hheader = self.horizontalHeader()
        assert isinstance(hheader, QtGui.QHeaderView)
        hheader.setHighlightSections(False)
        self.lastSort = (1, Qt.DescendingOrder)
        hheader.sortIndicatorChanged.connect(self.cancelFirstColumnSort)
        
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setSortingEnabled(True)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        
        self.setItemDelegateForColumn(0, CheckBoxDelegate(self))
        
        
    
    def setModel(self, model):
        QtGui.QTableView.setModel(self, model)
        hheader = self.horizontalHeader()
        assert isinstance(hheader, QtGui.QHeaderView)
        
        hheader.resizeSection(0,25)
        hheader.setResizeMode(0, QtGui.QHeaderView.Fixed)
        hheader.resizeSection(1, 300)
        hheader.setStretchLastSection(True)
        
        self.setColumnHidden(2, True)
        
    @QtCore.pyqtSlot(int, Qt.SortOrder)
    def cancelFirstColumnSort(self, column, order):
        if column == 0:
            column, order = self.lastSort
            self.horizontalHeader().setSortIndicator(column, order)
        else:
            self.lastSort = (column, order)

# http://stackoverflow.com/questions/3363190/
#  qt-qtableview-how-to-have-a-checkbox-only-column/7392432#7392432
# pylint: disable-msg=W0613
class CheckBoxDelegate(QtGui.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        return None
    def paint(self, painter, option, index):
        checked = bool(index.model().data(index, Qt.DisplayRole))
        check_box_style_option = QtGui.QStyleOptionButton()
    
        if index.flags() & Qt.ItemIsEditable:
            check_box_style_option.state |= QtGui.QStyle.State_Enabled
        else:
            check_box_style_option.state |= QtGui.QStyle.State_ReadOnly
    
        if checked:
            check_box_style_option.state |= QtGui.QStyle.State_On
        else:
            check_box_style_option.state |= QtGui.QStyle.State_Off
    
        check_box_style_option.rect = self.getCheckBoxRect(option)
        
#        if not index.model().hasFlag(index, Qt.ItemIsEditable):
        if not index.flags() & Qt.ItemIsEditable:
            check_box_style_option.state |= QtGui.QStyle.State_ReadOnly
    
        QtGui.QApplication.style().drawControl(QtGui.QStyle.CE_CheckBox, 
                                               check_box_style_option, painter)
    def editorEvent(self, event, model, option, index):
        '''
        Change the data in the model and the state of the checkbox
        if the user presses the left mousebutton or presses
        Key_Space or Key_Select and this cell is editable. Otherwise do nothing.
        '''
        if not index.flags() & Qt.ItemIsEditable:
            return False
    
        # Do not change the checkbox-state
        if (event.type() == QtCore.QEvent.MouseButtonRelease or 
            event.type() == QtCore.QEvent.MouseButtonDblClick):
            if (event.button() != Qt.LeftButton or 
                not self.getCheckBoxRect(option).contains(event.pos())):
                return False
            if event.type() == QtCore.QEvent.MouseButtonDblClick:
                return True
        elif event.type() == QtCore.QEvent.KeyPress:
            if event.key() != Qt.Key_Space and event.key() != Qt.Key_Select:
                return False
        else:
            return False
    
        # Change the checkbox-state
        self.setModelData(None, model, index)
        return True
    def setModelData (self, editor, model, index):
        '''
        The user wanted to change the old state in the opposite.
        '''
        newValue = not bool(index.model().data(index, Qt.DisplayRole))
        model.setData(index, newValue, Qt.EditRole)
    def getCheckBoxRect(self, option):
        check_box_style_option = QtGui.QStyleOptionButton()
        check_box_rect = QtGui.QApplication.style().subElementRect(
                QtGui.QStyle.SE_CheckBoxIndicator, check_box_style_option, None)
        check_box_point = QtCore.QPoint (option.rect.x() +
                             option.rect.width() / 2 -
                             check_box_rect.width() / 2,
                             option.rect.y() +
                             option.rect.height() / 2 -
                             check_box_rect.height() / 2)
        return QtCore.QRect(check_box_point, check_box_rect.size())
# pylint: enable-msg=W0613

class CheckableRowTableModel(QtCore.QAbstractTableModel):
    def __init__(self, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self.CHECK_COL = 0
        self.checked = {}
    
    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                if section == self.CHECK_COL:
                    return ""
    
    def data(self, index, role=QtCore.Qt.DisplayRole):
        assert isinstance(index, QtCore.QModelIndex)
        if index.column() == self.CHECK_COL:   
            if role == Qt.DisplayRole:
                return self.checked.get(index.row(), False)
            if role == Qt.CheckStateRole:
                return Qt.Unchecked
        return None
    
    def setData(self, index, value, role=Qt.EditRole):
        assert isinstance(index, QtCore.QModelIndex)
        if index.column() == self.CHECK_COL:
            if role == Qt.EditRole:
                self.checked[index.row()] = value
                self.dataChanged.emit(index, index)
    
    def flags(self, index):
        assert isinstance(index, QtCore.QModelIndex)
        if index.column() == 0:
            return Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable
#        if True:
#            return Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable
        return QtCore.QAbstractTableModel.flags(self, index)
    
    # selection modification tools #
    def checkAll(self):
        for index in self._iterCheckIndicies():
            self.setData(index, True, Qt.EditRole)
    def checkNone(self):
        for index in self._iterCheckIndicies():
            self.setData(index, False, Qt.EditRole)
    def checkInvert(self):
        for index in self._iterCheckIndicies():
            self.setData(index, not self.data(index, Qt.DisplayRole), Qt.EditRole)
    
    def _iterCheckIndicies(self):
        for row in range(0, self.rowCount()):
            yield self.index(row, self.CHECK_COL)

class MediaFileModel(CheckableRowTableModel):
    # attributes of the presentation.PresentationFile class
#    FIELD_ATTRIBUTES = {1: "filebase",
#                        2: "filepath",
#                        3: "title",
#                        4: "speaker",
#                        5: "description",
#                        6: "album",
#                        7: "duration",
#                        8: "filedate",
#                        9: "filesize"
#                        }
#    @property
#    def FIELD_HEADERS(self):
#        return         {1: self.tr("File Name"),
#                        2: self.tr("File Path"),
#                        3: self.tr("Title"),
#                        4: self.tr("Speaker"),
#                        5: self.tr("Description"),
#                        6: self.tr("Album"),
#                        7: self.tr("Duration"),
#                        8: self.tr("Date Modified"),
#                        9: self.tr("Size")}
#    NUM_FIELDS = 10
    class emptyloader(FreeseerMetadataLoader):
        def __init__(self):
            FreeseerMetadataLoader.__init__(self, None)
        def get_fields(self):
            return {}
    
    def __init__(self, parent=None, loader=None):
        CheckableRowTableModel.__init__(self, parent)
        self.setMetadataLoader(loader)
        
#        self.filedata = []
        self.filedata = [{}, {}, {}]
        self.header_data = {}
        self.header_indexkey = {}
        self.header_keyindex = {}
        
    def setDirectory(self, directory):
        # TODO: look at QtGui.QFileSystemModel
        self.beginResetModel()
        self.filedata = []
        self.endResetModel()
        
        # using qt libraries
#        qdir = QtCore.QDir(directory)
#        print [entry.absoluteFilePath() for entry in qdir.entryInfoList()]
        for f in [f for f in listabsdir(directory) 
                  if isAVmimetype(mimetypes.guess_type(f, False))]:
            self.beginInsertRows(QtCore.QModelIndex(), 
                                 len(self.filedata), len(self.filedata))
            item = self.loader.retrieve_metadata(f)
#            print item
            
            self.filedata.append(item)
            self.endInsertRows()
    
    def setMetadataLoader(self, loader):
        #TODO: actually do stuff with this
        if loader == None:
            loader = self.emptyloader()
        self.loader = loader
        self.refreshHeaders()
        
    def refreshHeaders(self):
        self.beginResetModel()
        self.header_indexkey = {}
        self.header_keyindex = {}
        
        self.header_data = self.loader.get_fields()
        
        count = 1
        for key, _ in sorted(self.header_data.iteritems(), key=lambda (k,v): v.position):
            self.header_indexkey[count] = key
            self.header_keyindex[key] = count
            count = count + 1
        
        self.endResetModel()
    
    # pylint: disable-msg=W0613
    ## Mandatory implemented abstract methods ##
    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.filedata)
    
    def columnCount(self, parent=QtCore.QModelIndex()):
#        return MediaFileModel.NUM_FIELDS
        return len(self.loader.get_fields())+1
    # pylint: enable-msg=W0613
    
    def data(self, index, role=QtCore.Qt.DisplayRole):
        assert isinstance(index, QtCore.QModelIndex)
        if role == Qt.DisplayRole or role == Qt.ToolTipRole:
            if self.header_indexkey.has_key(index.column()):
                return self.filedata[index.row()].get(self.header_indexkey[index.column()])
#                return str(index.row()) + ", " + str(index.column())
#                return (self.filedata[index.row()].get(
#                        self.header_indexkey[index.column()]), "")
        
        return CheckableRowTableModel.data(self, index, role)
    
    ## Optionally implemented abstract methods ##
#    def index(self, row, column, parent=QtCore.QModelIndex()):
#        return CheckableRowTableModel.index(row, column, parent)
    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
#                print section
                try:
                    return self.header_data[self.header_indexkey[section]].name
                except KeyError: 
                    pass
#                return self.FIELD_HEADERS.get(section,
#                          CheckableRowTableModel.headerData(self, section, 
#                                                            orientation, 
#                                                            role))
        # else
        return CheckableRowTableModel.headerData(self, section, orientation, role)

# based on gui/dialogs/qfilesystemmodel.cpp in Qt
#TODO: move this function somewhere else
def humanfilesize(nbytes):
    if nbytes == None:
        return ''
    # According to the Si standard KB is 1000 bytes, KiB is 1024
    # but on windows sizes are calculated by dividing by 1024 so we do what they do.
    kb = 1024
    mb = 1024 * kb
    gb = 1024 * mb
    tb = 1024 * gb
    if (nbytes >= tb):
        return QtCore.QCoreApplication.translate("QFileSystemDialog", "%1 TB").arg(QtCore.QLocale().toString(float(nbytes) / tb, 'f', 3))
    if (nbytes >= gb):
        return QtCore.QCoreApplication.translate("QFileSystemDialog", "%1 GB").arg(QtCore.QLocale().toString(float(nbytes) / gb, 'f', 2))
    if (nbytes >= mb):
        return QtCore.QCoreApplication.translate("QFileSystemDialog", "%1 MB").arg(QtCore.QLocale().toString(float(nbytes) / mb, 'f', 1))
    if (nbytes >= kb):
        return QtCore.QCoreApplication.translate("QFileSystemDialog", "%1 KB").arg(QtCore.QLocale().toString(nbytes / kb))
    return QtCore.QCoreApplication.translate("QFileSystemDialog", "%1 bytes").arg(QtCore.QLocale().toString(nbytes))
   

class MediaFileItem(QtCore.QObject):
    def __init__(self, parent=None):
        QtCore.QObject.__init__(self, parent)
        self.data = PresentationFile("default")
    filebase    = property(lambda self: self.data.filebase)
    filepath    = property(lambda self: self.data.filepath)
    title       = property(lambda self: self.data.title)
    speaker     = property(lambda self: self.data.speaker)
    description = property(lambda self: self.data.description)
    album       = property(lambda self: self.data.album)
    duration    = property(lambda self: self.data.duration)
    filedate    = property(lambda self: None if self.data.filedate == None else 
                           QtCore.QDateTime.fromTime_t(int(self.data.filedate)))
    filesize    = property(lambda self: humanfilesize(self.data.filesize))
    
if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    
    filelist = MediaFileView()
    filelist.resize(QtCore.QSize(320,320))
    
    filemodel = MediaFileModel(filelist)
#    filemodel.in
    filelist.setModel(filemodel)
#    filelist.horizontalHeader().resizeSections(QtGui.QHeaderView.ResizeToContents)
#    filelist.horizontalHeader().resizeSection(0,25)
    
#    filelist_model = QtGui.QFileSystemModel()
#    filelist_model.setRootPath("file:///home/")
#    filelist_model = QtGui.QStandardItemModel()
#    filelist_model.setColumnCount(3)
#    
#    from random import randint
#    for _ in range(10):
#        item = QtGui.QStandardItem('Item %s' % randint(1, 100))
#        check = QtCore.Qt.Checked if randint(0, 1) == 1 else QtCore.Qt.Unchecked
#        item.setColumnCount(3)
#        item.setCheckState(check)
#        item.setCheckable(True)
#        item.setEditable(False)
#        filelist_model.appendRow(item)
#    filelist.setModel(filelist_model)
    
    
    filelist.show()
    sys.exit(app.exec_())