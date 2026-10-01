package kr.naya.hwpedit.ui

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Paint
import android.text.InputFilter
import android.text.InputType
import android.text.Layout
import android.text.SpannableStringBuilder
import android.text.Spanned
import android.text.style.AbsoluteSizeSpan
import android.text.style.AlignmentSpan
import android.text.style.BackgroundColorSpan
import android.text.style.ForegroundColorSpan
import android.text.style.LeadingMarginSpan
import android.text.style.LineHeightSpan
import android.text.style.RelativeSizeSpan
import android.text.style.StrikethroughSpan
import android.text.style.StyleSpan
import android.text.style.SubscriptSpan
import android.text.style.SuperscriptSpan
import android.text.style.TypefaceSpan
import android.text.style.UnderlineSpan
import android.util.TypedValue
import android.view.Gravity
import android.widget.EditText
import kr.naya.hwpedit.core.Align
import kr.naya.hwpedit.core.CharStyle
import kr.naya.hwpedit.core.SpecialChars
import kr.naya.hwpedit.core.TextFlowBlock
import kotlin.math.min
import kotlin.math.roundToInt

/** 문단 안 줄바꿈(Shift+Enter)을 나타내는 표시. 화면에는 \n 으로 보인다. */
class SoftBreakSpan

/** 찾기 결과 강조. */
class FindSpan(color: Int) : BackgroundColorSpan(color)

/** 문단 위·아래 간격. */
class ParagraphSpacingSpan(private val before: Int, private val after: Int) : LineHeightSpan {
    override fun chooseHeight(text: CharSequence, start: Int, end: Int, spanstartv: Int, lineHeight: Int, fm: Paint.FontMetricsInt) {
        val s = text as? Spanned ?: return
        val spanStart = s.getSpanStart(this)
        val spanEnd = s.getSpanEnd(this)
        if (start == spanStart && before > 0) {
            fm.ascent -= before
            fm.top -= before
        }
        if (end == spanEnd && after > 0) {
            fm.descent += after
            fm.bottom += after
        }
    }
}

/**
 * 글 흐름(문단 여러 개) 하나를 보여 주고 고치는 입력칸.
 * 보기 상태에서는 키보드가 뜨지 않고 글자를 바꿀 수 없지만, 골라서 복사할 수는 있다.
 */
@SuppressLint("ViewConstructor")
class FlowEditText(context: Context, var flowId: Int, var originalText: String) : EditText(context) {

    private val blockAll = InputFilter { _, _, _, dest, dstart, dend -> dest.subSequence(dstart, dend) }

    var editable: Boolean = true
        set(value) {
            field = value
            filters = if (value) emptyArray() else arrayOf(blockAll)
            showSoftInputOnFocus = value
            isCursorVisible = value
        }

    init {
        background = null
        setPadding(0, dp(2), 0, dp(2))
        gravity = Gravity.TOP or Gravity.START
        inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE or
            InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS
        isSingleLine = false
        setHorizontallyScrolling(false)
        setTextColor(Palette.TEXT)
        setLineSpacing(0f, 1.15f)
        includeFontPadding = true
        highlightColor = 0x552F6FED
        // 긴 문서에서 입력칸마다 자동완성·맞춤법 검사가 돌면 느려진다.
        importantForAutofill = IMPORTANT_FOR_AUTOFILL_NO
        Typo.koreanWordWrap(this)
    }

    /** 문서에 저장할 형태의 글(문단 안 줄바꿈은 \u2028). */
    fun modelText(): String = DocText.toModel(text)

    fun hasEdits(): Boolean = modelText() != originalText

    fun clearFindMarks() {
        val e = text ?: return
        for (s in e.getSpans(0, e.length, FindSpan::class.java)) e.removeSpan(s)
    }
}

/** 글자 배치 공통 설정. */
object Typo {
    /** 한국어를 낱말(어절) 단위로 줄바꿈한다(안드로이드 13 이상). */
    fun koreanWordWrap(view: android.widget.TextView) {
        if (android.os.Build.VERSION.SDK_INT >= 33) {
            view.lineBreakWordStyle = android.graphics.text.LineBreakConfig.LINE_BREAK_WORD_STYLE_PHRASE
        }
    }
}

/** 문서 모델 글과 화면 글 사이 변환, 글자 모양 입히기. */
object DocText {

    fun toModel(text: CharSequence?): String {
        if (text == null) return ""
        val sb = StringBuilder(text)
        if (text is Spanned) {
            for (s in text.getSpans(0, text.length, SoftBreakSpan::class.java)) {
                val st = text.getSpanStart(s)
                if (st in sb.indices && sb[st] == '\n') sb.setCharAt(st, SpecialChars.LINE_BREAK)
            }
        }
        return sb.toString()
    }

    /**
     * @param ptPx 1포인트를 몇 픽셀로 그릴지
     * @param maxMarginPx 들여쓰기 최대 폭(좁은 화면에서 글이 밀려나지 않도록)
     */
    fun build(flow: TextFlowBlock, ptPx: Float, maxMarginPx: Int): SpannableStringBuilder {
        val sb = SpannableStringBuilder()
        val paraRanges = ArrayList<IntArray>()
        // 글을 먼저 다 붙이고 나서 모양을 입힌다. 모양 범위 끝이 '뒤에 붙는 글을 품는' 방식이라
        // 붙이는 도중에 입히면 뒤 문단까지 번진다.
        for ((pi, p) in flow.paragraphs.withIndex()) {
            if (pi > 0) sb.append('\n')
            val start = sb.length
            sb.append(p.text.replace(SpecialChars.LINE_BREAK, '\n'))
            paraRanges.add(intArrayOf(start, start + p.text.length))
        }
        for ((pi, p) in flow.paragraphs.withIndex()) {
            val start = paraRanges[pi][0]
            for ((i, c) in p.text.withIndex()) {
                if (c == SpecialChars.LINE_BREAK) {
                    sb.setSpan(SoftBreakSpan(), start + i, start + i + 1, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                }
            }
            for (r in p.runs) applyChar(sb, start + r.start, start + r.end, r.style, ptPx, atParagraphStart = r.start == 0)
        }
        for ((pi, p) in flow.paragraphs.withIndex()) {
            val (start, end0) = paraRanges[pi].let { it[0] to it[1] }
            val end = if (pi < flow.paragraphs.size - 1) end0 + 1 else sb.length
            if (end <= start && pi == flow.paragraphs.size - 1 && start == sb.length) continue
            val st = p.style
            val align = when (st.align) {
                Align.CENTER -> Layout.Alignment.ALIGN_CENTER
                Align.RIGHT -> Layout.Alignment.ALIGN_OPPOSITE
                else -> null
            }
            if (align != null) sb.setSpan(AlignmentSpan.Standard(align), start, end, Spanned.SPAN_PARAGRAPH)
            val left = (st.marginLeftPt * ptPx).roundToInt()
            val first = left + (st.indentPt.coerceAtLeast(0f) * ptPx).roundToInt()
            val rest = left + ((-st.indentPt).coerceAtLeast(0f) * ptPx).roundToInt()
            if (first > 0 || rest > 0) {
                sb.setSpan(
                    LeadingMarginSpan.Standard(min(first, maxMarginPx), min(rest, maxMarginPx)),
                    start, end, Spanned.SPAN_PARAGRAPH,
                )
            }
            val before = (st.spaceBeforePt.coerceIn(0f, 24f) * ptPx).roundToInt()
            val after = (st.spaceAfterPt.coerceIn(0f, 24f) * ptPx).roundToInt()
            if (before > 0 || after > 0) sb.setSpan(ParagraphSpacingSpan(before, after), start, end, Spanned.SPAN_PARAGRAPH)
        }
        return sb
    }

    /**
     * 글자 모양을 입힌다. 범위 끝에 친 글은 그 모양을 따른다(앞 글자 모양 잇기).
     * 문단 첫 글자 모양은 문단 맨 앞에 친 글에도 이어지도록 시작도 포함으로 둔다.
     */
    private fun applyChar(sb: SpannableStringBuilder, start: Int, end: Int, s: CharStyle, ptPx: Float, atParagraphStart: Boolean) {
        if (end <= start) return
        val flag = if (atParagraphStart) Spanned.SPAN_INCLUSIVE_INCLUSIVE else Spanned.SPAN_EXCLUSIVE_INCLUSIVE
        val size = s.sizePt.coerceIn(4f, 72f)
        sb.setSpan(AbsoluteSizeSpan((size * ptPx).roundToInt(), false), start, end, flag)
        when {
            s.bold && s.italic -> sb.setSpan(StyleSpan(android.graphics.Typeface.BOLD_ITALIC), start, end, flag)
            s.bold -> sb.setSpan(StyleSpan(android.graphics.Typeface.BOLD), start, end, flag)
            s.italic -> sb.setSpan(StyleSpan(android.graphics.Typeface.ITALIC), start, end, flag)
        }
        if (s.underline) sb.setSpan(UnderlineSpan(), start, end, flag)
        if (s.strike) sb.setSpan(StrikethroughSpan(), start, end, flag)
        if (s.superscript || s.subscript) {
            sb.setSpan(if (s.superscript) SuperscriptSpan() else SubscriptSpan(), start, end, flag)
            sb.setSpan(RelativeSizeSpan(0.7f), start, end, flag)
        }
        val color = readableColor(s.color)
        if (color != 0xFF000000.toInt()) sb.setSpan(ForegroundColorSpan(color), start, end, flag)
        sb.setSpan(TypefaceSpan(familyOf(s.fontName)), start, end, flag)
    }

    /** 흰 글씨처럼 흰 종이에서 안 보이는 색은 회색으로 바꿔 보여 준다(파일에는 영향 없음). */
    private fun readableColor(argb: Int): Int {
        val r = (argb shr 16) and 0xFF
        val g = (argb shr 8) and 0xFF
        val b = argb and 0xFF
        val lum = 0.299 * r + 0.587 * g + 0.114 * b
        return if (lum > 225) 0xFF8A8F98.toInt() else (argb or (0xFF shl 24))
    }

    fun familyOf(fontName: String?): String {
        val n = fontName ?: return "sans-serif"
        val serifHints = listOf("바탕", "명조", "궁서", "batang", "myeongjo", "serif", "times", "georgia", "garamond")
        return if (serifHints.any { n.contains(it, ignoreCase = true) }) "serif" else "sans-serif"
    }

    /** 찾기용: 글에서 query 가 나오는 모든 위치(대소문자 무시). */
    fun findAll(text: CharSequence, query: String): List<Int> {
        if (query.isEmpty()) return emptyList()
        val hay = text.toString().lowercase()
        val needle = query.lowercase()
        val out = ArrayList<Int>()
        var i = hay.indexOf(needle)
        while (i >= 0) {
            out.add(i)
            i = hay.indexOf(needle, i + needle.length)
        }
        return out
    }

    fun setBaseSize(view: EditText, ptPx: Float) {
        view.setTextSize(TypedValue.COMPLEX_UNIT_PX, 10f * ptPx)
    }
}
