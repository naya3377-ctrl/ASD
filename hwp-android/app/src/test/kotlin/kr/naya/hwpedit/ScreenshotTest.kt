package kr.naya.hwpedit

import android.app.Activity
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Canvas
import android.net.Uri
import android.os.Looper
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.io.File

/**
 * 화면을 그림 파일로 남긴다(app/build/screens). 실제 휴대폰이 없을 때 모양을 확인하는 용도.
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [34], qualifiers = "w393dp-h852dp-hdpi")
class ScreenshotTest {

    private val outDir = File("build/screens").apply { mkdirs() }

    private fun idleFor(ms: Long, cond: () -> Boolean = { false }) {
        val deadline = System.currentTimeMillis() + ms
        while (System.currentTimeMillis() < deadline) {
            shadowOf(Looper.getMainLooper()).idle()
            if (cond()) break
            Thread.sleep(20)
        }
        shadowOf(Looper.getMainLooper()).idle()
    }

    private fun capture(activity: Activity, name: String) {
        val root = activity.window.decorView
        val w = root.width.takeIf { it > 0 } ?: 590
        val h = root.height.takeIf { it > 0 } ?: 1278
        val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        root.draw(Canvas(bmp))
        File(outDir, "$name.png").outputStream().use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }
    }

    private fun sample(name: String): File {
        val bytes = javaClass.getResourceAsStream("/samples/$name")!!.readBytes()
        return File.createTempFile("shot-", "." + name.substringAfterLast('.')).apply { writeBytes(bytes) }
    }

    private fun editor(file: File): EditorActivity {
        val ctx = RuntimeEnvironment.getApplication()
        val intent = Intent(ctx, EditorActivity::class.java).setAction(Intent.ACTION_VIEW).setData(Uri.fromFile(file))
        val a = Robolectric.buildActivity(EditorActivity::class.java, intent).setup().get()
        idleFor(20_000) { !a.isBusyForTest() && a.flowViews().isNotEmpty() }
        idleFor(500)
        return a
    }

    @Test
    fun startScreen() {
        val a = Robolectric.buildActivity(MainActivity::class.java).setup().get()
        idleFor(300)
        capture(a, "1-start")
    }

    @Test
    fun documentScreens() {
        capture(editor(sample("field.hwp")), "2-field-hwp")
        capture(editor(sample("table.hwp")), "3-table-hwp")
        val e = editor(sample("sample1.hwpx"))
        e.setEditModeForTest(true)
        idleFor(300)
        capture(e, "4-edit-hwpx")
    }
}
