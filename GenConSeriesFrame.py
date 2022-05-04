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
## Class GenConSeriesFrame
###########################################################################

class GenConSeriesFrame ( wx.Dialog ):

	def __init__( self, parent ):
		wx.Dialog.__init__ ( self, parent, id = wx.ID_ANY, title = u"Edit Convention Series", pos = wx.DefaultPosition, size = wx.Size( 700,682 ), style = wx.CLOSE_BOX|wx.DEFAULT_DIALOG_STYLE|wx.MAXIMIZE_BOX|wx.MINIMIZE_BOX|wx.RESIZE_BORDER )

		self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )

		bSizerMainBox = wx.BoxSizer( wx.VERTICAL )

		fgSizer6 = wx.FlexGridSizer( 2, 4, 0, 0 )
		fgSizer6.AddGrowableRow( 1 )
		fgSizer6.SetFlexibleDirection( wx.BOTH )
		fgSizer6.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )

		self.bUploadConSeries = wx.Button( self, wx.ID_ANY, u"Upload ConSeries", wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer6.Add( self.bUploadConSeries, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5 )

		self.m_panel2 = wx.Panel( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.BORDER_THEME|wx.TAB_TRAVERSAL )
		fgSizer8 = wx.FlexGridSizer( 2, 0, 0, 0 )
		fgSizer8.SetFlexibleDirection( wx.BOTH )
		fgSizer8.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )

		self.m_staticText13 = wx.StaticText( self.m_panel2, wx.ID_ANY, u"HTML Output", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText13.Wrap( -1 )

		fgSizer8.Add( self.m_staticText13, 0, wx.ALL, 5 )

		m_radioBoxShowEmptyChoices = [ u"Yes", u"No" ]
		self.m_radioBoxShowEmpty = wx.RadioBox( self.m_panel2, wx.ID_ANY, u"Show empty cons?", wx.DefaultPosition, wx.DefaultSize, m_radioBoxShowEmptyChoices, 1, wx.RA_SPECIFY_ROWS )
		self.m_radioBoxShowEmpty.SetSelection( 0 )
		fgSizer8.Add( self.m_radioBoxShowEmpty, 0, wx.ALL, 5 )


		self.m_panel2.SetSizer( fgSizer8 )
		self.m_panel2.Layout()
		fgSizer8.Fit( self.m_panel2 )
		fgSizer6.Add( self.m_panel2, 1, wx.EXPAND |wx.ALL, 5 )

		self.bLoadSeriesFromFancy = wx.Button( self, wx.ID_ANY, u"Load New ConSeries from Fancy 3", wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer6.Add( self.bLoadSeriesFromFancy, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5 )

		self.m_Cancel = wx.Button( self, wx.ID_OK, u"Exit", wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer6.Add( self.m_Cancel, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5 )


		bSizerMainBox.Add( fgSizer6, 0, wx.EXPAND, 5 )

		fgSizer4 = wx.FlexGridSizer( 0, 2, 0, 0 )
		fgSizer4.SetFlexibleDirection( wx.BOTH )
		fgSizer4.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )

		self.m_staticText1 = wx.StaticText( self, wx.ID_ANY, u"Convention Series Name:", wx.DefaultPosition, wx.DefaultSize, 0 )
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
		fgSizerComments.AddGrowableRow( 0 )
		fgSizerComments.SetFlexibleDirection( wx.BOTH )
		fgSizerComments.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )

		self.m_staticText2 = wx.StaticText( self, wx.ID_ANY, u"Top text:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText2.Wrap( -1 )

		fgSizerComments.Add( self.m_staticText2, 0, wx.ALL, 5 )

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

		bSizer7 = wx.BoxSizer( wx.VERTICAL )

		self.m_status = wx.StaticText( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( 400,-1 ), 0 )
		self.m_status.Wrap( -1 )

		bSizer7.Add( self.m_status, 0, wx.ALIGN_TOP|wx.ALL, 5 )


		bSizerMainBox.Add( bSizer7, 0, wx.ALIGN_TOP|wx.EXPAND, 5 )


		self.SetSizer( bSizerMainBox )
		self.Layout()
		self.m_GridPopup = wx.Menu()
		self.m_popupCopy = wx.MenuItem( self.m_GridPopup, wx.ID_ANY, u"Copy", wx.EmptyString, wx.ITEM_NORMAL )
		self.m_GridPopup.Append( self.m_popupCopy )

		self.m_popupPaste = wx.MenuItem( self.m_GridPopup, wx.ID_ANY, u"Paste", wx.EmptyString, wx.ITEM_NORMAL )
		self.m_GridPopup.Append( self.m_popupPaste )

		self.m_popupCreateNewConPage = wx.MenuItem( self.m_GridPopup, wx.ID_ANY, u"Create New Convention Page", wx.EmptyString, wx.ITEM_NORMAL )
		self.m_GridPopup.Append( self.m_popupCreateNewConPage )

		self.m_popupDeleteConPage = wx.MenuItem( self.m_GridPopup, wx.ID_ANY, u"Delete Convention Page", wx.EmptyString, wx.ITEM_NORMAL )
		self.m_GridPopup.Append( self.m_popupDeleteConPage )

		self.m_popupEditConPage = wx.MenuItem( self.m_GridPopup, wx.ID_ANY, u"Edit Convention Page", wx.EmptyString, wx.ITEM_NORMAL )
		self.m_GridPopup.Append( self.m_popupEditConPage )

		self.m_popupAllowEditCell = wx.MenuItem( self.m_GridPopup, wx.ID_ANY, u"Allow Cell Edit", wx.EmptyString, wx.ITEM_NORMAL )
		self.m_GridPopup.Append( self.m_popupAllowEditCell )

		self.m_popupUnlink = wx.MenuItem( self.m_GridPopup, wx.ID_ANY, u"Unlink", wx.EmptyString, wx.ITEM_NORMAL )
		self.m_GridPopup.Append( self.m_popupUnlink )

		self.m_popupChangeConSeries = wx.MenuItem( self.m_GridPopup, wx.ID_ANY, u"Change Convention Series", wx.EmptyString, wx.ITEM_NORMAL )
		self.m_GridPopup.Append( self.m_popupChangeConSeries )

		self.Bind( wx.EVT_RIGHT_DOWN, self.GenConSeriesFrameOnContextMenu )


		self.Centre( wx.BOTH )

		# Connect Events
		self.Bind( wx.EVT_CLOSE, self.OnClose )
		self.bUploadConSeries.Bind( wx.EVT_BUTTON, self.OnUploadConSeries )
		self.m_radioBoxShowEmpty.Bind( wx.EVT_RADIOBOX, self.OnSetShowEmptyRadioBox )
		self.bLoadSeriesFromFancy.Bind( wx.EVT_BUTTON, self.OnLoadSeriesFromFancy )
		self.m_Cancel.Bind( wx.EVT_BUTTON, self.OnClose )
		self.tConSeries.Bind( wx.EVT_KEY_UP, self.ConTextConSeriesKeyUp )
		self.tConSeries.Bind( wx.EVT_TEXT, self.OnTextConSeriesName )
		self.tFancyURL.Bind( wx.EVT_TEXT, self.OnTextFancyURL )
		self.tComments.Bind( wx.EVT_TEXT, self.OnTextComments )
		self.gRowGrid.Bind( wx.grid.EVT_GRID_CELL_CHANGED, self.OnGridCellChanged )
		self.gRowGrid.Bind( wx.grid.EVT_GRID_CELL_LEFT_DCLICK, self.OnGridCellDoubleClick )
		self.gRowGrid.Bind( wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.OnGridCellRightClick )
		self.gRowGrid.Bind( wx.grid.EVT_GRID_EDITOR_SHOWN, self.OnGridEditorShown )
		self.gRowGrid.Bind( wx.EVT_KEY_DOWN, self.OnKeyDown )
		self.gRowGrid.Bind( wx.EVT_KEY_UP, self.OnKeyUp )
		self.Bind( wx.EVT_MENU, self.OnPopupCopy, id = self.m_menuItemCopy.GetId() )
		self.Bind( wx.EVT_MENU, self.OnPopupPaste, id = self.m_menuItemPaste.GetId() )
		self.Bind( wx.EVT_MENU, self.OnPopupCreateNewConPage, id = self.m_popupCreateNewConPage.GetId() )
		self.Bind( wx.EVT_MENU, self.OnPopupDeleteConPage, id = self.m_popupDeleteConPage.GetId() )
		self.Bind( wx.EVT_MENU, self.OnPopupEditConPage, id = self.m_popupEditConPage.GetId() )
		self.Bind( wx.EVT_MENU, self.OnPopupAllowEditCell, id = self.m_popupAllowEditCell.GetId() )
		self.Bind( wx.EVT_MENU, self.OnPopupUnlink, id = self.m_popupUnlink.GetId() )
		self.Bind( wx.EVT_MENU, self.OnPopupChangeConSeries, id = self.m_popupChangeConSeries.GetId() )

	def __del__( self ):
		pass


	# Virtual event handlers, overide them in your derived class
	def OnClose( self, event ):
		event.Skip()

	def OnUploadConSeries( self, event ):
		event.Skip()

	def OnSetShowEmptyRadioBox( self, event ):
		event.Skip()

	def OnLoadSeriesFromFancy( self, event ):
		event.Skip()


	def ConTextConSeriesKeyUp( self, event ):
		event.Skip()

	def OnTextConSeriesName( self, event ):
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

	def OnGridEditorShown( self, event ):
		event.Skip()

	def OnKeyDown( self, event ):
		event.Skip()

	def OnKeyUp( self, event ):
		event.Skip()

	def OnPopupCopy( self, event ):
		event.Skip()

	def OnPopupPaste( self, event ):
		event.Skip()

	def OnPopupCreateNewConPage( self, event ):
		event.Skip()

	def OnPopupDeleteConPage( self, event ):
		event.Skip()

	def OnPopupEditConPage( self, event ):
		event.Skip()

	def OnPopupAllowEditCell( self, event ):
		event.Skip()

	def OnPopupUnlink( self, event ):
		event.Skip()

	def OnPopupChangeConSeries( self, event ):
		event.Skip()

	def gRowGridOnContextMenu( self, event ):
		self.gRowGrid.PopupMenu( self.m_menu1, event.GetPosition() )

	def GenConSeriesFrameOnContextMenu( self, event ):
		self.PopupMenu( self.m_GridPopup, event.GetPosition() )


