# -*- coding: utf-8 -*-

###########################################################################
## Python code generated with wxFormBuilder (version 4.2.1-0-g80c4cb6)
## http://www.wxformbuilder.org/
##
## PLEASE DO *NOT* EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc

###########################################################################
## Class GenExtrasDialog
###########################################################################

class GenExtrasDialog ( wx.Dialog ):

	def __init__( self, parent ):
		wx.Dialog.__init__ ( self, parent, id = wx.ID_ANY, title = u"Edit Extras", pos = wx.DefaultPosition, size = wx.Size( 480,210 ), style = wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER )

		self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )

		bSizerMain = wx.BoxSizer( wx.VERTICAL )

		fgSizerFields = wx.FlexGridSizer( 3, 2, 8, 8 )
		fgSizerFields.AddGrowableCol( 1 )
		fgSizerFields.SetFlexibleDirection( wx.BOTH )
		fgSizerFields.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )

		self.m_staticSpecialLink = wx.StaticText( self, wx.ID_ANY, u"Link to Other Series:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticSpecialLink.Wrap( -1 )

		self.m_staticSpecialLink.SetToolTip( u"Link the current con instance to open a con instance in another con series." )

		fgSizerFields.Add( self.m_staticSpecialLink, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5 )

		self.m_textSpecialLink = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( 380,-1 ), 0 )
		self.m_textSpecialLink.SetToolTip( u"Link the current con instance to open a con instance in another con series." )

		fgSizerFields.Add( self.m_textSpecialLink, 1, wx.ALL|wx.EXPAND, 5 )

		self.m_staticSpecialText = wx.StaticText( self, wx.ID_ANY, u"Name in Other Series:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticSpecialText.Wrap( -1 )

		self.m_staticSpecialText.SetToolTip( u"Name of the con instance in the other series." )

		fgSizerFields.Add( self.m_staticSpecialText, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5 )

		self.m_textSpecialText = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( 380,-1 ), 0 )
		self.m_textSpecialText.SetToolTip( u"Name of the con instance in the other series." )

		fgSizerFields.Add( self.m_textSpecialText, 1, wx.ALL|wx.EXPAND, 5 )

		self.m_staticNotes = wx.StaticText( self, wx.ID_ANY, u"Notes / Other:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticNotes.Wrap( -1 )

		self.m_staticNotes.SetToolTip( u"Text to be displayed following the links. Use sparingly." )

		fgSizerFields.Add( self.m_staticNotes, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5 )

		self.m_textNotes = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( 380,-1 ), 0 )
		self.m_textNotes.SetToolTip( u"Text to be displayed following the links. Use sparingly." )

		fgSizerFields.Add( self.m_textNotes, 1, wx.ALL|wx.EXPAND, 5 )


		bSizerMain.Add( fgSizerFields, 1, wx.ALL|wx.EXPAND, 8 )

		m_sdbSizer = wx.StdDialogButtonSizer()
		self.m_sdbSizerOK = wx.Button( self, wx.ID_OK )
		m_sdbSizer.AddButton( self.m_sdbSizerOK )
		self.m_sdbSizerCancel = wx.Button( self, wx.ID_CANCEL )
		m_sdbSizer.AddButton( self.m_sdbSizerCancel )
		m_sdbSizer.Realize()

		bSizerMain.Add( m_sdbSizer, 0, wx.ALL|wx.ALIGN_RIGHT, 8 )


		self.SetSizer( bSizerMain )
		self.Layout()

		self.Centre( wx.BOTH )

	def __del__( self ):
		pass


