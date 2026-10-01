package kr.naya.hwpedit.core.hwp

import kr.dogfoot.hwplib.`object`.HWPFile
import kr.dogfoot.hwplib.`object`.bodytext.ParagraphListInterface
import kr.dogfoot.hwplib.`object`.bodytext.control.Control
import kr.dogfoot.hwplib.`object`.bodytext.control.ControlEndnote
import kr.dogfoot.hwplib.`object`.bodytext.control.ControlEquation
import kr.dogfoot.hwplib.`object`.bodytext.control.ControlFooter
import kr.dogfoot.hwplib.`object`.bodytext.control.ControlFootnote
import kr.dogfoot.hwplib.`object`.bodytext.control.ControlForm
import kr.dogfoot.hwplib.`object`.bodytext.control.ControlHeader
import kr.dogfoot.hwplib.`object`.bodytext.control.ControlSectionDefine
import kr.dogfoot.hwplib.`object`.bodytext.control.ControlTable
import kr.dogfoot.hwplib.`object`.bodytext.control.gso.ControlArc
import kr.dogfoot.hwplib.`object`.bodytext.control.gso.ControlContainer
import kr.dogfoot.hwplib.`object`.bodytext.control.gso.ControlCurve
import kr.dogfoot.hwplib.`object`.bodytext.control.gso.ControlEllipse
import kr.dogfoot.hwplib.`object`.bodytext.control.gso.ControlPicture
import kr.dogfoot.hwplib.`object`.bodytext.control.gso.ControlPolygon
import kr.dogfoot.hwplib.`object`.bodytext.control.gso.ControlRectangle
import kr.dogfoot.hwplib.`object`.bodytext.control.gso.GsoControl
import kr.dogfoot.hwplib.`object`.bodytext.control.gso.GsoControlType
import kr.dogfoot.hwplib.`object`.bodytext.control.gso.textbox.TextBox
import kr.dogfoot.hwplib.`object`.bodytext.paragraph.Paragraph
import kr.dogfoot.hwplib.`object`.bodytext.paragraph.rangetag.RangeTagItem
import kr.dogfoot.hwplib.`object`.bodytext.paragraph.text.HWPChar
import kr.dogfoot.hwplib.`object`.bodytext.paragraph.text.HWPCharControlChar
import kr.dogfoot.hwplib.`object`.bodytext.paragraph.text.HWPCharControlInline
import kr.dogfoot.hwplib.`object`.bodytext.paragraph.text.HWPCharNormal
import kr.dogfoot.hwplib.`object`.bodytext.paragraph.text.HWPCharType
import kr.dogfoot.hwplib.`object`.docinfo.parashape.Alignment
import kr.dogfoot.hwplib.`object`.docinfo.parashape.LineSpaceSort
import kr.naya.hwpedit.core.Align
import kr.naya.hwpedit.core.Block
import kr.naya.hwpedit.core.BoxBlock
import kr.naya.hwpedit.core.BoxKind
import kr.naya.hwpedit.core.CellView
import kr.naya.hwpedit.core.CharStyle
import kr.naya.hwpedit.core.DocFormat
import kr.naya.hwpedit.core.DocModel
import kr.naya.hwpedit.core.DocumentAdapter
import kr.naya.hwpedit.core.ImageBlock
import kr.naya.hwpedit.core.ObjectBlock
import kr.naya.hwpedit.core.ParaStyle
import kr.naya.hwpedit.core.SpecialChars
import kr.naya.hwpedit.core.TableBlock
import kr.naya.hwpedit.core.edit.Anchor
import kr.naya.hwpedit.core.edit.Mark
import kr.naya.hwpedit.core.edit.RebuiltPara
import kr.naya.hwpedit.core.edit.SourcePara

/** hwp(한글 5.0 형식) 문서 처리. */
internal class HwpAdapter(val file: HWPFile) : DocumentAdapter<Paragraph, ParagraphListInterface>() {

    /** 글자 사이에 박힌 개체: 원래 문자 객체와, 확장 컨트롤이면 그에 딸린 컨트롤. */
    class CharAnchor(val ch: HWPChar, val control: Control?)

    /** 형광펜 등 범위 표시의 시작/끝. */
    class RangeMark(val item: RangeTagItem, val isStart: Boolean)

    private val docInfo = file.docInfo
    private var sampleTab: HWPCharControlInline? = null
    private var footnoteNo = 0
    private var endnoteNo = 0

    fun buildModel(): DocModel {
        val blocks = ArrayList<Block>()
        var bodyWidth = 0L
        for (section in file.bodyText.sectionList) {
            if (bodyWidth == 0L) bodyWidth = sectionBodyWidth(section)
            blocks.addAll(walk(section))
        }
        val header = file.fileHeader
        val readOnly = when {
            header.isDistribution -> "배포용 문서라서 고쳐서 저장할 수 없어요."
            else -> null
        }
        return DocModel(
            format = DocFormat.HWP,
            blocks = blocks,
            bodyWidth = if (bodyWidth > 0) bodyWidth else DEFAULT_BODY_WIDTH,
            readOnlyReason = readOnly,
            warnings = warnings.toList(),
        )
    }

    private fun sectionBodyWidth(section: ParagraphListInterface): Long {
        for (p in section) {
            for (c in p.controlList ?: continue) {
                if (c is ControlSectionDefine) {
                    val pd = c.pageDef ?: continue
                    val landscape = try {
                        pd.property.paperDirection.toString().contains("Landscape", ignoreCase = true)
                    } catch (e: RuntimeException) {
                        false
                    }
                    val w = if (landscape) pd.paperHeight else pd.paperWidth
                    val body = w - pd.leftMargin - pd.rightMargin - pd.gutterMargin
                    if (body > 0) return body
                }
            }
            break
        }
        return 0
    }

    // ---- 문단 목록 ----

    override fun paragraphs(container: ParagraphListInterface): List<Paragraph> =
        (0 until container.paragraphCount).map { container.getParagraph(it) }

    override fun replace(container: ParagraphListInterface, start: Int, count: Int, newParas: List<Paragraph>) {
        repeat(count) { container.deleteParagraph(start) }
        for ((k, p) in newParas.withIndex()) container.insertParagraph(start + k, p)
    }

    // ---- 읽기 ----

    override fun read(p: Paragraph): SourcePara {
        val chars = p.text?.charList ?: emptyList<HWPChar>()
        val shapes = p.charShape?.positonShapeIdPairList ?: emptyList()
        fun fmtAt(pos: Long): String {
            var id = shapes.firstOrNull()?.shapeId ?: 0L
            for (s in shapes) {
                if (s.position <= pos) id = s.shapeId else break
            }
            return id.toString()
        }
        val controls = p.controlList ?: emptyList<Control>()
        var extIndex = 0

        val sb = StringBuilder()
        val fmts = ArrayList<String>()
        val payloads = ArrayList<Any?>()
        val anchors = ArrayList<Anchor>()
        // 글자 위치(WCHAR 단위) -> 글자열 위치. 범위 표시 변환용.
        val posList = ArrayList<Long>()
        val offList = ArrayList<Int>()
        var pos = 0L
        var endFmt: String? = null

        fun text(c: Char, payload: Any? = null) {
            sb.append(c); fmts.add(fmtAt(pos)); payloads.add(payload)
        }

        for (ch in chars) {
            posList.add(pos); offList.add(sb.length)
            when (ch.type) {
                HWPCharType.Normal -> text(ch.code.toChar())
                HWPCharType.ControlChar -> when (ch.code) {
                    0x0d -> endFmt = fmtAt(pos)
                    0x0a -> text(SpecialChars.LINE_BREAK)
                    0x1e -> text(SpecialChars.NB_SPACE)
                    0x1f -> text(SpecialChars.FW_SPACE)
                    0x18 -> text(SpecialChars.HYPHEN)
                    else -> anchors.add(Anchor(sb.length, fmtAt(pos), CharAnchor(ch, null)))
                }
                HWPCharType.ControlInline -> {
                    if (ch.code == 0x09) {
                        if (sampleTab == null) sampleTab = ch as HWPCharControlInline
                        text(SpecialChars.TAB, ch)
                    } else {
                        // 0x04 = 필드 끝: 끝에 덧붙인 글이 필드 안에 들어가도록 오른쪽에 붙인다.
                        anchors.add(Anchor(sb.length, fmtAt(pos), CharAnchor(ch, null), rightBias = ch.code == 0x04))
                    }
                }
                HWPCharType.ControlExtend -> {
                    val control = controls.getOrNull(extIndex++)
                    anchors.add(Anchor(sb.length, fmtAt(pos), CharAnchor(ch, control)))
                }
                null -> {}
            }
            if (endFmt != null) break
            pos += ch.charSize
        }
        if (endFmt == null) endFmt = fmtAt(pos)

        val marks = ArrayList<Mark>()
        val rangeItems = p.rangeTag?.rangeTagItemList ?: emptyList<RangeTagItem>()
        fun offsetOf(wpos: Long): Int {
            var off = 0
            for (i in posList.indices) {
                if (posList[i] <= wpos) off = offList[i] else break
            }
            if (posList.isNotEmpty() && wpos > posList.last()) off = sb.length
            return off.coerceIn(0, sb.length)
        }
        for (item in rangeItems) {
            marks.add(Mark(offsetOf(item.rangeStart), RangeMark(item, true)))
            marks.add(Mark(offsetOf(item.rangeEnd), RangeMark(item, false), rightBias = true))
        }
        marks.sortBy { it.offset }

        return SourcePara(
            text = sb.toString(),
            fmts = fmts.toTypedArray(),
            payloads = payloads.toTypedArray(),
            anchors = anchors,
            marks = marks,
            endFmt = endFmt!!,
            ref = p,
        )
    }

    // ---- 쓰기 ----

    override fun write(r: RebuiltPara): Paragraph {
        val p = if (r.reuse) r.template.ref as Paragraph else newParagraphLike(r.template.ref as Paragraph)

        val chars = ArrayList<HWPChar>()
        val charFmts = ArrayList<String>()
        val controls = ArrayList<Control>()
        // 글자열 위치 -> WCHAR 위치(범위 표시용)
        val wposOfOffset = LongArray(r.text.length + 1)
        var wpos = 0L
        var ai = 0

        fun emit(ch: HWPChar, fmt: String) {
            chars.add(ch); charFmts.add(fmt); wpos += ch.charSize
        }
        fun emitAnchors(offset: Int) {
            while (ai < r.anchors.size && r.anchors[ai].offset <= offset) {
                val a = r.anchors[ai++]
                val ca = a.payload as CharAnchor
                emit(ca.ch, a.fmt)
                if (ca.control != null) controls.add(ca.control)
            }
        }

        for (t in 0..r.text.length) {
            emitAnchors(t)
            wposOfOffset[t] = wpos
            if (t == r.text.length) break
            val c = r.text[t]
            val fmt = r.fmts[t]
            val ch: HWPChar = when (c) {
                SpecialChars.TAB -> (r.payloads[t] as? HWPCharControlInline) ?: newTab()
                SpecialChars.LINE_BREAK -> HWPCharControlChar(0x0a)
                SpecialChars.NB_SPACE -> HWPCharControlChar(0x1e)
                SpecialChars.FW_SPACE -> HWPCharControlChar(0x1f)
                SpecialChars.HYPHEN -> HWPCharControlChar(0x18)
                else -> HWPCharNormal(if (c < ' ') ' '.code else c.code)
            }
            emit(ch, fmt)
        }
        emitAnchors(Int.MAX_VALUE)
        val endFmt = if (r.text.isEmpty() && chars.isEmpty()) r.endFmt else charFmts.lastOrNull() ?: r.endFmt
        emit(HWPCharControlChar(0x0d), endFmt)

        if (p.text == null) p.createText()
        p.text.charList.clear()
        p.text.charList.addAll(chars)

        if (p.charShape == null) p.createCharShape()
        val pairs = p.charShape.positonShapeIdPairList
        pairs.clear()
        var position = 0L
        var lastFmt: String? = null
        for ((i, ch) in chars.withIndex()) {
            val f = charFmts[i]
            if (f != lastFmt) {
                p.charShape.addParaCharShape(position, f.toLong())
                lastFmt = f
            }
            position += ch.charSize
        }

        if (p.controlList == null) {
            if (controls.isNotEmpty()) p.createControlList()
        } else {
            p.controlList.clear()
        }
        p.controlList?.addAll(controls)

        // 줄 배치 정보는 고친 글과 맞지 않으므로 지운다. 한글에서 열 때 다시 계산한다.
        p.deleteLineSeg()
        rewriteRangeTags(p, r, wposOfOffset)
        return p
    }

    private fun rewriteRangeTags(p: Paragraph, r: RebuiltPara, wposOfOffset: LongArray) {
        val starts = LinkedHashMap<RangeTagItem, Int>()
        val ends = HashMap<RangeTagItem, Int>()
        for (m in r.marks) {
            val rm = m.payload as RangeMark
            if (rm.isStart) starts[rm.item] = m.offset else ends[rm.item] = m.offset
        }
        if (starts.isEmpty()) {
            p.deleteRangeTag()
            return
        }
        if (p.rangeTag == null) p.createRangeTag()
        val list = p.rangeTag.rangeTagItemList
        list.clear()
        for ((item, s) in starts) {
            val e = (ends[item] ?: r.text.length).coerceAtLeast(s)
            item.rangeStart = wposOfOffset[s]
            item.rangeEnd = wposOfOffset[e]
            if (item.rangeEnd > item.rangeStart) list.add(item)
        }
        if (list.isEmpty()) p.deleteRangeTag()
    }

    private fun newParagraphLike(t: Paragraph): Paragraph {
        val p = Paragraph()
        p.header.copy(t.header)
        p.header.divideSort.value = 0
        p.header.instanceID = 0
        p.header.isMergedByTrack = 0
        p.createText()
        p.createCharShape()
        return p
    }

    private fun newTab(): HWPCharControlInline {
        val tab = sampleTab?.clone() as? HWPCharControlInline
        if (tab != null) return tab
        return HWPCharControlInline().apply {
            code = 0x09
            addition = ByteArray(12)
        }
    }

    // ---- 모양 ----

    override fun paraStyle(p: Paragraph): ParaStyle {
        val ps = docInfo.paraShapeList.getOrNull(p.header.paraShapeId) ?: return ParaStyle.DEFAULT
        val align = when (ps.property1.alignment) {
            Alignment.Left -> Align.LEFT
            Alignment.Right -> Align.RIGHT
            Alignment.Center -> Align.CENTER
            Alignment.Distribute, Alignment.Divide -> Align.DISTRIBUTE
            else -> Align.JUSTIFY
        }
        val lineSpacing = when (ps.property1.lineSpaceSort) {
            LineSpaceSort.RatioForLetter -> ps.lineSpace2.toInt().takeIf { it > 0 } ?: ps.lineSpace
            else -> null
        }
        // 문단 여백 값은 HWPUNIT 의 2배로 저장되어 있다.
        return ParaStyle(
            align = align,
            marginLeftPt = ps.leftMargin / 200f,
            marginRightPt = ps.rightMargin / 200f,
            indentPt = ps.indent / 200f,
            spaceBeforePt = ps.topParaSpace / 200f,
            spaceAfterPt = ps.bottomParaSpace / 200f,
            lineSpacingPercent = lineSpacing,
        )
    }

    override fun charStyle(fmt: String): CharStyle {
        val cs = docInfo.charShapeList.getOrNull(fmt.toInt()) ?: return CharStyle.DEFAULT
        val prop = cs.property
        val color = cs.charColor
        val fontName = docInfo.hangulFaceNameList.getOrNull(cs.faceNameIds.hangul)?.name
        return CharStyle(
            bold = prop.isBold,
            italic = prop.isItalic,
            underline = prop.underLineSort?.toString()?.let { it != "None" } ?: false,
            strike = prop.isStrikeLine,
            superscript = prop.isSuperScript,
            subscript = prop.isSubScript,
            sizePt = cs.baseSize / 100f,
            color = (0xFF shl 24) or (color.r.toInt() shl 16) or (color.g.toInt() shl 8) or color.b.toInt(),
            fontName = fontName,
        )
    }

    // ---- 개체 ----

    override fun leadingBlocks(anchor: Anchor): List<Block> {
        val c = (anchor.payload as CharAnchor).control ?: return emptyList()
        return when (c) {
            is ControlHeader -> listOf(BoxBlock(BoxKind.HEADER, "머리말", walk(c.paragraphList)))
            is ControlFooter -> listOf(BoxBlock(BoxKind.FOOTER, "꼬리말", walk(c.paragraphList)))
            else -> emptyList()
        }
    }

    override fun trailingBlocks(anchor: Anchor): List<Block>? {
        val c = (anchor.payload as CharAnchor).control ?: return null
        return when (c) {
            is ControlTable -> listOf(tableBlock(c))
            is ControlEquation -> listOf(
                ObjectBlock("수식", c.eqEdit?.script?.toUTF16LEString()?.takeIf { it.isNotBlank() }),
            )
            is ControlForm -> listOf(ObjectBlock("양식 개체"))
            is GsoControl -> if (c.gsoType == GsoControlType.Line || c.gsoType == GsoControlType.ObjectLinkLine) {
                null // 선은 장식이라 따로 보여 주지 않는다.
            } else {
                gsoBlocks(c)
            }
            is ControlFootnote -> listOf(BoxBlock(BoxKind.FOOTNOTE, "각주 ${++footnoteNo}", walk(c.paragraphList)))
            is ControlEndnote -> listOf(BoxBlock(BoxKind.ENDNOTE, "미주 ${++endnoteNo}", walk(c.paragraphList)))
            else -> null
        }
    }

    private fun captionOf(c: Control): List<Block> {
        val caption = when (c) {
            is ControlTable -> c.caption
            is GsoControl -> c.caption
            is ControlEquation -> c.caption
            else -> null
        } ?: return emptyList()
        val list = caption.paragraphList ?: return emptyList()
        return walk(list)
    }

    private fun tableBlock(c: ControlTable): TableBlock {
        val cells = ArrayList<CellView>()
        var rows = c.table?.rowCount ?: 0
        var cols = c.table?.columnCount ?: 0
        val widthByCol = HashMap<Int, Long>()
        val spanning = ArrayList<Triple<Int, Int, Long>>()
        for (row in c.rowList) {
            for (cell in row.cellList) {
                val lh = cell.listHeader
                val r = lh.rowIndex
                val col = lh.colIndex
                val rs = maxOf(1, lh.rowSpan)
                val cs = maxOf(1, lh.colSpan)
                rows = maxOf(rows, r + rs)
                cols = maxOf(cols, col + cs)
                if (cs == 1) widthByCol[col] = minOf(widthByCol[col] ?: Long.MAX_VALUE, lh.width)
                else spanning.add(Triple(col, cs, lh.width))
                cells.add(CellView(r, col, rs, cs, walk(cell.paragraphList)))
            }
        }
        return TableBlock(rows, cols, columnWidths(cols, widthByCol, spanning), cells, captionOf(c))
    }

    private fun gsoBlocks(c: GsoControl): List<Block> {
        val caption = captionOf(c)
        return when (c) {
            is ControlPicture -> {
                val binId = c.shapeComponentPicture?.pictureInfo?.binItemID ?: 0
                val header = c.header
                listOf(ImageBlock(imageData(binId), header?.width ?: 0, header?.height ?: 0, caption))
            }
            is ControlContainer -> {
                val inner = c.childControlList.flatMap { gsoBlocks(it) }
                    .filter { it !is ObjectBlock }
                if (inner.isEmpty()) listOf(ObjectBlock("묶음 개체")) else listOf(BoxBlock(BoxKind.GROUP, "묶음 개체", inner))
            }
            else -> {
                val tb = textBoxOf(c)
                if (tb?.paragraphList != null) {
                    listOf(BoxBlock(BoxKind.TEXT_BOX, "글상자", walk(tb.paragraphList) + caption))
                } else {
                    listOf(ObjectBlock(gsoLabel(c.gsoType)))
                }
            }
        }
    }

    private fun textBoxOf(c: GsoControl): TextBox? = when (c) {
        is ControlRectangle -> c.textBox
        is ControlEllipse -> c.textBox
        is ControlArc -> c.textBox
        is ControlPolygon -> c.textBox
        is ControlCurve -> c.textBox
        else -> null
    }

    private fun gsoLabel(t: GsoControlType?): String = when (t) {
        GsoControlType.Line -> "선"
        GsoControlType.Rectangle -> "사각형"
        GsoControlType.Ellipse -> "타원"
        GsoControlType.Arc -> "호"
        GsoControlType.Polygon -> "다각형"
        GsoControlType.Curve -> "곡선"
        GsoControlType.OLE -> "OLE 개체(차트 등)"
        GsoControlType.TextArt -> "글맵시"
        GsoControlType.ObjectLinkLine -> "연결선"
        else -> "그리기 개체"
    }

    private fun imageData(binItemId: Int): ByteArray? {
        if (binItemId <= 0) return null
        val prefix = "BIN%04X".format(binItemId)
        val list = file.binData?.embeddedBinaryDataList ?: return null
        return list.firstOrNull { it.name.startsWith(prefix, ignoreCase = true) }?.data
    }

    companion object {
        /** A4, 좌우 여백 30mm 일 때 본문 폭(150mm). */
        const val DEFAULT_BODY_WIDTH = 42520L

        fun columnWidths(cols: Int, single: Map<Int, Long>, spanning: List<Triple<Int, Int, Long>>): List<Long> {
            val widths = LongArray(cols) { single[it] ?: 0L }
            for ((start, span, w) in spanning) {
                val end = minOf(cols, start + span)
                val known = (start until end).sumOf { widths[it] }
                val unknown = (start until end).count { widths[it] == 0L }
                if (unknown > 0 && w > known) {
                    val each = (w - known) / unknown
                    for (i in start until end) if (widths[i] == 0L) widths[i] = each
                }
            }
            val fallback = widths.filter { it > 0 }.let { if (it.isEmpty()) 1000L else it.sum() / it.size }
            return widths.map { if (it > 0) it else fallback }
        }
    }
}
