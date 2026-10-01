package kr.naya.hwpedit.core.hwpx

import kr.dogfoot.hwpxlib.`object`.HWPXFile
import kr.dogfoot.hwpxlib.`object`.content.header_xml.enumtype.HorizontalAlign2
import kr.dogfoot.hwpxlib.`object`.content.header_xml.enumtype.LineSpacingType
import kr.dogfoot.hwpxlib.`object`.content.header_xml.enumtype.LineType2
import kr.dogfoot.hwpxlib.`object`.content.header_xml.enumtype.UnderlineType
import kr.dogfoot.hwpxlib.`object`.content.header_xml.references.CharPr
import kr.dogfoot.hwpxlib.`object`.content.header_xml.references.ParaPr
import kr.dogfoot.hwpxlib.`object`.content.section_xml.ParaListCore
import kr.dogfoot.hwpxlib.`object`.content.section_xml.SubList
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.Ctrl
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.Para
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.Run
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.RunItem
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.T
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.TItem
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.ctrl.EndNote
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.ctrl.FieldEnd
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.ctrl.FootNote
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.ctrl.Footer
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.ctrl.Header
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.`object`.Chart
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.`object`.ConnectLine
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.`object`.Container
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.`object`.Equation
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.`object`.Line
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.`object`.OLE
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.`object`.Picture
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.`object`.Table
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.`object`.TextArt
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.`object`.Video
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.`object`.drawingobject.DrawingObject
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.`object`.shapeobject.ShapeObject
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.secpr.SecPr
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.t.DeleteEnd
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.t.FWSpace
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.t.InsertEnd
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.t.MarkpenEnd
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.t.Hyphen
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.t.LineBreak
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.t.NBSpace
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.t.NormalText
import kr.dogfoot.hwpxlib.`object`.content.section_xml.paragraph.t.Tab
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
import kr.naya.hwpedit.core.edit.RebuiltPara
import kr.naya.hwpedit.core.edit.SourcePara
import kr.naya.hwpedit.core.hwp.HwpAdapter

/** hwpx(한글 개방형 XML 형식) 문서 처리. */
internal class HwpxAdapter(val file: HWPXFile) : DocumentAdapter<Para, ParaListCore>() {

    /** 구역 설정(문단 첫 run 에 붙음). */
    class SecPrAnchor(val secPr: SecPr)

    /** run 안의 개체(표, 그림, 컨트롤 등). */
    class RunItemAnchor(val item: RunItem)

    /** 글자 요소 안의 표시(형광펜 시작·끝, 변경 추적 표시 등). */
    class TItemAnchor(val item: TItem)

    private val charPrById: Map<String, CharPr> by lazy {
        file.headerXMLFile()?.refList()?.charProperties()?.items()?.associateBy { it.id() } ?: emptyMap()
    }
    private val paraPrById: Map<String, ParaPr> by lazy {
        file.headerXMLFile()?.refList()?.paraProperties()?.items()?.associateBy { it.id() } ?: emptyMap()
    }
    private val hangulFontById: Map<String, String> by lazy {
        val ff = file.headerXMLFile()?.refList()?.fontfaces()?.hangulFontface()
        ff?.fonts()?.associate { (it.id() ?: "") to (it.face() ?: "") } ?: emptyMap()
    }
    private var footnoteNo = 0
    private var endnoteNo = 0

    fun buildModel(): DocModel {
        val blocks = ArrayList<Block>()
        var bodyWidth = 0L
        for (section in file.sectionXMLFileList().items()) {
            if (bodyWidth == 0L) bodyWidth = sectionBodyWidth(section)
            blocks.addAll(walk(section))
        }
        return DocModel(
            format = DocFormat.HWPX,
            blocks = blocks,
            bodyWidth = if (bodyWidth > 0) bodyWidth else HwpAdapter.DEFAULT_BODY_WIDTH,
            readOnlyReason = null,
            warnings = warnings.toList(),
        )
    }

    private fun sectionBodyWidth(section: ParaListCore): Long {
        val first = section.paras().firstOrNull() ?: return 0
        for (run in first.runs()) {
            val pp = run.secPr()?.pagePr() ?: continue
            val w = (pp.width() ?: 0).toLong()
            val m = pp.margin()
            val body = w - (m?.left() ?: 0) - (m?.right() ?: 0) - (m?.gutter() ?: 0)
            if (body > 0) return body
        }
        return 0
    }

    // ---- 문단 목록 ----

    override fun paragraphs(container: ParaListCore): List<Para> = container.paras().toList()

    override fun replace(container: ParaListCore, start: Int, count: Int, newParas: List<Para>) {
        repeat(count) { container.removePara(start) }
        for ((k, p) in newParas.withIndex()) container.insertPara(p, start + k)
    }

    // ---- 읽기 ----

    override fun read(p: Para): SourcePara {
        val sb = StringBuilder()
        val fmts = ArrayList<String>()
        val payloads = ArrayList<Any?>()
        val anchors = ArrayList<Anchor>()
        var lastFmt: String? = null

        fun char(c: Char, fmt: String, payload: Any? = null) {
            sb.append(c); fmts.add(fmt); payloads.add(payload)
        }
        fun text(s: String?, fmt: String) {
            if (s == null) return
            for (c in s) when (c) {
                '\r' -> {}
                '\n' -> char(SpecialChars.LINE_BREAK, fmt)
                else -> char(c, fmt)
            }
        }

        for (run in p.runs()) {
            val runFmt = run.charPrIDRef() ?: "0"
            lastFmt = runFmt
            run.secPr()?.let { anchors.add(Anchor(sb.length, runFmt, SecPrAnchor(it))) }
            for (item in run.runItems()) {
                if (item is T) {
                    val f = item.charPrIDRef() ?: runFmt
                    if (item.isOnlyText) {
                        text(item.onlyText(), f)
                    } else if (item.countOfItems() > 0) {
                        for (ti in item.items()) when (ti) {
                            is NormalText -> text(ti.text(), f)
                            is Tab -> char(SpecialChars.TAB, f, ti)
                            is LineBreak -> char(SpecialChars.LINE_BREAK, f)
                            is NBSpace -> char(SpecialChars.NB_SPACE, f)
                            is FWSpace -> char(SpecialChars.FW_SPACE, f)
                            is Hyphen -> char(SpecialChars.HYPHEN, f)
                            else -> anchors.add(Anchor(sb.length, f, TItemAnchor(ti), rightBias = isRangeEnd(ti)))
                        }
                    }
                } else {
                    val end = item is Ctrl && item.countOfCtrlItems() > 0 && item.ctrlItems().all { it is FieldEnd }
                    anchors.add(Anchor(sb.length, runFmt, RunItemAnchor(item), rightBias = end))
                }
            }
        }
        return SourcePara(
            text = sb.toString(),
            fmts = fmts.toTypedArray(),
            payloads = payloads.toTypedArray(),
            anchors = anchors,
            marks = emptyList(),
            endFmt = lastFmt ?: "0",
            ref = p,
        )
    }

    private fun isRangeEnd(ti: TItem) = ti is MarkpenEnd || ti is InsertEnd || ti is DeleteEnd

    // ---- 쓰기 ----

    override fun write(r: RebuiltPara): Para {
        val para = if (r.reuse) r.template.ref as Para else newParaLike(r.template.ref as Para)
        para.removeAllRuns()
        // 줄 배치 정보는 고친 글과 맞지 않으므로 지운다. 한글에서 열 때 다시 계산한다.
        para.removeLineSegArray()

        var run: Run? = null
        var t: T? = null
        val pending = StringBuilder()

        fun ensureT(): T {
            val cur = t
            if (cur != null) return cur
            return run!!.addNewT().also { t = it }
        }
        fun flushText() {
            if (pending.isEmpty()) return
            ensureT().addText(pending.toString())
            pending.setLength(0)
        }
        fun newRun(fmt: String): Run {
            flushText()
            return para.addNewRun().also {
                it.charPrIDRef(fmt)
                run = it
                t = null
            }
        }
        fun ensureRun(fmt: String): Run {
            val cur = run
            if (cur != null && cur.charPrIDRef() == fmt) return cur
            return newRun(fmt)
        }

        var ai = 0
        fun emitAnchors(offset: Int) {
            while (ai < r.anchors.size && r.anchors[ai].offset <= offset) {
                val a = r.anchors[ai++]
                when (val payload = a.payload) {
                    is SecPrAnchor -> {
                        // 구역 설정은 run 의 맨 앞에만 놓일 수 있다.
                        val cur = run
                        val target = if (cur != null && cur.secPr() == null && cur.countOfRunItem() == 0 &&
                            pending.isEmpty() && cur.charPrIDRef() == a.fmt
                        ) cur else newRun(a.fmt)
                        target.createSecPr()
                        target.secPr().copyFrom(payload.secPr)
                    }
                    is RunItemAnchor -> {
                        val cur = ensureRun(a.fmt)
                        flushText()
                        cur.addRunItem(payload.item)
                        t = null
                    }
                    is TItemAnchor -> {
                        ensureRun(a.fmt)
                        flushText()
                        ensureT().addItem(payload.item)
                    }
                }
            }
        }

        for (i in 0..r.text.length) {
            emitAnchors(i)
            if (i == r.text.length) break
            val c = r.text[i]
            ensureRun(r.fmts[i])
            when (c) {
                SpecialChars.TAB -> {
                    flushText()
                    ensureT().addItem((r.payloads[i] as? Tab) ?: Tab())
                }
                SpecialChars.LINE_BREAK -> {
                    flushText(); ensureT().addNewLineBreak()
                }
                SpecialChars.NB_SPACE -> {
                    flushText(); ensureT().addNewNBSpace()
                }
                SpecialChars.FW_SPACE -> {
                    flushText(); ensureT().addNewFWSpace()
                }
                SpecialChars.HYPHEN -> {
                    flushText(); ensureT().addNewHyphen()
                }
                else -> pending.append(if (c < ' ') ' ' else c)
            }
        }
        emitAnchors(Int.MAX_VALUE)
        flushText()
        if (para.countOfRun() == 0) para.addNewRun().charPrIDRef(r.endFmt)
        return para
    }

    private fun newParaLike(t: Para): Para = Para().apply {
        id("0")
        paraPrIDRef(t.paraPrIDRef())
        styleIDRef(t.styleIDRef())
        pageBreak(false)
        columnBreak(false)
        merged(false)
    }

    // ---- 모양 ----

    override fun paraStyle(p: Para): ParaStyle {
        val pp = paraPrById[p.paraPrIDRef()] ?: return ParaStyle.DEFAULT
        val align = when (pp.align()?.horizontal()) {
            HorizontalAlign2.LEFT -> Align.LEFT
            HorizontalAlign2.RIGHT -> Align.RIGHT
            HorizontalAlign2.CENTER -> Align.CENTER
            HorizontalAlign2.DISTRIBUTE, HorizontalAlign2.DISTRIBUTE_SPACE -> Align.DISTRIBUTE
            else -> Align.JUSTIFY
        }
        val m = pp.margin()
        fun pt(v: Int?): Float = (v ?: 0) / 200f
        val ls = pp.lineSpacing()
        return ParaStyle(
            align = align,
            marginLeftPt = pt(m?.left()?.value()),
            marginRightPt = pt(m?.right()?.value()),
            indentPt = pt(m?.intent()?.value()),
            spaceBeforePt = pt(m?.prev()?.value()),
            spaceAfterPt = pt(m?.next()?.value()),
            lineSpacingPercent = if (ls == null || ls.type() == LineSpacingType.PERCENT) ls?.value() ?: 160 else null,
        )
    }

    override fun charStyle(fmt: String): CharStyle {
        val cp = charPrById[fmt] ?: return CharStyle.DEFAULT
        return CharStyle(
            bold = cp.bold() != null,
            italic = cp.italic() != null,
            underline = cp.underline()?.type().let { it != null && it != UnderlineType.NONE },
            strike = cp.strikeout()?.shape().let { it != null && it != LineType2.NONE },
            superscript = cp.supscript() != null,
            subscript = cp.subscript() != null,
            sizePt = (cp.height() ?: 1000) / 100f,
            color = parseColor(cp.textColor()),
            fontName = cp.fontRef()?.hangul()?.let { hangulFontById[it] },
        )
    }

    private fun parseColor(s: String?): Int {
        if (s == null || !s.startsWith("#") || s.length < 7) return 0xFF000000.toInt()
        return try {
            (0xFF shl 24) or s.substring(1, 7).toInt(16)
        } catch (e: NumberFormatException) {
            0xFF000000.toInt()
        }
    }

    // ---- 개체 ----

    override fun leadingBlocks(anchor: Anchor): List<Block> {
        val ctrl = (anchor.payload as? RunItemAnchor)?.item as? Ctrl ?: return emptyList()
        val out = ArrayList<Block>()
        for (ci in ctrl.ctrlItems()) when (ci) {
            is Header -> ci.subList()?.let { out.add(BoxBlock(BoxKind.HEADER, "머리말", walk(it))) }
            is Footer -> ci.subList()?.let { out.add(BoxBlock(BoxKind.FOOTER, "꼬리말", walk(it))) }
        }
        return out
    }

    override fun trailingBlocks(anchor: Anchor): List<Block>? {
        val item = (anchor.payload as? RunItemAnchor)?.item ?: return null
        if (item is Ctrl) {
            val out = ArrayList<Block>()
            for (ci in item.ctrlItems()) when (ci) {
                is FootNote -> ci.subList()?.let { out.add(BoxBlock(BoxKind.FOOTNOTE, "각주 ${++footnoteNo}", walk(it))) }
                is EndNote -> ci.subList()?.let { out.add(BoxBlock(BoxKind.ENDNOTE, "미주 ${++endnoteNo}", walk(it))) }
            }
            return out.ifEmpty { null }
        }
        return objectBlocks(item)
    }

    private fun captionOf(o: ShapeObject<*>): List<Block> {
        val sub: SubList = o.caption()?.subList() ?: return emptyList()
        return walk(sub)
    }

    private fun objectBlocks(item: RunItem): List<Block>? = when (item) {
        is Table -> listOf(tableBlock(item))
        is Picture -> listOf(
            ImageBlock(
                imageData(item.img()?.binaryItemIDRef()),
                item.sz()?.width() ?: 0L,
                item.sz()?.height() ?: 0L,
                captionOf(item),
            ),
        )
        is Equation -> listOf(ObjectBlock("수식", item.script()?.text()?.takeIf { it.isNotBlank() }))
        is Container -> {
            val inner = (0 until item.countOfChild()).flatMap { objectBlocks(item.getChild(it)) ?: emptyList() }
                .filter { it !is ObjectBlock }
            if (inner.isEmpty()) listOf(ObjectBlock("묶음 개체")) else listOf(BoxBlock(BoxKind.GROUP, "묶음 개체", inner))
        }
        is Line, is ConnectLine -> null
        is TextArt -> listOf(ObjectBlock("글맵시"))
        is DrawingObject<*> -> {
            val sub = item.drawText()?.subList()
            if (sub != null) listOf(BoxBlock(BoxKind.TEXT_BOX, "글상자", walk(sub) + captionOf(item)))
            else listOf(ObjectBlock("그리기 개체"))
        }
        is OLE -> listOf(ObjectBlock("OLE 개체"))
        is Chart -> listOf(ObjectBlock("차트"))
        is Video -> listOf(ObjectBlock("동영상"))
        is ShapeObject<*> -> listOf(ObjectBlock("양식 개체"))
        else -> null
    }

    private fun tableBlock(tbl: Table): TableBlock {
        val cells = ArrayList<CellView>()
        var rows = (tbl.rowCnt() ?: 0).toInt()
        var cols = (tbl.colCnt() ?: 0).toInt()
        val widthByCol = HashMap<Int, Long>()
        val spanning = ArrayList<Triple<Int, Int, Long>>()
        for ((ri, tr) in tbl.trs().withIndex()) {
            for ((ci, tc) in tr.tcs().withIndex()) {
                val r = tc.cellAddr()?.rowAddr()?.toInt() ?: ri
                val c = tc.cellAddr()?.colAddr()?.toInt() ?: ci
                val rs = maxOf(1, tc.cellSpan()?.rowSpan()?.toInt() ?: 1)
                val cs = maxOf(1, tc.cellSpan()?.colSpan()?.toInt() ?: 1)
                val w = tc.cellSz()?.width() ?: 0L
                rows = maxOf(rows, r + rs)
                cols = maxOf(cols, c + cs)
                if (cs == 1) widthByCol[c] = minOf(widthByCol[c] ?: Long.MAX_VALUE, w)
                else spanning.add(Triple(c, cs, w))
                val blocks = tc.subList()?.let { walk(it) } ?: emptyList()
                cells.add(CellView(r, c, rs, cs, blocks))
            }
        }
        return TableBlock(rows, cols, HwpAdapter.columnWidths(cols, widthByCol, spanning), cells, captionOf(tbl))
    }

    private fun imageData(id: String?): ByteArray? {
        if (id == null) return null
        val item = file.contentHPFFile()?.getManifestItemById(id) ?: return null
        return item.attachedFile()?.data()
    }
}
