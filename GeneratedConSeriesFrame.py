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
## Class MainConSeriesFrame
###########################################################################

class MainConSeriesFrame ( wx.Frame ):

	def __init__( self, parent ):
		wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = u"Edit Convention Series", pos = wx.Point( -1,15 ), size = wx.Size( 729,452 ), style = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL )

		self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )

		self.m_toolBar2 = self.CreateToolBar( wx.TB_HORIZONTAL, wx.ID_ANY )
		self.bLoadConSeries = wx.Button( self.m_toolBar2, wx.ID_ANY, u"Load ConSeries from Fanac.org", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_toolBar2.AddControl( self.bLoadConSeries )
		self.bSaveConSeries = wx.Button( self.m_toolBar2, wx.ID_ANY, u"Save ConSeries to Fanac.org", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_toolBar2.AddControl( self.bSaveConSeries )
		self.bCreateConSeries = wx.Button( self.m_toolBar2, wx.ID_ANY, u"Create New ConSeries", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_toolBar2.AddControl( self.bCreateConSeries )
		self.m_toolBar2.Realize()

		bSizerMainBox = wx.BoxSizer( wx.VERTICAL )

		fgSizer4 = wx.FlexGridSizer( 0, 2, 0, 0 )
		fgSizer4.SetFlexibleDirection( wx.BOTH )
		fgSizer4.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )

		self.m_staticText1 = wx.StaticText( self, wx.ID_ANY, u"Convention Series:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText1.Wrap( -1 )

		fgSizer4.Add( self.m_staticText1, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.ALL, 5 )

		self.tConSeries = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( 100,25 ), 0 )
		self.tConSeries.SetMaxSize( wx.Size( -1,25 ) )

		fgSizer4.Add( self.tConSeries, 0, wx.ALL|wx.EXPAND, 5 )

		self.m_staticText11 = wx.StaticText( self, wx.ID_ANY, u"URL on Fancyclopedia", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText11.Wrap( -1 )

		fgSizer4.Add( self.m_staticText11, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.ALL, 5 )

		self.tFancyURL = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( 9999,-1 ), 0 )
		self.tFancyURL.SetMaxSize( wx.Size( -1,25 ) )

		fgSizer4.Add( self.tFancyURL, 0, wx.ALL|wx.EXPAND, 5 )


		bSizerMainBox.Add( fgSizer4, 0, wx.EXPAND, 5 )

		fgSizerComments = wx.FlexGridSizer( 1, 2, 0, 0 )
		fgSizerComments.AddGrowableCol( 1 )
		fgSizerComments.AddGrowableRow( 0 )		# This needs to be set by hand to ( 0 ) due to apparent bug in wxFormBuilder
		fgSizerComments.SetFlexibleDirection( wx.BOTH )
		fgSizerComments.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )

		self.m_staticText2 = wx.StaticText( self, wx.ID_ANY, u"Top text:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText2.Wrap( -1 )

		fgSizerComments.Add( self.m_staticText2, 1, wx.ALL, 5 )

		self.tComments = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( 9999,-1 ), wx.TE_MULTILINE )
		self.tComments.SetMinSize( wx.Size( -1,80 ) )

		fgSizerComments.Add( self.tComments, 1, wx.ALL|wx.EXPAND, 5 )


		bSizerMainBox.Add( fgSizerComments, 0, wx.ALL|wx.EXPAND, 5 )

		theIssueGrid = wx.BoxSizer( wx.VERTICAL )

		self.gRowGrid = wx.grid.Grid( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0 )

		# Grid
		self.gRowGrid.CreateGrid( 10, 6 )
		self.gRowGrid.EnableEditing( True )
		self.gRowGrid.EnableGridLines( True )
		self.gRowGrid.EnableDragGridSize( False )
		self.gRowGrid.SetMargins( 0, 0 )

		# Columns
		self.gRowGrid.AutoSizeColumns()
		self.gRowGrid.EnableDragColMove( True )
		self.gRowGrid.EnableDragColSize( True )
		self.gRowGrid.SetColLabelSize( 30 )
		self.gRowGrid.SetColLabelAlignment( wx.ALIGN_CENTER, wx.ALIGN_CENTER )

		# Rows
		self.gRowGrid.AutoSizeRows()
		self.gRowGrid.EnableDragRowSize( False )
		self.gRowGrid.SetRowLabelSize( 80 )
		self.gRowGrid.SetRowLabelAlignment( wx.ALIGN_CENTER, wx.ALIGN_CENTER )

		# Label Appearance

		# Cell Defaults
		self.gRowGrid.SetDefaultCellAlignment( wx.ALIGN_LEFT, wx.ALIGN_TOP )
		self.m_menu1 = wx.Menu()
		self.m_menuItemCopy = wx.MenuItem( self.m_menu1, wx.ID_ANY, u"Copy", wx.EmptyString, wx.ITEM_NORMAL )
		self.m_menu1.Append( self.m_menuItemCopy )

		self.m_menuItemPaste = wx.MenuItem( self.m_menu1, wx.ID_ANY, u"Paste", wx.EmptyString, wx.ITEM_NORMAL )
		self.m_menu1.Append( self.m_menuItemPaste )

		self.gRowGrid.Bind( wx.EVT_RIGHT_DOWN, self.gRowGridOnContextMenu )

		theIssueGrid.Add( self.gRowGrid, 0, wx.ALL|wx.EXPAND, 5 )


		bSizerMainBox.Add( theIssueGrid, 1, wx.EXPAND, 5 )


		self.SetSizer( bSizerMainBox )
		self.Layout()
		self.m_menuPopup = wx.Menu()
		self.m_popupCopy = wx.MenuItem( self.m_menuPopup, wx.ID_ANY, u"Copy", wx.EmptyString, wx.ITEM_NORMAL )
		self.m_menuPopup.Append( self.m_popupCopy )

		self.m_popupPaste = wx.MenuItem( self.m_menuPopup, wx.ID_ANY, u"Paste", wx.EmptyString, wx.ITEM_NORMAL )
		self.m_menuPopup.Append( self.m_popupPaste )

		self.m_popupCreateNewConPage = wx.MenuItem( self.m_menuPopup, wx.ID_ANY, u"Create New Con Page", wx.EmptyString, wx.ITEM_NORMAL )
		self.m_menuPopup.Append( self.m_popupCreateNewConPage )

		self.Bind( wx.EVT_RIGHT_DOWN, self.MainConSeriesFrameOnContextMenu )


		self.Centre( wx.BOTH )

		# Connect Events
		self.bLoadConSeries.Bind( wx.EVT_BUTTON, self.OnLoadConSeries )
		self.bSaveConSeries.Bind( wx.EVT_BUTTON, self.OnSaveConSeries )
		self.bCreateConSeries.Bind( wx.EVT_BUTTON, self.OnCreateConSeries )
		self.tConSeries.Bind( wx.EVT_TEXT, self.OnTextConSeries )
		self.tFancyURL.Bind( wx.EVT_TEXT, self.OnTextFancyURL )
		self.tComments.Bind( wx.EVT_TEXT, self.OnTextComments )
		self.gRowGrid.Bind( wx.grid.EVT_GRID_CELL_CHANGED, self.OnGridCellChanged )
		self.gRowGrid.Bind( wx.grid.EVT_GRID_CELL_LEFT_DCLICK, self.OnGridCellDoubleClick )
		self.gRowGrid.Bind( wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.OnGridCellRightClick )
		self.gRowGrid.Bind( wx.EVT_KEY_DOWN, self.OnKeyDown )
		self.gRowGrid.Bind( wx.EVT_KEY_UP, self.OnKeyUp )
		self.Bind( wx.EVT_MENU, self.OnPopupCopy, id = self.m_menuItemCopy.GetId() )
		self.Bind( wx.EVT_MENU, self.OnPopupPaste, id = self.m_menuItemPaste.GetId() )
		self.Bind( wx.EVT_MENU, self.OnCreateNewConPage, id = self.m_popupCreateNewConPage.GetId() )

	def __del__( self ):
		pass


	# Virtual event handlers, overide them in your derived class
	def OnLoadConSeries( self, event ):
		event.Skip()

	def OnSaveConSeries( self, event ):
		event.Skip()

	def OnCreateConSeries( self, event ):
		event.Skip()

	def OnTextConSeries( self, event ):
		event.Skip()

	def OnTextFancyURL( self, event ):
		event.Skip()

	def OnTextComments( self, event ):
		event.Skip()

	def OnGridCellChanged( self, event ):
		event.Skip()

	def OnGridCellDoubleClick( self, event ):
		event.Skip()

	def OnGridCellRightClick( self, event ):
		event.Skip()

	def OnKeyDown( self, event ):
		event.Skip()

	def OnKeyUp( self, event ):
		event.Skip()

	def OnPopupCopy( self, event ):
		event.Skip()

	def OnPopupPaste( self, event ):
		event.Skip()

	def OnCreateNewConPage( self, event ):
		event.Skip()

	def gRowGridOnContextMenu( self, event ):
		self.gRowGrid.PopupMenu( self.m_menu1, event.GetPosition() )

	def MainConSeriesFrameOnContextMenu( self, event ):
		self.PopupMenu( self.m_menuPopup, event.GetPosition() )

