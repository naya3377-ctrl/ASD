package kr.naya.hwpedit.ui

import android.app.Activity
import android.content.Context
import android.content.res.ColorStateList
import android.graphics.Typeface
import android.graphics.drawable.ColorDrawable
import android.graphics.drawable.Drawable
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.RippleDrawable
import android.os.Build
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.WindowInsets
import android.widget.FrameLayout
import android.widget.ImageButton
import android.widget.LinearLayout
import android.widget.TextView
import kotlin.math.max
import kotlin.math.roundToInt

/** 앱 전체에서 쓰는 색. */
object Palette {
    const val ACCENT = 0xFF2F6FED.toInt()
    const val ACCENT_SOFT = 0xFFE8F0FE.toInt()
    const val TEXT = 0xFF1C1C1E.toInt()
    const val SUBTEXT = 0xFF6B7280.toInt()
    const val BACKGROUND = 0xFFF2F3F5.toInt()
    const val SURFACE = 0xFFFFFFFF.toInt()
    const val LINE = 0xFFE3E5E8.toInt()
    const val TABLE_LINE = 0xFFB8BEC6.toInt()
    const val DANGER = 0xFFD93025.toInt()
    const val FIND = 0x66FFD54F
    const val FIND_CURRENT = 0xCCFF9800.toInt()
}

fun Context.dp(v: Number): Int =
    TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, v.toFloat(), resources.displayMetrics).roundToInt()

fun Context.sp(v: Number): Float =
    TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_SP, v.toFloat(), resources.displayMetrics)

fun View.dp(v: Number): Int = context.dp(v)

fun roundRect(fill: Int, radius: Float, stroke: Int? = null, strokeWidth: Int = 0): GradientDrawable =
    GradientDrawable().apply {
        setColor(fill)
        cornerRadius = radius
        if (stroke != null) setStroke(strokeWidth, stroke)
    }

/** 누르면 물결이 퍼지는 배경. */
fun ripple(content: Drawable?, radius: Float = 0f, color: Int = 0x22000000): Drawable {
    val mask = roundRect(0xFFFFFFFF.toInt(), radius)
    return RippleDrawable(ColorStateList.valueOf(color), content, mask)
}

fun Context.iconButton(iconRes: Int, description: String, tint: Int = Palette.TEXT, onClick: (View) -> Unit): ImageButton =
    ImageButton(this).apply {
        setImageResource(iconRes)
        imageTintList = ColorStateList.valueOf(tint)
        contentDescription = description
        background = ripple(null, dp(24).toFloat())
        scaleType = android.widget.ImageView.ScaleType.CENTER
        layoutParams = LinearLayout.LayoutParams(dp(48), dp(48))
        setOnClickListener(onClick)
        if (Build.VERSION.SDK_INT >= 26) tooltipText = description
    }

fun Context.label(text: CharSequence, sizeSp: Float = 15f, color: Int = Palette.TEXT, bold: Boolean = false): TextView =
    TextView(this).apply {
        this.text = text
        setTextColor(color)
        setTextSize(TypedValue.COMPLEX_UNIT_SP, sizeSp)
        if (bold) typeface = Typeface.DEFAULT_BOLD
    }

/** 둥근 단추. primary 면 강조색 바탕. */
fun Context.pillButton(text: String, primary: Boolean, onClick: (View) -> Unit): TextView =
    label(text, 16f, if (primary) Palette.SURFACE else Palette.ACCENT, bold = true).apply {
        gravity = Gravity.CENTER
        minHeight = dp(52)
        setPadding(dp(20), 0, dp(20), 0)
        val fill = if (primary) Palette.ACCENT else Palette.ACCENT_SOFT
        background = ripple(roundRect(fill, dp(26).toFloat()), dp(26).toFloat(), 0x33FFFFFF)
        isClickable = true
        isFocusable = true
        setOnClickListener(onClick)
    }

fun Context.divider(): View = View(this).apply {
    setBackgroundColor(Palette.LINE)
    layoutParams = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, max(1, dp(0.5f)))
}

/** 위 막대: [왼쪽 단추] 제목 [오른쪽 단추들]. */
class TopBar(context: Context) : LinearLayout(context) {
    val title: TextView = context.label("", 18f, Palette.TEXT, bold = true).apply {
        maxLines = 1
        ellipsize = android.text.TextUtils.TruncateAt.MIDDLE
        layoutParams = LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).apply { marginStart = dp(4) }
    }
    val actions = LinearLayout(context).apply { orientation = HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
    private val leading = FrameLayout(context)

    init {
        orientation = HORIZONTAL
        gravity = Gravity.CENTER_VERTICAL
        setBackgroundColor(Palette.SURFACE)
        minimumHeight = dp(56)
        setPadding(dp(4), 0, dp(4), 0)
        addView(leading, LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        addView(title)
        addView(actions)
    }

    fun setLeading(view: View?) {
        leading.removeAllViews()
        if (view != null) leading.addView(view)
        title.setPadding(if (view == null) dp(12) else 0, 0, 0, 0)
    }

    fun setActions(vararg views: View) {
        actions.removeAllViews()
        for (v in views) actions.addView(v)
    }
}

/** 상태 막대·내비게이션 막대·키보드 뒤로 내용이 들어가지 않도록 여백을 준다. */
object EdgeToEdge {
    @Suppress("DEPRECATION")
    fun enable(activity: Activity) {
        val window = activity.window
        if (Build.VERSION.SDK_INT >= 30) {
            window.setDecorFitsSystemWindows(false)
        } else {
            window.decorView.systemUiVisibility = View.SYSTEM_UI_FLAG_LAYOUT_STABLE or
                View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN or
                View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION or
                View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR or
                View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR
        }
        window.statusBarColor = 0
        window.navigationBarColor = 0
        if (Build.VERSION.SDK_INT >= 29) {
            window.isNavigationBarContrastEnforced = false
        }
        window.setBackgroundDrawable(ColorDrawable(Palette.SURFACE))
    }

    /** top: 위쪽 여백을 받을 뷰, bottom: 아래쪽(내비게이션 막대·키보드) 여백을 받을 뷰. */
    @Suppress("DEPRECATION")
    fun apply(root: View, top: View, bottom: View) {
        val topBase = top.paddingTop
        val bottomBase = bottom.paddingBottom
        root.setOnApplyWindowInsetsListener { _, insets ->
            val t: Int
            val b: Int
            val l: Int
            val r: Int
            if (Build.VERSION.SDK_INT >= 30) {
                val bars = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
                val ime = insets.getInsets(WindowInsets.Type.ime())
                t = bars.top; b = max(bars.bottom, ime.bottom); l = bars.left; r = bars.right
            } else {
                t = insets.systemWindowInsetTop; b = insets.systemWindowInsetBottom
                l = insets.systemWindowInsetLeft; r = insets.systemWindowInsetRight
            }
            top.setPadding(top.paddingLeft, topBase + t, top.paddingRight, top.paddingBottom)
            bottom.setPadding(bottom.paddingLeft, bottom.paddingTop, bottom.paddingRight, bottomBase + b)
            root.setPadding(l, 0, r, 0)
            insets
        }
        root.requestApplyInsets()
    }
}
