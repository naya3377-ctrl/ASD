package kr.naya.hwpedit

import android.content.Intent
import android.net.Uri
import android.os.Looper
import kr.naya.hwpedit.core.HwpDocuments
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config
import java.io.File

/** 실제 화면 코드로 문서를 열고, 고치고, 저장해 본다(가상 안드로이드). */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34])
class EditorSmokeTest {

    private fun sampleFile(name: String): File {
        val bytes = javaClass.getResourceAsStream("/samples/$name")!!.readBytes()
        val ext = name.substringAfterLast('.')
        return File.createTempFile("smoke-", ".$ext").apply { writeBytes(bytes) }
    }

    private fun waitUntil(what: String, cond: () -> Boolean) {
        val deadline = System.currentTimeMillis() + 30_000
        while (System.currentTimeMillis() < deadline) {
            shadowOf(Looper.getMainLooper()).idle()
            if (cond()) return
            Thread.sleep(20)
        }
        throw AssertionError("시간 안에 끝나지 않음: $what")
    }

    private fun openEditor(file: File): EditorActivity {
        val ctx = RuntimeEnvironment.getApplication()
        val intent = Intent(ctx, EditorActivity::class.java).setAction(Intent.ACTION_EDIT).setData(Uri.fromFile(file))
        val activity = Robolectric.buildActivity(EditorActivity::class.java, intent).setup().get()
        waitUntil("문서 열기") { !activity.isBusyForTest() && activity.flowViews().isNotEmpty() }
        return activity
    }

    @Test
    fun opensEditsAndSavesHwp() {
        val file = sampleFile("table.hwp")
        val activity = openEditor(file)
        val flows = activity.flowViews()
        val cell = flows.first { it.text.toString() == "OPQ" }

        // 보기 상태에서는 글이 바뀌지 않아야 한다.
        cell.text.insert(0, "X")
        assertEquals("OPQ", cell.text.toString())

        activity.setEditModeForTest(true)
        cell.text.append(" 수정\n새 문단")
        activity.saveForTest()
        waitUntil("저장") { !activity.isBusyForTest() }

        val saved = HwpDocuments.open(file.readBytes()).model
        assertTrue(saved.plainText().contains("OPQ 수정\n새 문단"))
        assertFalse(activity.flowViews().any { it.hasEdits() })
    }

    @Test
    fun characterFormatsDoNotLeakIntoFollowingText() {
        // sample1.hwpx: 첫 문단 "수학"은 기울임, 둘째 문단은 "수학"(6~8)만 기울임.
        val activity = openEditor(sampleFile("sample1.hwpx"))
        val flow = activity.flowViews().first { it.text.toString().contains("우리는") }
        val e = flow.text
        fun italicAt(i: Int) = e.getSpans(i, i + 1, android.text.style.StyleSpan::class.java)
            .any { it.style == android.graphics.Typeface.ITALIC }
        val at = e.indexOf("우리는")
        assertFalse("우리는 은 기울임이 아니어야 함", italicAt(at))
        assertTrue("수학 은 기울임", italicAt(e.indexOf("수학", at)))
        assertTrue("첫 문단 수학 은 기울임", italicAt(0))
    }

    @Test
    fun opensAndSavesHwpxWithSoftBreak() {
        val file = sampleFile("sample1.hwpx")
        val activity = openEditor(file)
        activity.setEditModeForTest(true)
        val flow = activity.flowViews().first { it.text.toString().contains("우리는") }
        val at = flow.text.indexOf("우리는")
        flow.text.insert(at, "모두 ")
        activity.saveForTest()
        waitUntil("저장") { !activity.isBusyForTest() }
        val saved = HwpDocuments.open(file.readBytes()).model
        assertTrue(saved.plainText().contains("모두 우리는"))
    }

    @Test
    fun startScreenAndAboutOpen() {
        val main = Robolectric.buildActivity(MainActivity::class.java).setup().get()
        assertFalse(main.isFinishing)
        val about = Robolectric.buildActivity(AboutActivity::class.java).setup().get()
        assertFalse(about.isFinishing)
    }

    @Test
    fun newDocumentStartsInEditMode() {
        val ctx = RuntimeEnvironment.getApplication()
        val intent = Intent(ctx, EditorActivity::class.java).putExtra(EditorActivity.EXTRA_NEW, true)
        val activity = Robolectric.buildActivity(EditorActivity::class.java, intent).setup().get()
        waitUntil("새 문서") { !activity.isBusyForTest() && activity.flowViews().isNotEmpty() }
        val flow = activity.flowViews().first()
        flow.text.append("첫 글")
        assertEquals("첫 글", flow.modelText())
    }
}
