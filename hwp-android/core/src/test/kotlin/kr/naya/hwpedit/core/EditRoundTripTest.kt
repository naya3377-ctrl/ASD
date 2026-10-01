package kr.naya.hwpedit.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

class EditRoundTripTest {

    private fun open(bytes: ByteArray) = HwpDocuments.open(bytes).model

    private fun flowsOf(model: DocModel) = model.allFlows()

    @Test
    fun saveWithoutEditsKeepsEverything() {
        for (name in TestSupport.sampleNames) {
            val original = TestSupport.sample(name)
            val before = open(original)
            val saved = HwpDocuments.save(original, emptyMap())
            TestSupport.output("unchanged-$name", saved)
            val after = open(saved)
            assertEquals(name, before.plainText(), after.plainText())
            assertEquals(name, HwpDocuments.anchorCount(original), HwpDocuments.anchorCount(saved))
        }
    }

    @Test
    fun appendTextToEveryFlow() {
        for (name in TestSupport.sampleNames) {
            val original = TestSupport.sample(name)
            val before = open(original)
            if (before.readOnlyReason != null) continue
            val edits = flowsOf(before).associate { it.flowId to it.text + " 수정함" }
            val saved = HwpDocuments.save(original, edits)
            TestSupport.output("appended-$name", saved)
            val after = open(saved)
            val texts = flowsOf(after).map { it.text }
            for (f in flowsOf(before)) {
                val expected = f.text + " 수정함"
                assertTrue("$name: '$expected' 없음 in $texts", texts.any { it.contains(expected.trim()) })
            }
            assertEquals(name, HwpDocuments.anchorCount(original), HwpDocuments.anchorCount(saved))
        }
    }

    @Test
    fun splitMergeInsertDeleteParagraphs() {
        for (name in listOf("text.hwp", "headerfooter.hwp", "sample1.hwpx", "headerfooter.hwpx")) {
            val original = TestSupport.sample(name)
            val model = open(original)
            val flow = flowsOf(model).maxBy { it.paragraphs.size }
            val lines = flow.text.split('\n').toMutableList()

            // 1) 첫 문단을 둘로 나누고, 둘째·셋째 문단을 합치고, 끝에 새 문단을 넣는다.
            val first = lines[0]
            val cut = first.length / 2
            val edited = ArrayList<String>()
            edited.add(first.substring(0, cut))
            edited.add(first.substring(cut))
            if (lines.size >= 3) {
                edited.add(lines[1] + lines[2])
                edited.addAll(lines.drop(3))
            } else {
                edited.addAll(lines.drop(1))
            }
            edited.add("새로 넣은 문단")
            val newText = edited.joinToString("\n")

            val saved = HwpDocuments.save(original, mapOf(flow.flowId to newText))
            TestSupport.output("restructured-$name", saved)
            val after = open(saved)
            // 개체가 붙은 문단 뒤에 넣은 문단은 다시 열면 개체 다음에 보일 수 있으므로 순서만 확인한다.
            assertInOrder(name, edited.filter { it.isNotEmpty() }, after.plainText().split('\n'))
            assertEquals(name, HwpDocuments.anchorCount(original), HwpDocuments.anchorCount(saved))

            // 2) 흐름 전체를 지워도 보이지 않는 개체(구역 정의 등)는 남아야 한다.
            val cleared = HwpDocuments.save(original, mapOf(flow.flowId to ""))
            TestSupport.output("cleared-$name", cleared)
            assertEquals(name, HwpDocuments.anchorCount(original), HwpDocuments.anchorCount(cleared))
        }
    }

    private fun assertInOrder(name: String, expected: List<String>, actual: List<String>) {
        var i = 0
        for (line in actual) if (i < expected.size && line == expected[i]) i++
        assertEquals("$name: $expected 순서대로 없음 in $actual", expected.size, i)
    }

    @Test
    fun formattingOfUntouchedCharactersIsKept() {
        // sample1.hwpx 둘째 문단: "  우리는 수학 이다.더" 중 6~8("수학")만 기울임.
        val original = TestSupport.sample("sample1.hwpx")
        val model = open(original)
        val flow = flowsOf(model).first { it.text.contains("우리는") }
        val newText = flow.text.replace("우리는", "우리 모두는")
        val saved = HwpDocuments.save(original, mapOf(flow.flowId to newText))
        val after = flowsOf(open(saved)).first { it.text.contains("우리 모두는") }
        val para = after.paragraphs.first { it.text.contains("우리 모두는") }
        val italic = para.runs.filter { it.style.italic }.map { para.text.substring(it.start, it.end) }
        assertEquals(listOf("수학"), italic)
    }

    @Test
    fun specialCharactersRoundTrip() {
        for (name in listOf("text.hwp", "blank.hwpx")) {
            val original = TestSupport.sample(name)
            val flow = flowsOf(open(original)).first()
            val text = "탭\t다음${SpecialChars.LINE_BREAK}줄바꿈 묶음${SpecialChars.NB_SPACE}빈칸 " +
                "고정${SpecialChars.FW_SPACE}폭 하이픈${SpecialChars.HYPHEN}끝 😀 이모지"
            val saved = HwpDocuments.save(original, mapOf(flow.flowId to text))
            TestSupport.output("special-$name", saved)
            val after = flowsOf(open(saved)).first()
            assertEquals(name, text, after.text)
        }
    }

    @Test
    fun editTableCellAndCaption() {
        val original = TestSupport.sample("table.hwp")
        val model = open(original)
        val table = model.blocks.filterIsInstance<TableBlock>().first()
        val cell = table.cells.first { it.row == 1 && it.col == 1 }
        val cellFlow = cell.blocks.filterIsInstance<TextFlowBlock>().first()
        val captionFlow = table.caption.filterIsInstance<TextFlowBlock>().first()
        val saved = HwpDocuments.save(
            original,
            mapOf(cellFlow.flowId to "칸 수정\n두 번째 문단", captionFlow.flowId to "표 1. 캡션 수정"),
        )
        TestSupport.output("table-edit.hwp", saved)
        val after = open(saved)
        val t2 = after.blocks.filterIsInstance<TableBlock>().first()
        val c2 = t2.cells.first { it.row == 1 && it.col == 1 }
        assertEquals("칸 수정\n두 번째 문단", c2.blocks.filterIsInstance<TextFlowBlock>().first().text)
        assertEquals("표 1. 캡션 수정", t2.caption.filterIsInstance<TextFlowBlock>().first().text)
    }

    @Test
    fun editTextAroundFieldKeepsField() {
        val original = TestSupport.sample("field.hwp")
        val model = open(original)
        val flow = flowsOf(model).first { it.text.contains("테스트 누름틀") }
        val saved = HwpDocuments.save(original, mapOf(flow.flowId to flow.text.replace("테스트 누름틀", "바뀐 누름틀 내용")))
        TestSupport.output("field-edit.hwp", saved)
        assertEquals(HwpDocuments.anchorCount(original), HwpDocuments.anchorCount(saved))
        assertTrue(open(saved).plainText().contains("AA바뀐 누름틀 내용ABCD"))
    }

    @Test
    fun repeatedSavesStayStable() {
        for (name in listOf("text.hwp", "table.hwpx")) {
            var bytes = TestSupport.sample(name)
            repeat(3) { round ->
                val flow = flowsOf(open(bytes)).first()
                bytes = HwpDocuments.save(bytes, mapOf(flow.flowId to flow.text + "\n${round + 1}번째 저장"))
            }
            val text = open(bytes).plainText()
            assertTrue(name, text.contains("1번째 저장") && text.contains("3번째 저장"))
        }
    }

    @Test
    fun hwpxPackageLooksLikeHancomOutput() {
        val original = TestSupport.sample("table.hwpx")
        val flow = flowsOf(open(original)).first()
        val saved = HwpDocuments.save(original, mapOf(flow.flowId to "미리보기에 보일 글"))
        java.util.zip.ZipInputStream(saved.inputStream()).use { zin ->
            val first = zin.nextEntry!!
            assertEquals("mimetype", first.name)
            assertEquals(java.util.zip.ZipEntry.STORED, first.method)
            assertEquals("application/hwp+zip", String(zin.readBytes()))
            var preview: String? = null
            while (true) {
                val e = zin.nextEntry ?: break
                if (e.name == "Preview/PrvText.txt") preview = String(zin.readBytes(), Charsets.UTF_8)
            }
            assertTrue(preview, preview!!.startsWith("<미리보기에 보일 글>"))
        }
    }

    @Test
    fun rejectsNonHwpFiles() {
        try {
            HwpDocuments.open("hello".toByteArray())
            fail()
        } catch (e: DocumentException) {
            assertTrue(e.message!!.isNotBlank())
        }
    }
}
