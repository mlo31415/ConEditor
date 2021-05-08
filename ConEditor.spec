# -*- mode: python ; coding: utf-8 -*-


block_cipher = None

a = Analysis(['ConEditorFrame.py'],
             pathex=['C:\\Users\\mlo\\Documents\\usr\\Fancyclopedia\\Python\\ConEditor'],
             binaries=[],
             datas=[('Template-ConMain.html', '.'), ('Template-ConPage.html', '.'), ('Template-ConSeries.html', '.')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

#a.datas=[('Template-ConMain.html', ".")]
#a.datas=[('Template-ConMain.html', 'Template-ConMain.html', 'DATA'), 
#('Template-ConPage.html', 'Template-ConPage.html', 'DATA'), 
#('Template-ConSeries.html', 'Template-ConSeries.html', 'DATA'), 
#('index.html', 'index.html', 'DATA')]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='ConEditor',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False )
