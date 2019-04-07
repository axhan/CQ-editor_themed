from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QFileDialog, \
    QAction, QMenu, QWidget, QAbstractItemView
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal

from pyqtgraph.parametertree import Parameter, ParameterTree

import cadquery as cq

from OCC.AIS import AIS_ColoredShape, AIS_Line
from OCC.Quantity import Quantity_NOC_RED as RED
from OCC.Quantity import Quantity_NOC_GREEN as GREEN
from OCC.Quantity import Quantity_NOC_BLUE1 as BLUE
from OCC.Geom import Geom_CylindricalSurface, Geom_Plane, Geom_Circle,\
     Geom_TrimmedCurve, Geom_Axis1Placement, Geom_Axis2Placement, Geom_Line
from OCC.gp import gp_Trsf, gp_Vec, gp_Ax3, gp_Dir, gp_Pnt, gp_Ax1

from ..mixins import ComponentMixin
from ..icons import icon
from ..cq_utils import make_AIS, export, to_occ_color, to_workplane
from ..utils import splitter, layout

class TopTreeItem(QTreeWidgetItem):

    def __init__(self,*args,**kwargs):

        super(TopTreeItem,self).__init__(*args,**kwargs)

class ObjectTreeItem(QTreeWidgetItem):

    props = [{'name': 'Name', 'type': 'str', 'value': ''},
             {'name': 'Color', 'type': 'color', 'value': "f4da16"},
             {'name': 'Alpha', 'type': 'float', 'value': 0, 'limits': (0,1), 'step': 1e-1},
             {'name': 'Visible', 'type': 'bool','value': True}]

    def __init__(self,
                 name,
                 ais=None,
                 shape=None,
                 sig=None,
                 alpha=0.,
                 **kwargs):

        super(ObjectTreeItem,self).__init__([name],**kwargs)
        self.setFlags( self.flags() | Qt.ItemIsUserCheckable)
        self.setCheckState(0,Qt.Checked)

        self.ais = ais
        self.shape = shape
        self.sig = sig

        self.properties = Parameter.create(name='Properties',
                                           children=self.props)

        self.properties['Name'] = name
        self.properties['Alpha'] = alpha
        self.properties.sigTreeStateChanged.connect(self.propertiesChanged)

    def propertiesChanged(self,*args):

        self.setData(0,0,self.properties['Name'])
        self.ais.SetTransparency(self.properties['Alpha'])
        self.ais.SetColor(to_occ_color(self.properties['Color']))
        self.ais.Redisplay()

        if self.properties['Visible']:
            self.setCheckState(0,Qt.Checked)
        else:
            self.setCheckState(0,Qt.Unchecked)

        if self.sig:
            self.sig.emit()

class CQRootItem(TopTreeItem):

    def __init__(self,*args,**kwargs):

        super(CQRootItem,self).__init__(['CQ models'],*args,**kwargs)


class ImportRootItem(TopTreeItem):

    def __init__(self,*args,**kwargs):

        super(ImportRootItem,self).__init__(['Imports'],*args,**kwargs)

class HelpersRootItem(TopTreeItem):

    def __init__(self,*args,**kwargs):

        super(HelpersRootItem,self).__init__(['Helpers'],*args,**kwargs)


class ObjectTree(QWidget,ComponentMixin):

    name = 'Object Tree'
    _stash = []

    preferences = Parameter.create(name='Preferences',children=[
        {'name': 'Clear all before each run', 'type': 'bool', 'value': True},
        {'name': 'STL precision','type': 'float', 'value': .1}])

    sigObjectsAdded = pyqtSignal([list],[list,bool])
    sigObjectsRemoved = pyqtSignal(list)
    sigCQObjectSelected = pyqtSignal(object)
    sigItemChanged = pyqtSignal(QTreeWidgetItem,int)
    sigObjectPropertiesChanged = pyqtSignal()

    def  __init__(self,parent):

        super(ObjectTree,self).__init__(parent)

        self.tree = tree = QTreeWidget(self,
                                       selectionMode=QAbstractItemView.ExtendedSelection)
        self.properties_editor = ParameterTree(self)

        tree.setHeaderHidden(True)
        tree.setItemsExpandable(False)
        tree.setRootIsDecorated(False)
        tree.setContextMenuPolicy(Qt.ActionsContextMenu)

        #forward itemChanged singal
        tree.itemChanged.connect(\
            lambda item,col: self.sigItemChanged.emit(item,col))
        #handle visibility changes form tree
        tree.itemChanged.connect(self.handleChecked)

        self.CQ = CQRootItem()
        self.Imports = ImportRootItem()
        self.Helpers = HelpersRootItem()

        root = tree.invisibleRootItem()
        root.addChild(self.CQ)
        root.addChild(self.Imports)
        root.addChild(self.Helpers)

        self._export_STL_action = \
            QAction('Export as STL',
                    self,
                    enabled=False,
                    triggered=lambda: \
                        self.export('*stl','stl',
                                    self.preferences['STL precision']))

        self._export_STEP_action = \
            QAction('Export as STEP',
                    self,
                    enabled=False,
                    triggered=lambda: \
                        self.export('*step','step',[]))

        self._clear_current_action = QAction(icon('delete'),
                                             'Clear current',
                                             self,
                                             enabled=False,
                                             triggered=self.removeSelected)

        self._toolbar_actions = \
            [QAction(icon('delete-many'),'Clear all',self,triggered=self.removeObjects),
             self._clear_current_action,]

        self.prepareMenu()

        tree.itemSelectionChanged.connect(self.handleSelection)
        tree.customContextMenuRequested.connect(self.showMenu)

        self.prepareLayout()


    def prepareMenu(self):

        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)

        self._context_menu = QMenu(self)
        self._context_menu.addActions(self._toolbar_actions)
        self._context_menu.addActions((self._export_STL_action,
                                       self._export_STEP_action))

    def prepareLayout(self):

        self._splitter = splitter((self.tree,self.properties_editor),
                                  stretch_factors = (2,1),
                                  orientation=Qt.Vertical)
        layout(self,(self._splitter,),top_widget=self)

        self._splitter.show()

    def showMenu(self,position):

        item = self.tree.selectedItems()[-1]
        if item.parent() is self.CQ:
            self._export_STL_action.setEnabled(True)
        else:
            self._export_STL_action.setEnabled(False)

        self._context_menu.exec_(self.tree.viewport().mapToGlobal(position))


    def menuActions(self):

        return {'Tools' : [self._export_STL_action]}

    def toolbarActions(self):

        return self._toolbar_actions

    def addLines(self):

        origin = (0,0,0)
        ais_list = []

        for name,color,direction in zip(('X','Y','Z'),
                                        (RED,GREEN,BLUE),
                                        ((1,0,0),(0,1,0),(0,0,1))):
            line_placement = Geom_Line(gp_Ax1(gp_Pnt(*origin),
                                       gp_Dir(*direction)))
            line = AIS_Line(line_placement)
            line.SetColor(color)

            self.Helpers.addChild(ObjectTreeItem(name,
                                                 ais=line))

            ais_list.append(line)

        self.sigObjectsAdded.emit(ais_list)
        self.tree.expandToDepth(1)

    @pyqtSlot(dict,bool)
    @pyqtSlot(dict)
    def addObjects(self,objects,clean=False,root=None,alpha=0.):

        if root is None:
            root = self.CQ

        request_fit_view = True if root.childCount() == 0 else False

        if clean or self.preferences['Clear all before each run']:
            self.removeObjects()

        ais_list = []

        #convert cq.Shape objects to cq.Workplane
        tmp = ((k,v) if isinstance(v,cq.Workplane) else (k,to_workplane(v)) \
               for k,v in objects.items())
        #remove Vector objects
        objects_f = \
        {k:v for k,v in tmp if not isinstance(v.val(),(cq.Vector,))}

        for name,shape in objects_f.items():
            ais = make_AIS(shape)
            ais.SetTransparency(alpha)
            ais_list.append(ais)
            root.addChild(ObjectTreeItem(name,
                                         shape=shape,
                                         ais=ais,
                                         sig=self.sigObjectPropertiesChanged))

        if request_fit_view:
            self.sigObjectsAdded[list,bool].emit(ais_list,True)
        else:
            self.sigObjectsAdded[list].emit(ais_list)

    @pyqtSlot(object,str,float)
    def addObject(self,obj,name='',alpha=.0,):

        root = self.CQ

        if isinstance(obj, cq.Workplane):
            ais = make_AIS(obj)
        else:
            ais = make_AIS(to_workplane(obj))

        ais.SetTransparency(alpha)

        root.addChild(ObjectTreeItem(name,
                                     shape=obj,
                                     ais=ais,
                                     sig=self.sigObjectPropertiesChanged))

        self.sigObjectsAdded.emit([ais])

    @pyqtSlot(list)
    @pyqtSlot()
    def removeObjects(self,objects=None):

        if objects:
            removed_items_ais = [self.CQ.takeChild(i).ais for i in objects]
        else:
            removed_items_ais = [ch.ais for ch in self.CQ.takeChildren()]

        self.sigObjectsRemoved.emit(removed_items_ais)

    @pyqtSlot(bool)
    def stashObjects(self,action : bool):

        if action:
            self._stash = self.CQ.takeChildren()
            removed_items_ais = [ch.ais for ch in self._stash]
            self.sigObjectsRemoved.emit(removed_items_ais)
        else:
            self.removeObjects()
            self.CQ.addChildren(self._stash)
            ais_list = [el.ais for el in self._stash]
            self.sigObjectsAdded.emit(ais_list)

    @pyqtSlot()
    def removeSelected(self):

        ixs = self.tree.selectedIndexes()
        rows = [ix.row() for ix in ixs]

        self.removeObjects(rows)

    def export(self,file_wildcard,export_type,precision=None):

        items = self.tree.selectedItems()
        shapes = [item.shape for item in items if item.parent() is self.CQ]

        fname,_ = QFileDialog.getSaveFileName(self,filter=file_wildcard)
        if fname is not '':
             export(shapes,export_type,fname,precision)

    @pyqtSlot()
    def handleSelection(self):

        items =self.tree.selectedItems()
        if len(items) == 0:
            return

        item = items[-1]
        if item.parent() is self.CQ:
            self._export_STL_action.setEnabled(True)
            self._export_STEP_action.setEnabled(True)
            self._clear_current_action.setEnabled(True)
            self.sigCQObjectSelected.emit(item.shape)
            self.properties_editor.setParameters(item.properties,
                                                 showTop=False)
            self.properties_editor.setEnabled(True)
        else:
            self._export_STL_action.setEnabled(False)
            self._export_STEP_action.setEnabled(False)
            self._clear_current_action.setEnabled(False)
            self.properties_editor.setEnabled(False)
            self.properties_editor.clear()

    @pyqtSlot(QTreeWidgetItem,int)
    def handleChecked(self,item,col):

        if type(item) is ObjectTreeItem:
            if item.checkState(0):
                item.properties['Visible'] = True
            else:
                item.properties['Visible'] = False



