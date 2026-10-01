package kr.naya.hwpedit.ui

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.view.View
import android.view.ViewGroup
import kotlin.math.max

/**
 * 표 하나를 칸 합치기까지 반영해 격자로 배치하는 뷰.
 * 열 폭은 고정, 행 높이는 칸 내용에 맞춘다.
 */
@SuppressLint("ViewConstructor")
class TableGridView(
    context: Context,
    private val rows: Int,
    private val cols: Int,
    private val columnWidths: IntArray,
) : ViewGroup(context) {

    class CellParams(val row: Int, val col: Int, val rowSpan: Int, val colSpan: Int) :
        ViewGroup.LayoutParams(MATCH_PARENT, WRAP_CONTENT)

    private val colX = IntArray(cols + 1).also {
        for (c in 0 until cols) it[c + 1] = it[c] + columnWidths[c]
    }
    private var rowY = IntArray(rows + 1)
    private val border = Paint().apply {
        color = Palette.TABLE_LINE
        style = Paint.Style.STROKE
        strokeWidth = max(1f, resources.displayMetrics.density * 0.8f)
        isAntiAlias = false
    }

    init {
        setWillNotDraw(false)
    }

    val totalWidth: Int get() = colX[cols]

    fun addCell(view: View, row: Int, col: Int, rowSpan: Int, colSpan: Int) {
        val r = row.coerceIn(0, rows - 1)
        val c = col.coerceIn(0, cols - 1)
        addView(view, CellParams(r, c, rowSpan.coerceIn(1, rows - r), colSpan.coerceIn(1, cols - c)))
    }

    private fun cellWidth(p: CellParams) = colX[p.col + p.colSpan] - colX[p.col]

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val rowH = IntArray(rows) { dp(28) }
        val children = (0 until childCount).map { getChildAt(it) }
        for (child in children) {
            val p = child.layoutParams as CellParams
            child.measure(
                MeasureSpec.makeMeasureSpec(cellWidth(p), MeasureSpec.EXACTLY),
                MeasureSpec.makeMeasureSpec(0, MeasureSpec.UNSPECIFIED),
            )
            if (p.rowSpan == 1) rowH[p.row] = max(rowH[p.row], child.measuredHeight)
        }
        // 여러 행에 걸친 칸이 더 크면 마지막 행을 늘린다.
        for (child in children.sortedBy { (it.layoutParams as CellParams).rowSpan }) {
            val p = child.layoutParams as CellParams
            if (p.rowSpan == 1) continue
            var have = 0
            for (r in p.row until p.row + p.rowSpan) have += rowH[r]
            val need = child.measuredHeight - have
            if (need > 0) rowH[p.row + p.rowSpan - 1] += need
        }
        rowY = IntArray(rows + 1)
        for (r in 0 until rows) rowY[r + 1] = rowY[r] + rowH[r]
        // 칸 높이를 행 높이에 맞춰 다시 잰다(배경·선이 칸 전체를 채우도록).
        for (child in children) {
            val p = child.layoutParams as CellParams
            val h = rowY[p.row + p.rowSpan] - rowY[p.row]
            if (child.measuredHeight != h) {
                child.measure(
                    MeasureSpec.makeMeasureSpec(cellWidth(p), MeasureSpec.EXACTLY),
                    MeasureSpec.makeMeasureSpec(h, MeasureSpec.EXACTLY),
                )
            }
        }
        setMeasuredDimension(colX[cols] + border.strokeWidth.toInt(), rowY[rows] + border.strokeWidth.toInt())
    }

    override fun onLayout(changed: Boolean, l: Int, t: Int, r: Int, b: Int) {
        for (i in 0 until childCount) {
            val child = getChildAt(i)
            val p = child.layoutParams as CellParams
            child.layout(colX[p.col], rowY[p.row], colX[p.col + p.colSpan], rowY[p.row + p.rowSpan])
        }
    }

    override fun dispatchDraw(canvas: Canvas) {
        super.dispatchDraw(canvas)
        val half = border.strokeWidth / 2f
        for (i in 0 until childCount) {
            val c = getChildAt(i)
            canvas.drawRect(c.left + half, c.top + half, c.right - half, c.bottom - half, border)
        }
    }

    override fun checkLayoutParams(p: LayoutParams?): Boolean = p is CellParams
}
