package kr.naya.hwpedit.ui

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Typeface
import android.os.Handler
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.FrameLayout
import android.widget.HorizontalScrollView
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import kr.naya.hwpedit.core.Block
import kr.naya.hwpedit.core.BoxBlock
import kr.naya.hwpedit.core.BoxKind
import kr.naya.hwpedit.core.DocModel
import kr.naya.hwpedit.core.ImageBlock
import kr.naya.hwpedit.core.ObjectBlock
import kr.naya.hwpedit.core.TableBlock
import kr.naya.hwpedit.core.TextFlowBlock
import java.util.concurrent.ExecutorService
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/**
 * 문서 모델을 화면 뷰로 만든다.
 *
 * @param textScale 1포인트를 몇 sp 로 그릴지(글자 크기 설정)
 * @param contentWidth 본문 폭(px). 문서의 본문 폭을 여기에 맞춘다.
 * @param onFlow 입력칸이 하나 만들어질 때마다 불린다(문서 순서대로).
 */
class DocumentRenderer(
    private val context: Context,
    private val model: DocModel,
    textScale: Float,
    private val contentWidth: Int,
    private val io: ExecutorService,
    private val main: Handler,
    private val onFlow: (FlowEditText) -> Unit,
) {
    val ptPx: Float = context.sp(textScale)
    private val huPx: Float = contentWidth.toFloat() / model.bodyWidth.coerceAtLeast(1)
    private val cellPad = context.dp(6)

    /** 맨 위 블록마다 뷰를 만드는 함수 목록. 화면이 멈추지 않도록 조금씩 나눠 만든다. */
    fun topLevelBuilders(): List<() -> View> = model.blocks.map { b -> { blockView(b, contentWidth) } }

    private fun blockView(b: Block, width: Int): View = when (b) {
        is TextFlowBlock -> flowView(b, width)
        is TableBlock -> tableView(b, width)
        is ImageBlock -> imageView(b, width)
        is BoxBlock -> boxView(b, width)
        is ObjectBlock -> objectView(b)
    }

    private fun column(blocks: List<Block>, width: Int): LinearLayout = LinearLayout(context).apply {
        orientation = LinearLayout.VERTICAL
        for (b in blocks) addView(blockView(b, width), lp(ViewGroup.LayoutParams.MATCH_PARENT))
    }

    private fun lp(w: Int, h: Int = ViewGroup.LayoutParams.WRAP_CONTENT, top: Int = 0, bottom: Int = 0) =
        LinearLayout.LayoutParams(w, h).apply {
            topMargin = top
            bottomMargin = bottom
        }

    private fun flowView(flow: TextFlowBlock, width: Int): View {
        val v = FlowEditText(context, flow.flowId, flow.text)
        DocText.setBaseSize(v, ptPx)
        v.setText(DocText.build(flow, ptPx, width / 3))
        onFlow(v)
        return v
    }

    private fun tableView(t: TableBlock, width: Int): View {
        val minCol = context.dp(44)
        val px = IntArray(t.colCount) { i ->
            val hu = t.columnWidths.getOrElse(i) { 1000L }
            max(minCol, (hu * huPx).roundToInt())
        }
        // 표가 본문보다 조금 넓으면 줄여서 맞추고, 많이 넓으면 옆으로 밀어 보게 한다.
        val sum = px.sum()
        if (sum > width && sum < width * 1.25) {
            val k = width.toFloat() / sum
            for (i in px.indices) px[i] = max(minCol, (px[i] * k).toInt())
        }
        val grid = TableGridView(context, max(1, t.rowCount), max(1, t.colCount), px)
        for (cell in t.cells) {
            val cw = (cell.col until min(t.colCount, cell.col + cell.colSpan)).sumOf { px.getOrElse(it) { minCol } }
            val inner = column(cell.blocks, max(minCol, cw - cellPad * 2)).apply {
                setPadding(cellPad, cellPad / 2, cellPad, cellPad / 2)
                gravity = Gravity.CENTER_VERTICAL
            }
            grid.addCell(inner, cell.row, cell.col, cell.rowSpan, cell.colSpan)
        }
        val wrapper = LinearLayout(context).apply { orientation = LinearLayout.VERTICAL }
        if (grid.totalWidth > width) {
            val scroller = HorizontalScrollView(context).apply {
                isHorizontalScrollBarEnabled = true
                addView(grid)
            }
            wrapper.addView(scroller, lp(ViewGroup.LayoutParams.MATCH_PARENT))
        } else {
            wrapper.addView(grid, lp(ViewGroup.LayoutParams.WRAP_CONTENT))
        }
        if (t.caption.isNotEmpty()) wrapper.addView(column(t.caption, width), lp(ViewGroup.LayoutParams.MATCH_PARENT, top = context.dp(4)))
        wrapper.setPadding(0, context.dp(6), 0, context.dp(6))
        return wrapper
    }

    private fun imageView(img: ImageBlock, width: Int): View {
        val w = if (img.width > 0) (img.width * huPx).roundToInt().coerceIn(context.dp(40), width) else width
        val h = if (img.width > 0 && img.height > 0) (w.toLong() * img.height / img.width).toInt() else context.dp(160)
        val frame = FrameLayout(context).apply {
            background = roundRect(0xFFF6F7F9.toInt(), context.dp(4).toFloat())
        }
        val iv = ImageView(context).apply {
            scaleType = ImageView.ScaleType.FIT_CENTER
            contentDescription = "그림"
        }
        frame.addView(iv, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        val data = img.data
        if (data == null) {
            showPlaceholder(frame, "그림을 찾을 수 없어요")
        } else {
            io.execute {
                val bmp = decode(data, w, h)
                main.post {
                    if (bmp != null) {
                        iv.setImageBitmap(bmp)
                        frame.background = null
                    } else {
                        showPlaceholder(frame, "이 그림 형식은 미리 볼 수 없어요(파일에는 그대로 남아요)")
                    }
                }
            }
        }
        val wrapper = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(0, context.dp(6), 0, context.dp(6))
        }
        wrapper.addView(frame, LinearLayout.LayoutParams(w, h.coerceIn(context.dp(32), context.dp(2000))))
        if (img.caption.isNotEmpty()) wrapper.addView(column(img.caption, width), lp(ViewGroup.LayoutParams.MATCH_PARENT, top = context.dp(4)))
        return wrapper
    }

    private fun showPlaceholder(frame: FrameLayout, message: String) {
        val tv = context.label(message, 13f, Palette.SUBTEXT).apply {
            gravity = Gravity.CENTER
            setPadding(context.dp(8), context.dp(8), context.dp(8), context.dp(8))
        }
        frame.addView(tv, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
    }

    private fun decode(data: ByteArray, w: Int, h: Int): Bitmap? = try {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeByteArray(data, 0, data.size, bounds)
        if (bounds.outWidth <= 0 || bounds.outHeight <= 0) {
            null
        } else {
            var sample = 1
            while (bounds.outWidth / (sample * 2) >= w && bounds.outHeight / (sample * 2) >= h) sample *= 2
            val opts = BitmapFactory.Options().apply {
                inSampleSize = sample
                inPreferredConfig = if (bounds.outMimeType == "image/jpeg") Bitmap.Config.RGB_565 else Bitmap.Config.ARGB_8888
            }
            BitmapFactory.decodeByteArray(data, 0, data.size, opts)
        }
    } catch (e: OutOfMemoryError) {
        null
    } catch (e: RuntimeException) {
        null
    }

    private fun boxView(b: BoxBlock, width: Int): View {
        val pad = context.dp(10)
        val fill = when (b.kind) {
            BoxKind.HEADER, BoxKind.FOOTER -> 0xFFF7F8FA.toInt()
            BoxKind.FOOTNOTE, BoxKind.ENDNOTE -> 0xFFF5F8FF.toInt()
            else -> Palette.SURFACE
        }
        val box = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            background = roundRect(fill, context.dp(8).toFloat(), Palette.LINE, max(1, context.dp(1)))
            setPadding(pad, context.dp(6), pad, context.dp(6))
        }
        box.addView(context.label(b.label, 12f, Palette.SUBTEXT, bold = true))
        box.addView(column(b.blocks, width - pad * 2), lp(ViewGroup.LayoutParams.MATCH_PARENT))
        return FrameLayout(context).apply {
            setPadding(0, context.dp(6), 0, context.dp(6))
            addView(box, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        }
    }

    private fun objectView(o: ObjectBlock): View {
        val text = if (o.detail != null) "${o.label}  ${o.detail}" else o.label
        val tv: TextView = context.label(text, 13f, Palette.SUBTEXT).apply {
            if (o.detail != null) typeface = Typeface.MONOSPACE
            background = roundRect(0xFFF1F3F4.toInt(), context.dp(6).toFloat())
            setPadding(context.dp(10), context.dp(6), context.dp(10), context.dp(6))
            maxLines = 4
        }
        return FrameLayout(context).apply {
            setPadding(0, context.dp(4), 0, context.dp(4))
            addView(tv, FrameLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        }
    }
}
