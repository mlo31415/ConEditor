# -*- coding: utf-8 -*-

###########################################################################
## Python code generated with wxFormBuilder (version Oct 26 2018)
## http://www.wxformbuilder.org/
##
## PLEASE DO *NOT* EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc

###########################################################################
## Class dlgEnterFancyName
###########################################################################

class dlgEnterFancyName ( wx.Dialog ):

	def __init__( self, parent ):
		wx.Dialog.__init__ ( self, parent, id = wx.ID_ANY, title = u"Enter Fancyclopedia Name", pos = wx.DefaultPosition, size = wx.Size( 396,152 ), style = wx.DEFAULT_DIALOG_STYLE )

		self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )

		bSizer5 = wx.BoxSizer( wx.VERTICAL )

		self.m_staticText4 = wx.StaticText( self, wx.ID_ANY, u"To create a new convention series page, enter the name of the convention series on Fancyclopedia 3 and then press the Create button. ", wx.DefaultPosition, wx.Size( -1,30 ), 0 )
		self.m_staticText4.Wrap( 999 )

		bSizer5.Add( self.m_staticText4, 0, wx.ALL, 5 )

		bSizer6 = wx.BoxSizer( wx.HORIZONTAL )

		self.m_staticText5 = wx.StaticText( self, wx.ID_ANY, u"Name on Fancy 3:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText5.Wrap( -1 )

		bSizer6.Add( self.m_staticText5, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5 )

		self.m_textCtrl4 = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( 999,-1 ), 0 )
		bSizer6.Add( self.m_textCtrl4, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5 )


		bSizer5.Add( bSizer6, 1, wx.EXPAND, 5 )

		self.b_CreateConSeries = wx.Button( self, wx.ID_OK, u"Create Convention Series", wx.DefaultPosition, wx.DefaultSize, 0 )

		self.b_CreateConSeries.SetDefault()
		bSizer5.Add( self.b_CreateConSeries, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 5 )


		self.SetSizer( bSizer5 )
		self.Layout()

		self.Centre( wx.BOTH )

		# Connect Events
		self.m_textCtrl4.Bind( wx.EVT_TEXT, self.OnTextChanged )
		self.b_CreateConSeries.Bind( wx.EVT_BUTTON, self.OnBuCreateConSeries )

	def __del__( self ):
		pass


	# Virtual event handlers, overide them in your derived class
	def OnTextChanged( self, event ):
		event.Skip()

	def OnBuCreateConSeries( self, event ):
		event.Skip()


