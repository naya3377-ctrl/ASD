package kr.naya.hwpedit.core.edit

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test

class FlowRebuilderTest {

    /** 글자마다 모양 번호를 문자 하나로 주는 짧은 표기: fmts="aabbb" */
    private fun para(text: String, fmts: String = "a".repeat(text.length), anchors: List<Anchor> = emptyList(), ref: Any = Any()) =
        SourcePara(
            text = text,
            fmts = fmts.map { it.toString() }.toTypedArray(),
            payloads = arrayOfNulls(text.length),
            anchors = anchors,
            marks = emptyList(),
            endFmt = fmts.lastOrNull()?.toString() ?: "a",
            ref = ref,
        )

    private fun fmtString(r: RebuiltPara) = r.fmts.joinToString("")

    @Test
    fun unchangedParagraphsAreKept() {
        val old = listOf(para("하나"), para("둘"), para("셋"))
        val out = FlowRebuilder.rebuild(old, "하나\n둘 고침\n셋")
        assertEquals(3, out.size)
        assertTrue(out[0].unchanged)
        assertFalse(out[1].unchanged)
        assertTrue(out[2].unchanged)
        assertSame(old[1], out[1].template)
        assertTrue(out[1].reuse)
    }

    @Test
    fun insertedTextFollowsPreviousCharacterFormat() {
        val old = listOf(para("가나다라", "aabb"))
        val out = FlowRebuilder.rebuild(old, "가나X다라Y")
        assertEquals("aaabbb", fmtString(out[0]))
    }

    @Test
    fun textTypedAtParagraphStartTakesFirstCharacterFormat() {
        val old = listOf(para("가나", "bb"))
        val out = FlowRebuilder.rebuild(old, "X가나")
        assertEquals("bbb", fmtString(out[0]))
    }

    @Test
    fun splitParagraphClonesTemplate() {
        val p = para("앞부분뒷부분", "aaabbb")
        val out = FlowRebuilder.rebuild(listOf(p), "앞부분\n뒷부분")
        assertEquals(2, out.size)
        assertTrue(out[0].reuse)
        assertFalse(out[1].reuse)
        assertSame(p, out[1].template)
        assertEquals("aaa", fmtString(out[0]))
        assertEquals("bbb", fmtString(out[1]))
    }

    @Test
    fun newParagraphAfterEnterContinuesFormat() {
        val old = listOf(para("제목", "tt"), para("본문", "bb"))
        val out = FlowRebuilder.rebuild(old, "제목\n본문\n새 줄")
        assertEquals(3, out.size)
        assertTrue(out[0].unchanged)
        assertEquals("bbb", fmtString(out[2]))
        assertSame(old[1], out[2].template)
    }

    @Test
    fun mergedParagraphKeepsBothFormatsAndAnchors() {
        val secd = Any()
        val tbl = Any()
        val old = listOf(
            para("첫째", "aa", listOf(Anchor(0, "a", secd))),
            para("둘째", "bb", listOf(Anchor(2, "b", tbl))),
        )
        val out = FlowRebuilder.rebuild(old, "첫째둘째")
        assertEquals(1, out.size)
        assertEquals("aabb", fmtString(out[0]))
        assertEquals(listOf(0, 4), out[0].anchors.map { it.offset })
        assertSame(secd, out[0].anchors[0].payload)
        assertSame(tbl, out[0].anchors[1].payload)
    }

    @Test
    fun anchorsSurviveDeletingEverything() {
        val a = Any()
        val b = Any()
        val old = listOf(para("가나다", anchors = listOf(Anchor(1, "a", a))), para("라마", anchors = listOf(Anchor(2, "a", b))))
        val out = FlowRebuilder.rebuild(old, "")
        assertEquals(1, out.size)
        assertEquals(listOf(a, b), out[0].anchors.map { it.payload })
    }

    @Test
    fun deletingAWholeParagraphMovesItsAnchors() {
        val obj = Any()
        val old = listOf(para("하나"), para("지울 문단", anchors = listOf(Anchor(0, "a", obj))), para("셋"))
        val out = FlowRebuilder.rebuild(old, "하나\n셋")
        assertEquals(2, out.size)
        val all = out.flatMap { it.anchors }
        assertEquals(1, all.size)
        assertSame(obj, all[0].payload)
    }

    @Test
    fun textTypedAtFieldEndGoesInsideField() {
        val begin = Any()
        val end = Any()
        // "AA[필드]BB"
        val p = para(
            "AA필드BB",
            anchors = listOf(Anchor(2, "a", begin), Anchor(4, "a", end, rightBias = true)),
        )
        val out = FlowRebuilder.rebuild(listOf(p), "AA필드내용BB")
        assertEquals(listOf(2, 6), out[0].anchors.map { it.offset })

        // 필드 바로 앞에 쓴 글은 시작 표시가 왼쪽에 붙어 있으므로 필드 안쪽 맨 앞으로 들어간다.
        val out2 = FlowRebuilder.rebuild(listOf(p), "AAX필드BB")
        assertEquals(listOf(2, 5), out2[0].anchors.map { it.offset })
    }

    @Test
    fun replacingTextAfterFieldEndStaysOutside() {
        val end = Any()
        val p = para("필드뒤글", anchors = listOf(Anchor(2, "a", end, rightBias = true)))
        val out = FlowRebuilder.rebuild(listOf(p), "필드다른글")
        assertEquals(2, out[0].anchors.single().offset)
    }

    @Test
    fun adjacentFieldsNeverInterleave() {
        val aEnd = Any()
        val bBegin = Any()
        val p = para("AB", anchors = listOf(Anchor(1, "a", aEnd, rightBias = true), Anchor(1, "a", bBegin)))
        val out = FlowRebuilder.rebuild(listOf(p), "AZB")
        val anchors = out[0].anchors
        assertEquals(listOf(aEnd, bBegin), anchors.map { it.payload })
        assertTrue(anchors[0].offset <= anchors[1].offset)
    }

    @Test
    fun largeRewriteStillWorks() {
        val old = (1..300).map { para("문단 $it 의 내용입니다. ".repeat(3)) }
        val newText = (1..300).joinToString("\n") { if (it % 7 == 0) "완전히 새로운 문단 $it" else "문단 $it 의 내용입니다. ".repeat(3) }
        val out = FlowRebuilder.rebuild(old, newText)
        assertEquals(300, out.size)
        assertEquals(newText, out.joinToString("\n") { it.text })
        assertEquals(300 - 300 / 7, out.count { it.unchanged })
    }
}
