package kr.naya.hwpedit.core.edit

/**
 * 문단 하나를 형식(hwp/hwpx)과 상관없이 나타낸 것.
 *
 * text     화면에 보이는 글자(탭·줄바꿈 등은 SpecialChars 로 바뀐 상태)
 * fmts     글자마다 원래 글자 모양 번호
 * payloads 글자마다 딸린 원래 객체(예: 탭의 원래 정보). 보통은 null
 * anchors  글자 사이에 박혀 있는 보이지 않는 개체(표, 그림, 구역 정의, 필드 표시 등)
 * marks    글자 사이 위치 표시(hwp 형광펜 범위 등)
 */
class SourcePara(
    val text: String,
    val fmts: Array<String>,
    val payloads: Array<Any?>,
    val anchors: List<Anchor>,
    val marks: List<Mark>,
    val endFmt: String,
    val ref: Any,
) {
    init {
        require(fmts.size == text.length && payloads.size == text.length)
    }
}

/**
 * offset 번째 글자 앞에 놓인 개체.
 * rightBias: 필드 끝처럼 '범위의 끝'을 나타내면 true. 바로 그 자리에 넣은 글이 범위 안으로 들어간다.
 */
class Anchor(val offset: Int, val fmt: String, val payload: Any, val rightBias: Boolean = false)

class Mark(val offset: Int, val payload: Any, val rightBias: Boolean = false)

class RebuiltPara(
    /** 문단 모양을 물려받을 원래 문단. */
    val template: SourcePara,
    /** true 면 원래 문단 객체를 고쳐서 쓰고, false 면 새 문단을 만든다. */
    val reuse: Boolean,
    /** true 면 원래 문단과 완전히 같으므로 손대지 않는다. */
    val unchanged: Boolean,
    val text: String,
    val fmts: Array<String>,
    val payloads: Array<Any?>,
    val anchors: List<Anchor>,
    val marks: List<Mark>,
    val endFmt: String,
)

/**
 * 고치기 전 문단들과 고친 뒤 글자열을 비교해, 새 문단 목록을 만든다.
 *
 * 원칙
 *  - 글이 그대로인 문단은 손대지 않는다.
 *  - 남은 글자는 원래 글자 모양을 지킨다. 새로 넣은 글자는 바로 앞 글자의 모양을 따른다.
 *  - 보이지 않는 개체(표, 그림, 구역 정의 등)는 절대 지우지 않는다. 주변 글이 지워지면 가까운 자리로 옮긴다.
 */
object FlowRebuilder {

    fun rebuild(old: List<SourcePara>, newText: String): List<RebuiltPara> {
        require(old.isNotEmpty())
        val newLines = newText.split('\n')
        val oldTexts = old.map { it.text }
        if (oldTexts == newLines) return old.map { unchangedOf(it) }

        // 1) 문단 단위로 먼저 짝을 찾는다.
        val lm = TextDiff.matches(oldTexts, newLines)
        val segments = ArrayList<Seg>()
        var po = 0
        var pn = 0
        var i = 0
        while (i <= lm.size) {
            val o = if (i < lm.size) lm[i] else old.size
            val n = if (i < lm.size) lm[i + 1] else newLines.size
            if (o > po || n > pn) segments.add(Seg(po, o, pn, n, matched = false))
            if (i < lm.size) segments.add(Seg(o, o + 1, n, n + 1, matched = true))
            po = o + 1
            pn = n + 1
            i += 2
        }

        // 2) 한쪽이 빈 구간(문단을 통째로 넣거나 지운 곳)은 이웃한 같은 문단과 묶어서 처리한다.
        val absorbed = BooleanArray(segments.size)
        for ((g, s) in segments.withIndex()) {
            if (s.matched) continue
            val oldEmpty = s.oEnd == s.oStart
            val newEmpty = s.nEnd == s.nStart
            if (!oldEmpty && !newEmpty) continue
            if (g > 0 && segments[g - 1].matched) absorbed[g - 1] = true
            else if (g + 1 < segments.size && segments[g + 1].matched) absorbed[g + 1] = true
        }

        val out = ArrayList<RebuiltPara>(newLines.size)
        var g = 0
        while (g < segments.size) {
            val s = segments[g]
            if (s.matched && !absorbed[g]) {
                out.add(unchangedOf(old[s.oStart]))
                g++
                continue
            }
            var end = g
            while (end + 1 < segments.size && (!segments[end + 1].matched || absorbed[end + 1])) end++
            val oS = segments[g].oStart
            val oE = segments[end].oEnd
            val nS = segments[g].nStart
            val nE = segments[end].nEnd
            out.addAll(rebuildRegion(old, oS, oE, newLines, nS, nE))
            g = end + 1
        }
        return out
    }

    private class Seg(val oStart: Int, val oEnd: Int, val nStart: Int, val nEnd: Int, val matched: Boolean)

    private fun unchangedOf(p: SourcePara) = RebuiltPara(
        template = p, reuse = true, unchanged = true, text = p.text, fmts = p.fmts,
        payloads = p.payloads, anchors = p.anchors, marks = p.marks, endFmt = p.endFmt,
    )

    private fun rebuildRegion(
        old: List<SourcePara>, oS: Int, oE: Int,
        newLines: List<String>, nS: Int, nE: Int,
    ): List<RebuiltPara> {
        // 원래 글(문단을 \n 으로 이음)
        val oldSb = StringBuilder()
        val paraStart = IntArray(oE - oS)
        for (k in oS until oE) {
            if (k > oS) oldSb.append('\n')
            paraStart[k - oS] = oldSb.length
            oldSb.append(old[k].text)
        }
        val oldText = oldSb.toString()
        // 원래 글자 위치 -> (문단 번호, 문단 안 위치). \n 은 앞 문단 끝으로 기록.
        val oldPara = IntArray(oldText.length)
        val oldOff = IntArray(oldText.length)
        for (k in oS until oE) {
            val st = paraStart[k - oS]
            val len = old[k].text.length
            for (t in 0 until len) {
                oldPara[st + t] = k; oldOff[st + t] = t
            }
            if (st + len < oldText.length) {
                oldPara[st + len] = k; oldOff[st + len] = -1
            }
        }

        val lines = newLines.subList(nS, nE)
        val newText = lines.joinToString("\n")
        val lineStart = IntArray(lines.size)
        run {
            var p = 0
            for ((k, l) in lines.withIndex()) {
                lineStart[k] = p
                p += l.length + 1
            }
        }
        val pm = PositionMap(oldText.length, newText.length, TextDiff.matches(oldText, newText))

        fun isOldNewline(idx: Int) = oldOff[idx] < 0
        fun fmtOfOld(idx: Int): String {
            val p = old[oldPara[idx]]
            return if (oldOff[idx] < 0) p.endFmt else p.fmts[oldOff[idx]]
        }
        /** 새 글 j 위치 앞쪽에서 가장 가까운 남은 글자의 글자 모양. */
        fun fmtBefore(j: Int): String? {
            var t = j - 1
            while (t >= 0) {
                val o = pm.newToOld[t]
                if (o >= 0) return fmtOfOld(o)
                t--
            }
            return null
        }
        fun fmtAfter(j: Int): String? {
            var t = j
            while (t < newText.length) {
                val o = pm.newToOld[t]
                if (o >= 0) return fmtOfOld(o)
                t++
            }
            return null
        }

        // 각 새 문단이 어느 원래 문단의 모양을 물려받을지 정한다.
        val templates = IntArray(lines.size)
        for (k in lines.indices) {
            val s = lineStart[k]
            val e = s + lines[k].length
            var tpl = -1
            for (j in s until e) {
                val o = pm.newToOld[j]
                if (o >= 0) {
                    tpl = oldPara[o]; break
                }
            }
            if (tpl < 0 && k > 0) {
                val o = pm.newToOld[s - 1]
                if (o >= 0 && isOldNewline(o)) tpl = oldPara[o] + 1
            }
            if (tpl < 0 && k < lines.size - 1) {
                val o = pm.newToOld[e]
                if (o >= 0 && isOldNewline(o)) tpl = oldPara[o]
            }
            if (tpl < 0) {
                var t = s - 1
                while (t >= 0 && tpl < 0) {
                    val o = pm.newToOld[t]
                    if (o >= 0) tpl = if (isOldNewline(o)) oldPara[o] + 1 else oldPara[o]
                    t--
                }
            }
            if (tpl < 0) {
                var t = e
                while (t < newText.length && tpl < 0) {
                    val o = pm.newToOld[t]
                    if (o >= 0) tpl = oldPara[o]
                    t++
                }
            }
            if (tpl < 0) tpl = oS
            templates[k] = tpl.coerceIn(oS, oE - 1)
        }

        // 보이지 않는 개체와 위치 표시를 새 자리로 옮긴다.
        val lineAnchors = Array(lines.size) { ArrayList<Anchor>() }
        val lineMarks = Array(lines.size) { ArrayList<Mark>() }
        fun lineOf(pos: Int): Int {
            var lo = 0
            var hi = lines.size - 1
            while (lo < hi) {
                val mid = (lo + hi + 1) / 2
                if (lineStart[mid] <= pos) lo = mid else hi = mid - 1
            }
            return lo
        }
        // 개체는 원래 순서를 절대 바꾸지 않는다. 오른쪽에 붙는 개체(필드 끝 등)가 뒤 개체를 앞지르면
        // 필드가 서로 엇갈릴 수 있으므로, 뒤 개체 위치를 넘지 않게 줄인다.
        val movedAnchors = ArrayList<Anchor>()
        val movedPos = ArrayList<Int>()
        for (k in oS until oE) {
            val p = old[k]
            val st = paraStart[k - oS]
            for (a in p.anchors) {
                movedAnchors.add(a)
                movedPos.add(pm.map(st + a.offset, a.rightBias))
            }
            for (m in p.marks) {
                val np = pm.map(st + m.offset, m.rightBias)
                val ln = lineOf(np)
                lineMarks[ln].add(Mark(np - lineStart[ln], m.payload, m.rightBias))
            }
        }
        for (i in movedPos.size - 2 downTo 0) {
            if (movedPos[i] > movedPos[i + 1]) movedPos[i] = movedPos[i + 1]
        }
        for ((i, a) in movedAnchors.withIndex()) {
            val np = movedPos[i]
            val ln = lineOf(np)
            lineAnchors[ln].add(Anchor(np - lineStart[ln], a.fmt, a.payload, a.rightBias))
        }
        for (list in lineMarks) list.sortBy { it.offset }

        val used = BooleanArray(old.size)
        val out = ArrayList<RebuiltPara>(lines.size)
        for (k in lines.indices) {
            val s = lineStart[k]
            val text = lines[k]
            val tpl = old[templates[k]]
            val reuse = !used[templates[k]]
            used[templates[k]] = true

            val fmts = arrayOfNulls<String>(text.length)
            val payloads = arrayOfNulls<Any>(text.length)
            for (t in text.indices) {
                val o = pm.newToOld[s + t]
                if (o >= 0) {
                    fmts[t] = fmtOfOld(o)
                    val op = old[oldPara[o]]
                    payloads[t] = if (oldOff[o] >= 0) op.payloads[oldOff[o]] else null
                }
            }
            val fallback = fmtBefore(s) ?: fmtAfter(s) ?: tpl.endFmt
            for (t in text.indices) {
                if (fmts[t] == null) {
                    fmts[t] = if (t > 0) fmts[t - 1] else {
                        var f: String? = null
                        for (u in text.indices) if (pm.newToOld[s + u] >= 0) {
                            f = fmts[u]; break
                        }
                        f ?: fallback
                    }
                }
            }
            @Suppress("UNCHECKED_CAST")
            val fmtArr = fmts as Array<String>
            val endFmt = if (text.isEmpty()) {
                if (reuse && tpl.text.isEmpty()) tpl.endFmt else fallback
            } else fmtArr[text.length - 1]

            val anchors = lineAnchors[k]
            val marks = lineMarks[k]
            val unchanged = reuse && text == tpl.text && fmtArr.contentEquals(tpl.fmts) &&
                sameRefs(payloads, tpl.payloads) && sameAnchors(anchors, tpl.anchors) &&
                sameMarks(marks, tpl.marks)
            out.add(
                RebuiltPara(
                    template = tpl, reuse = reuse, unchanged = unchanged, text = text,
                    fmts = fmtArr, payloads = payloads, anchors = anchors, marks = marks,
                    endFmt = if (unchanged) tpl.endFmt else endFmt,
                ),
            )
        }
        return out
    }

    private fun sameRefs(a: Array<Any?>, b: Array<Any?>): Boolean {
        if (a.size != b.size) return false
        for (i in a.indices) if (a[i] !== b[i]) return false
        return true
    }

    private fun sameAnchors(a: List<Anchor>, b: List<Anchor>): Boolean {
        if (a.size != b.size) return false
        for (i in a.indices) {
            if (a[i].offset != b[i].offset || a[i].payload !== b[i].payload || a[i].fmt != b[i].fmt) return false
        }
        return true
    }

    private fun sameMarks(a: List<Mark>, b: List<Mark>): Boolean {
        if (a.size != b.size) return false
        for (i in a.indices) if (a[i].offset != b[i].offset || a[i].payload !== b[i].payload) return false
        return true
    }
}
