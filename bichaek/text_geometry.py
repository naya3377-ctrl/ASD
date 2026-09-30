"""Carry PDF line origins and character advances into the live text document.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
from PySide6.QtGui import QTextCursor,QTextCharFormat,QTextBlockFormat,QFont,QFontMetricsF
from PySide6.QtCore import Qt

SPACING=1048576+4  # QTextFormat.UserProperty + 4

def units(text):return len(text.encode('utf-16-le'))//2

def build_lines(editor,cursor):
    doc=editor.doc;lines=editor.target['textLines'];left=editor.target['rect'][0]
    records=[]
    for index,line in enumerate(lines):
        bf=QTextBlockFormat();bf.setLeftMargin(max(0,line['origin'][0]-left));bf.setAlignment(Qt.AlignLeft)
        if index:cursor.insertBlock(bf)
        else:cursor.setBlockFormat(bf)
        chars=[]
        for run in line['runs']:
            base=editor._format(run['font'],run['size'],'#%06x'%run['color'],run['flags'])
            font=base.font();font.setKerning(False);font.setStyleStrategy(QFont.PreferNoShaping);base.setFont(font)
            for char in run['chars']:
                chars.append((cursor.position(),units(char['c']),char,base))
                cursor.insertText(char['c'],base)
        records.append((cursor.block(),line,chars))
    # A wide temporary layout prevents an approximate advance from wrapping the
    # line before the source advances have been installed.
    doc.setTextWidth(20000)
    for block,line,chars in records:
        for index,(pos,length,char,base) in enumerate(chars):
            if not length:continue
            advance=(chars[index+1][2]['origin'][0]-char['origin'][0]) if index+1<len(chars) else char['bbox'][2]-char['origin'][0]
            metrics=QFontMetricsF(base.font(),editor.device)
            spacing=advance-metrics.horizontalAdvance(char['c'])
            fmt=QTextCharFormat(base);fmt.setFontLetterSpacingType(QFont.AbsoluteSpacing);fmt.setFontLetterSpacing(spacing);fmt.setProperty(SPACING,spacing)
            cursor.setPosition(pos);cursor.setPosition(pos+length,QTextCursor.KeepAnchor);cursor.setCharFormat(fmt)
        # Correct fixed-point layout rounding against the original glyph origins.
        for index in range(1,len(chars)):
            pos,length,char,base=chars[index];doc.size();layout=block.layout();ql=layout.lineAt(0)
            current=ql.cursorToX(pos-block.position())[0]+layout.position().x()
            delta=char['origin'][0]-left-current
            if abs(delta)>.025:
                prev,plen,_,_=chars[index-1];cursor.setPosition(prev);cursor.setPosition(prev+plen,QTextCursor.KeepAnchor)
                fmt=cursor.charFormat();spacing=fmt.fontLetterSpacing()+delta
                fmt.setFontLetterSpacing(spacing);fmt.setProperty(SPACING,spacing);cursor.setCharFormat(fmt)
    # PDF bboxes end at the last glyph, whereas Qt wrapping also counts its
    # trailing tracking. Leave room for that inherited spacing so replacing
    # the last letter with an equal-width letter does not wrap the whole word.
    trailing=0.
    for block,line,chars in records:
        if len(chars)>1:
            pos,length,_,_=chars[-2];cursor.setPosition(pos);cursor.setPosition(pos+length,QTextCursor.KeepAnchor)
            trailing=max(trailing,cursor.charFormat().fontLetterSpacing())
    # Qt rounds glyph advances and inherited tracking in fixed-point units.
    # A same-width replacement at the last position can differ by a fraction
    # of a point after font-cache changes. Reserve room without moving glyphs.
    editor._width=min(editor._width+trailing+.25,editor.target.get('pageWidth',20000)-left)
    editor.widthChanged.emit()
    doc.size()
    descents=[block.layout().lineAt(0).descent() for block,line,chars in records]
    for index,(block,line,chars) in enumerate(records):
        if index:
            step=line['origin'][1]-records[index-1][1]['origin'][1]
            height=step+descents[index]-descents[index-1]
        elif len(records)>1:
            height=records[1][1]['origin'][1]-line['origin'][1]
        else:height=0
        if height>0:
            bf=block.blockFormat();bf.setLineHeight(height,QTextBlockFormat.FixedHeight.value)
            QTextCursor(block).setBlockFormat(bf)
    doc.setTextWidth(editor._width);doc.size()
