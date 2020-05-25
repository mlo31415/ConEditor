# -*- coding: utf-8 -*-

###########################################################################
## Python code generated with wxFormBuilder (version Oct 26 2018)
## http://www.wxformbuilder.org/
##
## PLEASE DO *NOT* EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc
import wx.grid

###########################################################################
## Class GenConEditorFrame
###########################################################################

class GenConEditorFrame ( wx.Frame ):

	def __init__( self, parent ):
		wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = u"Fanac.org Convention Editor", pos = wx.DefaultPosition, size = wx.Size( 500,569 ), style = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL )

		self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )

		bSizer8 = wx.BoxSizer( wx.VERTICAL )

		fgSizer7 = wx.FlexGridSizer( 0, 4, 0, 0 )
		fgSizer7.SetFlexibleDirection( wx.BOTH )
		fgSizer7.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )

		self.m_buttonSave = wx.Button( self, wx.ID_ANY, u"Save", wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer7.Add( self.m_buttonSave, 0, wx.ALL, 5 )

		self.m_buttonSort = wx.Button( self, wx.ID_ANY, u"Sort", wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer7.Add( self.m_buttonSort, 0, wx.ALL, 5 )

		self.m_buttonExit = wx.Button( self, wx.ID_ANY, u"Exit", wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer7.Add( self.m_buttonExit, 0, wx.ALL, 5 )

		self.m_buttonSettings = wx.Button( self, wx.ID_ANY, u"Settings", wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer7.Add( self.m_buttonSettings, 0, wx.ALIGN_RIGHT|wx.ALL, 5 )


		bSizer8.Add( fgSizer7, 0, wx.EXPAND, 5 )

		bSizer7 = wx.BoxSizer( wx.VERTICAL )

		self.m_staticTextMessages = wx.StaticText( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( 400,-1 ), 0 )
		self.m_staticTextMessages.Wrap( -1 )

		bSizer7.Add( self.m_staticTextMessages, 0, wx.ALIGN_TOP|wx.ALL, 5 )


		bSizer8.Add( bSizer7, 0, wx.EXPAND, 5 )

		fgSizer8 = wx.FlexGridSizer( 0, 2, 0, 0 )
		fgSizer8.SetFlexibleDirection( wx.BOTH )
		fgSizer8.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )

		self.m_staticText12 = wx.StaticText( self, wx.ID_ANY, u"Top text:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText12.Wrap( -1 )

		fgSizer8.Add( self.m_staticText12, 0, wx.ALL, 5 )

		self.m_textCtrlTopText = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( 999,75 ), 0 )
		fgSizer8.Add( self.m_textCtrlTopText, 0, wx.ALL, 5 )


		bSizer8.Add( fgSizer8, 0, wx.EXPAND, 5 )

		bSizer9 = wx.BoxSizer( wx.VERTICAL )

		self.gRowGrid = wx.grid.Grid( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0 )

		# Grid
		self.gRowGrid.CreateGrid( 5, 5 )
		self.gRowGrid.EnableEditing( True )
		self.gRowGrid.EnableGridLines( True )
		self.gRowGrid.EnableDragGridSize( False )
		self.gRowGrid.SetMargins( 0, 0 )

		# Columns
		self.gRowGrid.EnableDragColMove( False )
		self.gRowGrid.EnableDragColSize( True )
		self.gRowGrid.SetColLabelSize( 30 )
		self.gRowGrid.SetColLabelAlignment( wx.ALIGN_CENTER, wx.ALIGN_CENTER )

		# Rows
		self.gRowGrid.EnableDragRowSize( True )
		self.gRowGrid.SetRowLabelSize( 80 )
		self.gRowGrid.SetRowLabelAlignment( wx.ALIGN_CENTER, wx.ALIGN_CENTER )

		# Label Appearance

		# Cell Defaults
		self.gRowGrid.SetDefaultCellAlignment( wx.ALIGN_LEFT, wx.ALIGN_TOP )
		self.m_menuPopupConEditor = wx.Menu()
		self.m_menuItemCopy = wx.MenuItem( self.m_menuPopupConEditor, wx.ID_ANY, u"Copy", wx.EmptyString, wx.ITEM_NORMAL )
		self.m_menuPopupConEditor.Append( self.m_menuItemCopy )

		self.m_menuItemPaste = wx.MenuItem( self.m_menuPopupConEditor, wx.ID_ANY, u"Paste", wx.EmptyString, wx.ITEM_NORMAL )
		self.m_menuPopupConEditor.Append( self.m_menuItemPaste )

		self.m_menuItemInsert = wx.MenuItem( self.m_menuPopupConEditor, wx.ID_ANY, u"Insert Convention Series", wx.EmptyString, wx.ITEM_NORMAL )
		self.m_menuPopupConEditor.Append( self.m_menuItemInsert )

		self.m_menuItemDelete = wx.MenuItem( self.m_menuPopupConEditor, wx.ID_ANY, u"Delete Convention Series", wx.EmptyString, wx.ITEM_NORMAL )
		self.m_menuPopupConEditor.Append( self.m_menuItemDelete )

		self.m_menuItemEdit = wx.MenuItem( self.m_menuPopupConEditor, wx.ID_ANY, u"Edit Convention Series", wx.EmptyString, wx.ITEM_NORMAL )
		self.m_menuPopupConEditor.Append( self.m_menuItemEdit )

		self.gRowGrid.Bind( wx.EVT_RIGHT_DOWN, self.gRowGridOnContextMenu )

		bSizer9.Add( self.gRowGrid, 1, wx.ALL, 5 )


		bSizer8.Add( bSizer9, 1, wx.EXPAND, 5 )


		self.SetSizer( bSizer8 )
		self.Layout()

		self.Centre( wx.BOTH )

		# Connect Events
		self.Bind( wx.EVT_CLOSE, self.OnClose )
		self.m_buttonSave.Bind( wx.EVT_BUTTON, self.OnButtonSaveClick )
		self.m_buttonSort.Bind( wx.EVT_BUTTON, self.OnButtonSortClick )
		self.m_buttonExit.Bind( wx.EVT_BUTTON, self.OnButtonExitClick )
		self.m_buttonSettings.Bind( wx.EVT_BUTTON, self.OnButtonSettingsClick )
		self.m_textCtrlTopText.Bind( wx.EVT_TEXT, self.OnTopTextUpdated )
		self.gRowGrid.Bind( wx.grid.EVT_GRID_CELL_CHANGED, self.OnGridCellChanged )
		self.gRowGrid.Bind( wx.grid.EVT_GRID_CELL_LEFT_DCLICK, self.OnGridCellDoubleClick )
		self.gRowGrid.Bind( wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.OnGridCellRightClick )
		self.gRowGrid.Bind( wx.grid.EVT_GRID_LABEL_RIGHT_CLICK, self.OnGridLabelRightClick )
		self.gRowGrid.Bind( wx.EVT_KEY_DOWN, self.OnKeyDown )
		self.gRowGrid.Bind( wx.EVT_KEY_UP, self.OnKeyUp )
		self.Bind( wx.EVT_MENU, self.OnPopupCopy, id = self.m_menuItemCopy.GetId() )
		self.Bind( wx.EVT_MENU, self.OnPopupPaste, id = self.m_menuItemPaste.GetId() )
		self.Bind( wx.EVT_MENU, self.OnPopupInsertCon, id = self.m_menuItemInsert.GetId() )
		self.Bind( wx.EVT_MENU, self.OnPopupDeleteCon, id = self.m_menuItemDelete.GetId() )
		self.Bind( wx.EVT_MENU, self.OnPopupEditCon, id = self.m_menuItemEdit.GetId() )

	def __del__( self ):
		pass


	# Virtual event handlers, overide them in your derived class
	def OnClose( self, event ):
		event.Skip()

	def OnButtonSaveClick( self, event ):
		event.Skip()

	def OnButtonSortClick( self, event ):
		event.Skip()

	def OnButtonExitClick( self, event ):
		event.Skip()

	def OnButtonSettingsClick( self, event ):
		event.Skip()

	def OnTopTextUpdated( self, event ):
		event.Skip()

	def OnGridCellChanged( self, event ):
		event.Skip()

	def OnGridCellDoubleClick( self, event ):
		event.Skip()

	def OnGridCellRightClick( self, event ):
		event.Skip()

	def OnGridLabelRightClick( self, event ):
		event.Skip()

	def OnKeyDown( self, event ):
		event.Skip()

	def OnKeyUp( self, event ):
		event.Skip()

	def OnPopupCopy( self, event ):
		event.Skip()

	def OnPopupPaste( self, event ):
		event.Skip()

	def OnPopupInsertCon( self, event ):
		event.Skip()

	def OnPopupDeleteCon( self, event ):
		event.Skip()

	def OnPopupEditCon( self, event ):
		event.Skip()

	def gRowGridOnContextMenu( self, event ):
		self.gRowGrid.PopupMenu( self.m_menuPopupConEditor, event.GetPosition() )


