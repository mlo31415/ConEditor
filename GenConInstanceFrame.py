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
## Class GenConInstanceFrame
###########################################################################

class GenConInstanceFrame ( wx.Dialog ):

	def __init__( self, parent ):
		wx.Dialog.__init__ ( self, parent, id = wx.ID_ANY, title = u"Convention Instance", pos = wx.DefaultPosition, size = wx.Size( 768,612 ), style = wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER )

		self.SetSizeHints( wx.Size( 522,606 ), wx.DefaultSize )

		bSizerMainBox = wx.BoxSizer( wx.VERTICAL )

		fgSizer5 = wx.FlexGridSizer( 1, 3, 0, 0 )
		fgSizer5.SetFlexibleDirection( wx.BOTH )
		fgSizer5.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )

		self.bUploadCon = wx.Button( self, wx.ID_ANY, u"Upload Con", wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer5.Add( self.bUploadCon, 0, wx.ALL, 5 )

		radioBoxFileListFormatChoices = [ u"Table", u"LIst" ]
		self.radioBoxFileListFormat = wx.RadioBox( self, wx.ID_ANY, u"File list format", wx.Point( -1,-1 ), wx.Size( -1,-1 ), radioBoxFileListFormatChoices, 1, wx.RA_SPECIFY_ROWS )
		self.radioBoxFileListFormat.SetSelection( 0 )
		fgSizer5.Add( self.radioBoxFileListFormat, 0, wx.ALL, 5 )

		self.bAddFiles = wx.Button( self, wx.ID_ANY, u"Add Files", wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer5.Add( self.bAddFiles, 0, wx.ALL, 5 )


		bSizerMainBox.Add( fgSizer5, 0, wx.EXPAND, 5 )

		fgSizer4 = wx.FlexGridSizer( 8, 2, 0, 0 )
		fgSizer4.SetFlexibleDirection( wx.BOTH )
		fgSizer4.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )

		self.m_staticText1 = wx.StaticText( self, wx.ID_ANY, u"Convention:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText1.Wrap( -1 )

		fgSizer4.Add( self.m_staticText1, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, 5 )

		self.tConInstanceName = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( 200,-1 ), 0 )
		fgSizer4.Add( self.tConInstanceName, 0, wx.ALL|wx.EXPAND, 5 )

		self.m_staticText11 = wx.StaticText( self, wx.ID_ANY, u"Fancy URL:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText11.Wrap( -1 )

		fgSizer4.Add( self.m_staticText11, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, 5 )

		self.tConInstanceFancyURL = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( 300,-1 ), 0 )
		fgSizer4.Add( self.tConInstanceFancyURL, 0, wx.ALL|wx.EXPAND, 5 )

		self.m_staticText14 = wx.StaticText( self, wx.ID_ANY, u"URL of photos page", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText14.Wrap( -1 )

		fgSizer4.Add( self.m_staticText14, 0, wx.ALL, 5 )

		self.m_textPhotosURL = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( 300,-1 ), 0 )
		fgSizer4.Add( self.m_textPhotosURL, 0, wx.ALL, 5 )

		self.m_staticText2 = wx.StaticText( self, wx.ID_ANY, u"Top text:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText2.Wrap( -1 )

		fgSizer4.Add( self.m_staticText2, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.ALL, 5 )

		self.topText = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( 9999,-1 ), wx.TE_MULTILINE )
		self.topText.SetMinSize( wx.Size( -1,80 ) )

		fgSizer4.Add( self.topText, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.EXPAND, 5 )


		bSizerMainBox.Add( fgSizer4, 0, wx.EXPAND, 5 )

		fgSizer9 = wx.FlexGridSizer( 0, 3, 0, 0 )
		fgSizer9.SetFlexibleDirection( wx.BOTH )
		fgSizer9.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )

		self.m_button10 = wx.Button( self, wx.ID_ANY, u"Photo page", wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer9.Add( self.m_button10, 0, wx.ALL, 5 )


		fgSizer9.Add( ( 30, 0), 0, wx.EXPAND, 5 )

		self.m_checkBoxAllowEditExtentions = wx.CheckBox( self, wx.ID_ANY, u"Allow editing of extensions", wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer9.Add( self.m_checkBoxAllowEditExtentions, 0, wx.ALL, 5 )


		bSizerMainBox.Add( fgSizer9, 1, wx.EXPAND, 5 )

		theIssueGrid = wx.BoxSizer( wx.VERTICAL )

		self.gRowGrid = wx.grid.Grid( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0 )

		# Grid
		self.gRowGrid.CreateGrid( 10, 3 )
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

		self.m_status = wx.StaticText( self, wx.ID_ANY, u"MyLabel", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_status.Wrap( -1 )

		theIssueGrid.Add( self.m_status, 0, wx.ALL, 5 )


		bSizerMainBox.Add( theIssueGrid, 1, wx.EXPAND, 5 )


		self.SetSizer( bSizerMainBox )
		self.Layout()
		self.m_menuPopup = wx.Menu()
		self.m_popupCopy = wx.MenuItem( self.m_menuPopup, wx.ID_ANY, u"Copy", wx.EmptyString, wx.ITEM_NORMAL )
		self.m_menuPopup.Append( self.m_popupCopy )

		self.m_popupPaste = wx.MenuItem( self.m_menuPopup, wx.ID_ANY, u"Paste", wx.EmptyString, wx.ITEM_NORMAL )
		self.m_menuPopup.Append( self.m_popupPaste )

		self.m_popupInsertRow = wx.MenuItem( self.m_menuPopup, wx.ID_ANY, u"Insert Row", wx.EmptyString, wx.ITEM_NORMAL )
		self.m_menuPopup.Append( self.m_popupInsertRow )

		self.m_popupAddFiles = wx.MenuItem( self.m_menuPopup, wx.ID_ANY, u"Add Files", wx.EmptyString, wx.ITEM_NORMAL )
		self.m_menuPopup.Append( self.m_popupAddFiles )

		self.m_popupDeleteFile = wx.MenuItem( self.m_menuPopup, wx.ID_ANY, u"Delete Selected Row(s)", wx.EmptyString, wx.ITEM_NORMAL )
		self.m_menuPopup.Append( self.m_popupDeleteFile )

		self.m_popupInsertText = wx.MenuItem( self.m_menuPopup, wx.ID_ANY, u"Insert Text Line", wx.EmptyString, wx.ITEM_NORMAL )
		self.m_menuPopup.Append( self.m_popupInsertText )

		self.Bind( wx.EVT_RIGHT_DOWN, self.GenConInstanceFrameOnContextMenu )


		self.Centre( wx.BOTH )

		# Connect Events
		self.Bind( wx.EVT_CLOSE, self.OnClose )
		self.bUploadCon.Bind( wx.EVT_BUTTON, self.OnUploadConInstance )
		self.radioBoxFileListFormat.Bind( wx.EVT_RADIOBOX, self.OnRadioFileListFormat )
		self.bAddFiles.Bind( wx.EVT_BUTTON, self.OnAddFilesButton )
		self.tConInstanceName.Bind( wx.EVT_KEY_UP, self.OnTextConInstanceNameKeyUp )
		self.tConInstanceName.Bind( wx.EVT_TEXT, self.OnTextConInstanceName )
		self.tConInstanceFancyURL.Bind( wx.EVT_TEXT, self.OnTextConInstanceFancyURL )
		self.m_textPhotosURL.Bind( wx.EVT_TEXT, self.OnTextPhotosURL )
		self.topText.Bind( wx.EVT_TEXT, self.OnTextComments )
		self.gRowGrid.Bind( wx.grid.EVT_GRID_CELL_CHANGED, self.OnGridCellChanged )
		self.gRowGrid.Bind( wx.grid.EVT_GRID_CELL_LEFT_DCLICK, self.OnGridCellDoubleClick )
		self.gRowGrid.Bind( wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.OnGridCellRightClick )
		self.gRowGrid.Bind( wx.grid.EVT_GRID_EDITOR_SHOWN, self.OnGridEditorShown )
		self.gRowGrid.Bind( wx.EVT_KEY_DOWN, self.OnKeyDown )
		self.gRowGrid.Bind( wx.EVT_KEY_UP, self.OnKeyUp )
		self.Bind( wx.EVT_MENU, self.OnPopupCopy, id = self.m_menuItemCopy.GetId() )
		self.Bind( wx.EVT_MENU, self.OnPopupPaste, id = self.m_menuItemPaste.GetId() )
		self.Bind( wx.EVT_MENU, self.OnPopupInsertRow, id = self.m_popupInsertRow.GetId() )
		self.Bind( wx.EVT_MENU, self.OnPopupAddFiles, id = self.m_popupAddFiles.GetId() )
		self.Bind( wx.EVT_MENU, self.OnPopupDeleteFile, id = self.m_popupDeleteFile.GetId() )
		self.Bind( wx.EVT_MENU, self.OnPopupInsertText, id = self.m_popupInsertText.GetId() )

	def __del__( self ):
		pass


	# Virtual event handlers, overide them in your derived class
	def OnClose( self, event ):
		event.Skip()

	def OnUploadConInstance( self, event ):
		event.Skip()

	def OnRadioFileListFormat( self, event ):
		event.Skip()

	def OnAddFilesButton( self, event ):
		event.Skip()

	def OnTextConInstanceNameKeyUp( self, event ):
		event.Skip()

	def OnTextConInstanceName( self, event ):
		event.Skip()

	def OnTextConInstanceFancyURL( self, event ):
		event.Skip()

	def OnTextPhotosURL( self, event ):
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

	def OnPopupInsertRow( self, event ):
		event.Skip()

	def OnPopupAddFiles( self, event ):
		event.Skip()

	def OnPopupDeleteFile( self, event ):
		event.Skip()

	def OnPopupInsertText( self, event ):
		event.Skip()

	def gRowGridOnContextMenu( self, event ):
		self.gRowGrid.PopupMenu( self.m_menu1, event.GetPosition() )

	def GenConInstanceFrameOnContextMenu( self, event ):
		self.PopupMenu( self.m_menuPopup, event.GetPosition() )


